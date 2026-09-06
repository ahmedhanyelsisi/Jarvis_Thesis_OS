import json
from dataclasses import replace
import pytest
from authorization.authorization_manager import AuthorizationManager
from security.authorization_audit_ledger import AuthorizationAuditLedger
from security.agent_permission_registry import AgentPermissionRegistry
from security.voice_safety_filter import InputSource, VoiceSafetyFilter
from security.state_recovery_manager import JarvisStateRecovery


@pytest.mark.parametrize("source", [InputSource.VOICE_CONFIRMED, InputSource.VOICE_UNCONFIRMED, InputSource.MEMORY, InputSource.AGENT])
def test_nonlocal_sources_cannot_enable_scopes(chat, source):
    chat.process_input("enable autonomous mode", input_source=source, confidence=.99, has_wake_word=True)
    assert chat.auth_manager.scoped_manager.get_active_scopes() == []


@pytest.mark.parametrize("confidence", [None, float("nan"), float("inf"), -1, 2, True, "0.99"])
def test_invalid_confidence_is_rejected(confidence):
    result = VoiceSafetyFilter().filter_input("check citations", InputSource.VOICE_UNCONFIRMED, confidence, True)
    assert not result["safe"]


def test_voice_provenance_never_upgraded():
    result = VoiceSafetyFilter().filter_input("check citations", InputSource.VOICE_UNCONFIRMED, .99, True)
    assert result["source"] is InputSource.VOICE_UNCONFIRMED


def test_no_activation_is_rejected():
    assert not VoiceSafetyFilter().filter_input("check citations", InputSource.VOICE_CONFIRMED, 1, False)["safe"]


def test_scope_approval_bound_to_exact_request_and_channel(chat):
    proposal = chat.handle_text("enable autonomous mode")
    assert chat.handle_voice(f"approve {proposal.proposal_id}").status == "waiting_for_approval"
    assert chat.handle_text("yes").status == "waiting_for_approval"
    assert chat.auth_manager.scoped_manager.get_active_scopes() == []
    assert chat.handle_text(f"approve {proposal.proposal_id}").status == "completed"
    assert chat.handle_text(f"approve {proposal.proposal_id}").status == "rejected"
    chat.cancel(reset_session=True)
    assert chat.auth_manager.scoped_manager.get_active_scopes() == []


def test_new_request_replaces_pending_approval(chat):
    old = chat.handle_text("enable autonomous mode")
    chat.handle_text("status")
    assert chat.handle_text(f"approve {old.proposal_id}").status == "rejected"


def setup_authority(clock=lambda: 1):
    key = object()
    manager = AuthorizationManager(control_key=key, clock=clock)
    proposal = manager.propose("edit", "WriterAgent", "thesis_writing", "chapter.tex", {"content": "draft"},
                               source_version="abc", mutating=True, control_key=key)
    return key, manager, proposal


def consume(manager, proposal, key, **overrides):
    args = dict(agent_registry=AgentPermissionRegistry(), permission="WRITE", resource="draft_files", origin="local_control",
                current_target="chapter.tex", current_version="abc", control_key=key)
    args.update(overrides)
    return manager.consume(proposal, **args)


def test_mutation_requires_approval_and_token_is_one_use():
    key, manager, proposal = setup_authority()
    assert not consume(manager, proposal, key)
    assert manager.approve(proposal, control_key=key)
    assert consume(manager, proposal, key)
    assert not consume(manager, proposal, key)


@pytest.mark.parametrize("change", [dict(target="other.tex"), dict(agent="BuildAgent"), dict(scope="compilation"),
                                  dict(payload_json='{"content":"changed"}'), dict(source_version="def")])
def test_forged_or_changed_proposal_rejected(change):
    key, manager, proposal = setup_authority()
    manager.approve(proposal, control_key=key)
    assert not consume(manager, replace(proposal, **change), key)


