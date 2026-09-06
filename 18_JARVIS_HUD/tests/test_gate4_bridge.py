from bridge import RuntimeBridge
from bridge.runtime_bridge import HudEventAdapter
from bridge.runtime_event_adapter import RuntimeEventAdapter
from bridge.runtime_event_adapter import RuntimePresentationEvent


def _wait_for(qtbot, bridge, predicate):
    qtbot.waitUntil(lambda: predicate(bridge), timeout=3000)


def test_real_local_status_request_returns_a_conversation_reply(qtbot):
    bridge = RuntimeBridge()
    try:
        bridge.submitText("status")
        _wait_for(qtbot, bridge, lambda item: len(item.messages) >= 3)
        assert bridge.messages[-1]["role"] == "JARVIS"
        assert "Read-only thesis inspection" in bridge.messages[-1]["text"]
        assert bridge.coreState == "COMPLETED"
    finally:
        bridge.close()


def test_approval_is_session_bound_and_exact_proposal_id_only(qtbot):
    bridge = RuntimeBridge()
    try:
        bridge.submitText("enable autonomous mode")
        _wait_for(qtbot, bridge, lambda item: bool(item.approval))
        proposal_id = bridge.approval["proposal_id"]
        bridge.approveProposal("wrong-proposal-id")
        assert bridge.coreState == "ERROR"
        assert "does not match" in bridge.errorSummary
        bridge.approveProposal(proposal_id)
        _wait_for(qtbot, bridge, lambda item: item.coreState == "COMPLETED")
        assert bridge.autonomy["mode"] == "AUTONOMOUS"
        bridge.approveProposal(proposal_id)
        assert bridge.coreState == "ERROR"
    finally:
        bridge.close()


def test_cancel_clears_authoritative_pending_request(qtbot):
    bridge = RuntimeBridge()
    try:
        bridge.submitText("enable autonomous mode")
        _wait_for(qtbot, bridge, lambda item: bool(item.approval))
        bridge.cancelCurrent()
        assert bridge.approval == {}
        assert bridge.coreState == "IDLE"
        assert bridge.autonomy["mode"] == "CONTROLLED"
    finally:
        bridge.close()


def test_malformed_request_is_rejected_before_conversation_execution(qtbot):
    bridge = RuntimeBridge()
    try:
        bridge.submitText(" ")
        assert bridge.coreState == "ERROR"
        assert "Request rejected" in bridge.errorSummary
    finally:
        bridge.close()


def test_session_mismatch_rejects_a_real_pending_proposal(qtbot):
    bridge = RuntimeBridge()
    try:
        bridge.submitText("enable autonomous mode")
        _wait_for(qtbot, bridge, lambda item: bool(item.approval))
        proposal_id = bridge.approval["proposal_id"]
        bridge._pending["session_id"] = "stale-session"  # controlled bridge fixture
        bridge.approveProposal(proposal_id)
        assert bridge.coreState == "ERROR"
        assert "different session" in bridge.errorSummary
    finally:
        bridge.close()


def test_bounded_event_adapter_preserves_terminal_event_behavior():
    adapter = HudEventAdapter(maxsize=1)
    first = adapter.normalize("progress", session_id="s", correlation_id="a")
    terminal = adapter.normalize("completed", session_id="s", correlation_id="b")
    assert adapter.offer(first)
    assert adapter.offer(terminal)
    assert adapter.drain() == [first, terminal]


def test_runtime_event_adapter_rejects_unknown_and_malformed_events():
    received = []
    adapter = RuntimeEventAdapter("session-a", received.append)
    assert not adapter.accept("agent.unknown", {})
    assert not adapter.accept("agent.started", {"agent_id": ["not-a-string"]})
    assert adapter.accept("workflow.started", {"workflow_id": "wf-1"})
    assert received[0].workflow_id == "wf-1"
    assert received[0].agent_id is None


def test_runtime_event_adapter_maps_only_explicit_agent_identity():
    received = []
    adapter = RuntimeEventAdapter("session-a", received.append)
    assert adapter.accept("agent.started", {"task_id": "wf_task"})
    assert received[-1].agent_id is None
    assert adapter.accept("agent.started", {"agent_id": "ResearchAgent"})
    assert received[-1].agent_id == "research"


def test_foreign_runtime_event_cannot_mutate_bridge_state(qtbot):
    bridge = RuntimeBridge()
    try:
        bridge._runtime_event.emit(RuntimePresentationEvent(
            "workflow.started", 1, 0, "foreign-session", "wf-1", None,
            "frozen_runtime_event_bus", {},
        ))
        assert bridge.coreState == "IDLE"
    finally:
        bridge.close()


def test_live_runtime_boot_exposes_frozen_health_and_closes(qtbot):
    bridge = RuntimeBridge(live_runtime=True)
    try:
        qtbot.waitUntil(lambda: any(
            row["label"] == "RUNTIME" and row["value"] == "ONLINE"
            for row in bridge.healthRows
        ), timeout=10000)
        assert any(row["label"] == "EVENT BUS" and row["value"] == "ONLINE"
                   for row in bridge.healthRows)
    finally:
        bridge.close()


def test_expired_hud_proposal_is_rejected_by_frozen_authority(qtbot):
    bridge = RuntimeBridge()
    try:
        bridge.submitText("enable autonomous mode")
        _wait_for(qtbot, bridge, lambda item: bool(item.approval))
        proposal_id = bridge.approval["proposal_id"]
        bridge._chat.auth_manager._AuthorizationManager__clock = lambda: float("inf")
        bridge.approveProposal(proposal_id)
        _wait_for(qtbot, bridge, lambda item: item.coreState == "ERROR")
        assert "expired" in bridge.messages[-1]["text"].lower()
    finally:
        bridge.close()


def test_terminal_workflow_is_not_revived_by_late_start_event(qtbot):
    bridge = RuntimeBridge()
    session = bridge._chat.auth_manager.session_id
    try:
        bridge._runtime_event.emit(RuntimePresentationEvent(
            "workflow.completed", 1, 0, session, "wf-1", None,
            "frozen_runtime_event_bus", {},
        ))
        assert bridge.coreState == "COMPLETED"
        bridge._runtime_event.emit(RuntimePresentationEvent(
            "workflow.started", 2, 0, session, "wf-1", None,
            "frozen_runtime_event_bus", {},
        ))
        assert bridge.coreState == "COMPLETED"
    finally:
        bridge.close()


def test_cancel_after_terminal_does_not_claim_cancellation(qtbot):
    bridge = RuntimeBridge()
    try:
        bridge.submitText("status")
        _wait_for(qtbot, bridge, lambda item: item.coreState == "COMPLETED")
        bridge.cancelCurrent()
        assert bridge.coreState == "COMPLETED"
        assert "No pending authorization" in bridge.messages[-1]["text"]
    finally:
        bridge.close()


def test_prototype_mode_cannot_boot_live_runtime(qtbot):
    bridge = RuntimeBridge(prototype_mode=True, live_runtime=True)
    try:
        assert bridge.prototypeMode
        assert bridge._runtime is None
        assert bridge.healthRows[2]["value"] == "UNCONFIGURED"
    finally:
        bridge.close()
