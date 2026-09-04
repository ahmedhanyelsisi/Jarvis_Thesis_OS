"""Stone 8 cognitive command center and compatibility tests."""

from __future__ import annotations

import importlib
from pathlib import Path
from typing import Any

import cognitive_ui
from cognitive_ui import (
    AGENT_COMPLETED,
    AGENT_STARTED,
    COMMAND_RECEIVED,
    MEMORY_UPDATED,
    RESPONSE_READY,
    WORKFLOW_STARTED,
    CommandCenter,
    DashboardMetrics,
    EventBus,
    SessionStore,
    SessionState,
    UIManager,
    is_unsafe_action,
    validate_command,
)
from jarvis import Jarvis


class RecordingJarvis:
    def __init__(self) -> None:
        self.requests: list[str] = []
        self.workflows: list[tuple[str, bool]] = []

    def process_request(self, request: str) -> dict[str, Any]:
        self.requests.append(request)
        return {
            "status": "completed",
            "agent": "thesis_writer_agent",
            "result": f"Drafted: {request}",
        }

    def process_workflow(
        self,
        request: str,
        evaluate: bool = True,
    ) -> dict[str, Any]:
        self.workflows.append((request, evaluate))
        return {
            "tasks": [
                {
                    "id": "task-1",
                    "description": request,
                    "required_agent": "thesis_writer_agent",
                    "status": "COMPLETED",
                }
            ],
            "workflow": {
                "workflow_id": "workflow-1",
                "current_task": None,
                "completed_tasks": ["task-1"],
                "failed_tasks": [],
                "skipped_tasks": [],
            },
            "final_response": "Draft ready",
        }

    def get_system_status(self) -> dict[str, Any]:
        return {
            "kernel": "active",
            "agents": 6,
            "memory": "active",
            "voice": "disabled",
            "workflow": "ready",
        }


def _kernel_config(tmp_path: Path) -> dict[str, Any]:
    return {
        "knowledge": {"enabled": False},
        "memory": {
            "enabled": False,
            "database_path": str(tmp_path / "memory.sqlite"),
        },
        "reasoning": {
            "enabled": True,
            "memory_path": str(tmp_path / "reasoning.json"),
        },
        "planner": {"enabled": True},
        "evaluation": {"enabled": False},
        "voice": {"enabled": False},
    }


def test_cognitive_ui_package_imports():
    assert importlib.import_module("cognitive_ui") is cognitive_ui
    assert cognitive_ui.UIEvent is not None
    assert cognitive_ui.SystemStatus is not None


def test_command_center_can_be_created_with_shared_ui_state():
    state = SessionState()
    bus = EventBus()

    center = CommandCenter(RecordingJarvis(), state, bus)

    assert center.session_state is state
    assert center.event_bus is bus
    assert state.active_session


def test_mock_command_reaches_jarvis_and_updates_session_state():
    kernel = RecordingJarvis()
    center = CommandCenter(kernel)

    result = center.send_command("Jarvis write my thesis introduction")

    assert kernel.requests == ["Jarvis write my thesis introduction"]
    assert result["status"] == "completed"
    assert result["response"]["result"].startswith("Drafted:")
    assert center.state.current_task is None
    assert center.state.last_response == result["response"]
    assert center.state.active_agents == {}


def test_request_events_are_emitted_in_routing_order():
    center = CommandCenter(RecordingJarvis())

    center.send_command("Write an introduction")

    assert [event.event_type for event in center.event_bus.history] == [
        COMMAND_RECEIVED,
        AGENT_STARTED,
        AGENT_COMPLETED,
        RESPONSE_READY,
    ]


def test_workflow_status_and_workflow_events_are_projected():
    kernel = RecordingJarvis()
    ui = UIManager(kernel)

    result = ui.handle_command(
        "Write and review an introduction",
        workflow=True,
        evaluate=False,
    )

    assert kernel.workflows == [("Write and review an introduction", False)]
    assert ui.session_state.workflow_status.status == "completed"
    assert ui.session_state.workflow_status.workflow_id == "workflow-1"
    assert [event.event_type for event in ui.event_bus.history] == [
        COMMAND_RECEIVED,
        WORKFLOW_STARTED,
        AGENT_STARTED,
        AGENT_COMPLETED,
        MEMORY_UPDATED,
        RESPONSE_READY,
    ]
    assert result["session"]["workflow_status"]["completed_tasks"] == [
        "task-1"
    ]