@pytest.mark.parametrize("overrides", [dict(current_target="elsewhere"), dict(current_version="changed"),
                                     dict(permission="EXECUTE", resource="compile")])
def test_current_target_version_and_permission_rechecked(overrides):
    key, manager, proposal = setup_authority()
    manager.approve(proposal, control_key=key)
    assert not consume(manager, proposal, key, **overrides)


def test_expiry_and_restart_revoke_authority():
    now = [1]
    key, manager, proposal = setup_authority(lambda: now[0])
    manager.approve(proposal, control_key=key)
    now[0] = 62
    assert not consume(manager, proposal, key)
    manager.end_session()
    assert not manager.approve(proposal, control_key=key)


def test_direct_or_forged_owner_cannot_append():
    ledger = AuthorizationAuditLedger()
    with pytest.raises(PermissionError):
        ledger.record_event(caller="AuthorizationManager", outcome="APPROVED")


def test_ledger_persists_without_restoring_authority_and_detects_deletion(tmp_path):
    path = tmp_path / "audit.jsonl"
    key = object()
    ledger = AuthorizationAuditLedger(owner_key=key, path=path)
    ledger.record_event(owner_key=key, outcome="SCOPES_ENABLED")
    entries = ledger.entries
    entries.clear()
    assert ledger.verify_integrity()
    restarted = AuthorizationManager(ledger_path=path)
    assert restarted.ledger.verify_integrity()
    assert restarted.scoped_manager.get_active_scopes() == []
    path.write_text("")
    assert not ledger.verify_integrity()


def test_dpapi_ledger_rejects_cold_start_rewrite_or_rollback(tmp_path):
    path = tmp_path / "audit.jsonl"
    key = object()
    ledger = AuthorizationAuditLedger(owner_key=key, path=path)
    ledger.record_event(owner_key=key, outcome="FIRST")
    first_copy = path.read_bytes()
    ledger.record_event(owner_key=key, outcome="SECOND")

    rewritten = json.loads(first_copy.decode().strip())
    rewritten["fields"]["outcome"] = "FORGED"
    body = dict(rewritten)
    body.pop("event_hash")
    body.pop("event_auth")
    rewritten["event_hash"] = AuthorizationAuditLedger._hash(body)
    path.write_text(json.dumps(rewritten) + "\n")
    assert not AuthorizationAuditLedger(path=path).verify_integrity()

    path.write_bytes(first_copy)
    assert not AuthorizationAuditLedger(path=path).verify_integrity()


def test_dpapi_ledger_rejects_cold_start_deletion(tmp_path):
    path = tmp_path / "audit.jsonl"
    key = object()
    ledger = AuthorizationAuditLedger(owner_key=key, path=path)
    ledger.record_event(owner_key=key, outcome="RECORDED")
    path.unlink()
    assert not AuthorizationAuditLedger(path=path).verify_integrity()


def test_audit_failure_blocks_dispatch(chat, tmp_path):
    from conversation_core.chat_manager import ChatManager
    path = tmp_path / "audit.jsonl"
    path.write_text("not valid json")
    broken = ChatManager(backend=chat.backend, ledger_path=path)
    called = []
    broken.backend.execute = lambda *args, **kwargs: called.append(True)
    assert broken.handle_text("check citations").status == "error"
    assert called == []


def test_preferences_corruption_or_config_change_discards_state(tmp_path):
    path = tmp_path / "prefs.json"
    recovery = JarvisStateRecovery(path)
    recovery.save_state({"a": 1}, {"language": "en", "active_scopes": ["all"], "authorization_tokens": ["x"]})
    assert recovery.recover_state({"a": 2})["recovery_status"] == "discarded"
    value = json.loads(path.read_text())
    value["preferences"]["authorization_mode"] = "AUTONOMOUS"
    path.write_text(json.dumps(value))
    assert recovery.recover_state()["safe_runtime_state"] == {"authorization_mode": "CONTROLLED_MODE"}
