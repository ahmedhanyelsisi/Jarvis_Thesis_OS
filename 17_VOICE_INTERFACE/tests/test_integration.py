import hashlib
import threading
from dataclasses import replace
import pytest
import jarvis_voice.backend as backend_module
from jarvis_voice.backend import WorkspaceBackend
from jarvis_voice.models import Recognition, Quality, assess_quality
from jarvis_voice.session import VoiceSession


def good(text="check thesis citations"):
    return Recognition(text, "en", -.1, .01, 1.1)


def test_real_workspace_result_and_source_unchanged(chat, thesis):
    before = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in thesis.iterdir()}
    reply = chat.handle_text("please check the thesis citations")
    assert reply.status == "completed"
    assert [issue["key"] for issue in reply.data["citations"]["missing_bibliography_entries"]] == ["missing"]
    assert reply.data["read_only"]
    assert before == {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in thesis.iterdir()}
    assert [item["fields"]["outcome"] for item in chat.auth_manager.ledger.entries] == ["PROPOSED", "DISPATCH_AUTHORIZED", "COMPLETED"]


def test_registry_denial_prevents_actual_dispatch(chat):
    invoked = []
    chat.agent_registry.check_permission = lambda *args: False
    chat.backend.execute = lambda *args, **kwargs: invoked.append(True)
    assert chat.handle_text("check citations").status == "rejected"
    assert invoked == []


@pytest.mark.parametrize("text", ["check chapter 3 citations", "check citations in main.tex", "check citations and delete files",
                                "don't check thesis citations", "check citations only", "check ../citations"])
def test_ambiguous_or_constrained_targets_do_not_silently_inspect_everything(chat, text):
    assert chat.handle_text(text).status == "clarification"
    assert not chat.auth_manager.ledger.entries


@pytest.mark.parametrize("text", ["compile thesis", "write chapter 3", "generate a diagram", "export thesis",
                                "find papers about transformers", "improve chapter 3 methodology"])
def test_unavailable_routes_do_not_announce_execution(chat, text):
    reply = chat.handle_text(text)
    assert reply.status == "unavailable"
    assert "Executing" not in reply.text


def test_source_change_after_prepare_rejected(thesis):
    backend = WorkspaceBackend(thesis)
    action = backend.prepare("thesis.inspect")
    (thesis / "main.tex").write_text("changed")
    with pytest.raises(ValueError, match="changed"):
        backend.execute(action)


def test_source_change_during_execution_discarded(thesis, monkeypatch):
    backend = WorkspaceBackend(thesis)
    action = backend.prepare("thesis.inspect")
    from thesis_workspace import ThesisWorkspaceManager
    original = ThesisWorkspaceManager.check_citations
    def changing(manager, structure):
        result = original(manager, structure)
        (thesis / "main.tex").write_text("changed")
        return result
    monkeypatch.setattr(ThesisWorkspaceManager, "check_citations", changing)
    with pytest.raises(ValueError, match="during"):
        backend.execute(action)


def test_platform_root_must_be_separate(thesis):
    with pytest.raises(ValueError):
        WorkspaceBackend(thesis, platform_root=thesis)
    with pytest.raises(ValueError):
        WorkspaceBackend(thesis.parent, platform_root=thesis)


def test_workspace_resource_limits(thesis):
    with pytest.raises(ValueError, match="limit"):
        WorkspaceBackend(thesis, max_files=1).prepare("thesis.inspect")
    with pytest.raises(ValueError, match="limit"):
        WorkspaceBackend(thesis, max_bytes=1).prepare("thesis.inspect")


def test_linked_file_refused(thesis, tmp_path):
    outside = tmp_path / "outside.tex"
    outside.write_text("outside")
    try:
        (thesis / "linked.tex").symlink_to(outside)
    except OSError:
        pytest.skip("Windows symlink privilege unavailable; manual junction check remains required")
    with pytest.raises(ValueError, match="Linked"):
        WorkspaceBackend(thesis).prepare("thesis.inspect")