def test_system_status_is_returned_through_command_center():
    center = CommandCenter(RecordingJarvis())

    status = center.get_system_status()
    result = center.send_command("Write an introduction")

    assert status == result["system_status"]
    assert status == {
        "kernel": "active",
        "agents": 6,
        "memory": "active",
        "voice": "disabled",
        "workflow": "ready",
    }


def test_jarvis_exposes_additive_system_status(tmp_path: Path):
    jarvis = Jarvis(config=_kernel_config(tmp_path))

    status = jarvis.get_system_status()

    assert status["kernel"] == "active"
    assert status["agents"] == len(jarvis.agent_manager.list_agents())
    assert status["memory"] == "disabled"
    assert status["voice"] == "disabled"
    assert status["workflow"] == "ready"
    jarvis.close()


def test_stones_4_through_7_public_kernel_paths_remain_available(tmp_path: Path):
    """The UI is additive and leaves prior managers and calls in place."""

    jarvis = Jarvis(config=_kernel_config(tmp_path))

    assert hasattr(jarvis, "knowledge")
    assert jarvis.memory_manager is not None
    assert jarvis.reasoning_engine is not None
    assert hasattr(jarvis, "process_request")
    assert hasattr(jarvis, "process_workflow")
    assert hasattr(jarvis, "process_voice_command")
    assert jarvis.process_request("Create a diagram")["status"] == "completed"
    jarvis.close()


def test_session_persistence_round_trip_update_and_clear(tmp_path: Path):
    state = SessionState()
    state.begin_task("Write chapter 3")
    state.finish_task({"result": "draft"})

    with SessionStore(tmp_path / "ui.sqlite") as store:
        session_id = store.save_session(state)
        loaded = store.load_session(session_id)
        assert loaded is not None
        assert loaded.active_session == state.active_session
        assert loaded.last_response == {"result": "draft"}
        store.update_session(session_id, {"last_response": {"result": "revised"}})
        assert store.load_session(session_id).last_response == {"result": "revised"}
        assert store.clear_session(session_id) == 1
        assert store.load_session(session_id) is None


def test_event_has_identity_source_payload_metadata_and_history_filter():
    bus = EventBus()
    event = bus.emit(
        "command_received",
        {"command": "write"},
        source="command_center",
        metadata={"mode": "request"},
    )

    assert event.event_id
    assert event.timestamp.tzinfo is not None
    assert event.source == "command_center"
    assert event.payload == {"command": "write"}
    assert event.metadata == {"mode": "request"}
    assert bus.get_history("command_received") == (event,)
    assert bus.retrieve_event_history("missing") == ()


def test_dashboard_metrics_update_success_and_failure():
    metrics = DashboardMetrics()
    metrics.record_request(workflow=True, successful=True, duration=2.0, active_agents=1)
    snapshot = metrics.record_request(workflow=True, successful=False, duration=4.0)

    assert snapshot.total_requests == 2
    assert snapshot.successful_workflows == 1
    assert snapshot.failed_workflows == 1
    assert snapshot.active_agents == 0
    assert snapshot.average_execution_duration == 3.0
    assert snapshot.last_execution_time is not None


def test_command_center_extracts_deterministic_intent_target_and_agent():
    parsed = CommandCenter.extract_intent("Jarvis continue thesis chapter 3")

    assert parsed == {
        "intent": "continue_writing",
        "target": "chapter 3",
        "agent": "latex_agent",
    }


def test_security_validation_blocks_unsafe_commands_without_confirmation():
    assert is_unsafe_action("delete the temporary draft")
    blocked = validate_command("delete the temporary draft")
    allowed = validate_command("delete the temporary draft", confirmed=True)

    assert blocked.valid is False
    assert blocked.requires_confirmation is True
    assert allowed.valid is True

    kernel = RecordingJarvis()
    result = CommandCenter(kernel).send_command("delete chapter 3")
    assert result["status"] == "blocked"
    assert kernel.requests == []