def test_windows_drive_relative_or_unc_root_is_refused():
    with pytest.raises(ValueError, match="Drive-relative"):
        backend_module._validate_root_input("D:relative-thesis")
    with pytest.raises(ValueError, match="UNC"):
        backend_module._validate_root_input(r"\\server\share\thesis")


def test_reparse_attribute_fallback_is_refused(thesis, monkeypatch):
    original = backend_module._is_reparse_point
    monkeypatch.setattr(backend_module, "_is_reparse_point", lambda path: path.name == "main.tex" or original(path))
    with pytest.raises(ValueError, match="Linked"):
        WorkspaceBackend(thesis).prepare("thesis.inspect")


def test_voice_to_real_backend_requires_activation_and_single_use(chat):
    session = VoiceSession(chat)
    with pytest.raises(PermissionError):
        session.begin_turn()
    session.enable()
    ticket = session.begin_turn()
    assert session.accept(good(), ticket).status == "completed"
    assert session.accept(good(), ticket).status == "rejected"
    assert sum(event["fields"]["outcome"] == "COMPLETED" for event in chat.auth_manager.ledger.entries) == 1


def test_mute_discards_late_transcript_and_authority(chat):
    session = VoiceSession(chat)
    session.enable()
    ticket = session.begin_turn()
    session.mute()
    assert session.accept(good(), ticket).status == "rejected"
    assert chat.auth_manager.scoped_manager.get_active_scopes() == []


def test_expired_or_forged_ticket_rejected(chat):
    now = [0]
    session = VoiceSession(chat, clock=lambda: now[0])
    session.enable()
    ticket = session.begin_turn()
    assert session.accept(good(), replace(ticket)).status == "rejected"
    now[0] = 181
    assert session.accept(good(), ticket).status == "rejected"


def test_voice_cannot_confirm_local_pending_scopes(chat):
    proposal = chat.handle_text("enable autonomous mode")
    session = VoiceSession(chat)
    session.enable()
    ticket = session.begin_turn()
    assert session.accept(good(f"approve {proposal.proposal_id}"), ticket).status == "waiting_for_approval"
    assert chat.auth_manager.scoped_manager.get_active_scopes() == []
    assert session.text(f"approve {proposal.proposal_id}").status == "completed"


@pytest.mark.parametrize("change,expected", [({"avg_logprob": None}, Quality.UNCERTAIN),
    ({"no_speech_prob": .8}, Quality.UNCERTAIN), ({"avg_logprob": -2}, Quality.UNCERTAIN),
    ({"compression_ratio": 3}, Quality.UNCERTAIN), ({"no_speech_prob": float("nan")}, Quality.REJECT),
    ({"avg_logprob": True}, Quality.REJECT), ({"text": ""}, Quality.REJECT),
    ({"language": "ar"}, Quality.REJECT), ({"truncated": True}, Quality.REJECT), ({"final": False}, Quality.REJECT)])
def test_quality_is_not_assumed(change, expected):
    assert assess_quality(replace(good(), **change)) == expected


def test_uncertain_speech_never_dispatches(chat):
    session = VoiceSession(chat)
    session.enable()
    assert session.accept(replace(good(), avg_logprob=None), session.begin_turn()).status == "clarification"
    assert chat.auth_manager.ledger.entries == []


def test_cancel_running_real_inspection_discards_result(chat):
    original = chat.backend.execute
    entered, proceed = threading.Event(), threading.Event()
    def delayed(action, *, cancel_event):
        entered.set()
        assert proceed.wait(2)
        return original(action, cancel_event=cancel_event)
    chat.backend.execute = delayed
    session = VoiceSession(chat)
    session.enable()
    ticket = session.begin_turn()
    results = []
    thread = threading.Thread(target=lambda: results.append(session.accept(good(), ticket)))
    thread.start()
    assert entered.wait(2)
    session.cancel()
    proceed.set()
    thread.join(2)
    assert not thread.is_alive()
    assert results[0].status == "cancelled"
    assert not any(entry["fields"]["outcome"] == "COMPLETED" for entry in chat.auth_manager.ledger.entries)
