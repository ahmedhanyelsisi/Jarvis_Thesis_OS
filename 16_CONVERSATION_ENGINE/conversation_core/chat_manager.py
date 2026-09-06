"""One conversation service for local controls and untrusted voice transcripts."""
import json
import re
import threading
from .intent_engine import IntentEngine
from .context_manager import ContextManager
from .task_planner import TaskPlanner
from .response_engine import ResponseEngine
from .service_models import ChatReply
from authorization.authorization_manager import AuthorizationManager
from authorization.approval_gate import ApprovalGate
from security.voice_safety_filter import VoiceSafetyFilter, InputSource
from security.agent_permission_registry import AgentPermissionRegistry


class ChatManager:
    SCOPE_COMMANDS = frozenset(("enable autonomous mode", "approve all thesis operations",
                               "jarvis approve all", "continue without asking", "approve all"))

    def __init__(self, *, backend=None, ledger_path=None):
        self.intent_engine = IntentEngine()
        self.context_manager = ContextManager()
        self.task_planner = TaskPlanner()
        self.response_engine = ResponseEngine()
        self.__control = object()
        self.auth_manager = AuthorizationManager(control_key=self.__control, ledger_path=ledger_path)
        self.approval_gate = ApprovalGate(self.auth_manager)
        self.voice_filter = VoiceSafetyFilter()
        self.agent_registry = AgentPermissionRegistry()
        self.backend = backend
        self.pending_proposal = None
        self.__lock = threading.RLock()
        self.__cancel = threading.Event()

    def process_input(self, user_text, simulated_approval="", input_source=InputSource.TEXT,
                      confidence=None, has_wake_word=False):
        if simulated_approval:
            return "JARVIS: Simulated approval rejected; use the pending proposal's local confirmation."
        check = self.voice_filter.filter_input(user_text, input_source, confidence, has_wake_word)
        if not check["safe"]:
            return f"JARVIS: Input rejected: {check['reason']}"
        reply = self._handle(check["text"], local=input_source == InputSource.TEXT)
        return self.response_engine.generate_chat_response(reply.text)

    def handle_text(self, text):
        """Trusted local UI entry; never route worker/agent/memory messages here."""
        return self._handle(text, local=True)

    def handle_voice(self, text, *, expected_session=None):
        """Coordinator calls this only after activation, freshness and quality checks."""
        return self._handle(text, local=False, expected_session=expected_session)

    def cancel(self, *, reset_session=False):
        # No conversation lock: interrupt a running read-only inspection promptly.
        self.__cancel.set()
        self.auth_manager.cancel_pending()
        self.pending_proposal = None
        self.context_manager.pending_intent = {}
        if reset_session:
            self.auth_manager.end_session()

    def _handle(self, text, *, local, expected_session=None):
        if not isinstance(text, str) or not text.strip() or len(text) > 4096:
            return ChatReply("rejected", "Input rejected: invalid or oversized text.")
        normalized = " ".join(text.lower().strip().split()).rstrip(".!?")
        if normalized in ("cancel", "cancel request", "stop", "revoke autonomy", "disable autonomous mode"):
            self.cancel(reset_session=True)
            return ChatReply("cancelled", "Pending requests cancelled. Controlled mode is active.")
        with self.__lock:
            try:
                if expected_session is not None and expected_session != self.auth_manager.session_id:
                    return ChatReply("rejected", "Stale voice session; request discarded.")
                return self._route(text.strip(), normalized, local=local)
            except InterruptedError:
                return ChatReply("cancelled", "Inspection cancelled.")
            except (OSError, RuntimeError, ValueError, PermissionError) as exc:
                self.cancel(reset_session=True)
                return ChatReply("error", f"Request could not complete: {exc}")

    def _route(self, text, normalized, *, local):
        if normalized in ("yes", "approve", "go ahead") or normalized.startswith("approve ") and normalized not in self.SCOPE_COMMANDS:
            proposal = self.pending_proposal
            if proposal is None:
                return ChatReply("rejected", "No pending proposal matches that approval.")
            if not local:
                return ChatReply("waiting_for_approval", "Use the local text control to confirm this proposal.", proposal.proposal_id)
            expected = f"approve {proposal.proposal_id}"
            if normalized != expected:
                return ChatReply("waiting_for_approval", f"Confirm the exact proposal with: {expected}", proposal.proposal_id)
            if not self.auth_manager.approve(proposal, control_key=self.__control):
                self.pending_proposal = None
                return ChatReply("rejected", "Proposal expired or changed; please request it again.")
            if proposal.capability == "scope.enable":
                scopes = json.loads(proposal.payload_json)["scopes"]
                success = self.auth_manager.enable_autonomous_mode("enable autonomous mode", scopes,
                    control_key=self.__control, proposal=proposal)
                self.pending_proposal = None
                return ChatReply("completed" if success else "rejected",
                                 "Session scopes enabled for 15 minutes. Unavailable capabilities remain disabled."
                                 if success else "Scope activation rejected.")
            return ChatReply("unavailable", "This proposal has no executable capability.")

        # A new request cannot inherit an old target or approval.
        self.auth_manager.cancel_pending()
        self.pending_proposal = None
        if normalized in self.SCOPE_COMMANDS:
            self.context_manager.pending_intent = {}
            if not local:
                return ChatReply("rejected", "Voice cannot enable autonomy. Use the local text control to review scopes.")
            scopes = ["thesis_writing", "research", "review", "compilation"]
            proposal = self.auth_manager.propose("scope.enable", "LocalUser", "authorization", "session",
                         {"scopes": scopes}, mutating=True, control_key=self.__control)
            self.pending_proposal = proposal
            return ChatReply("waiting_for_approval",
                             "Proposed 15-minute scopes: " + ", ".join(scopes)
                             + f". Confirm with: approve {proposal.proposal_id}", proposal.proposal_id)

        if normalized in ("status", "help", "what can you do", "show status", "jarvis status"):
            self.context_manager.pending_intent = {}
            return ChatReply("completed", "Read-only thesis inspection is " + ("available." if self.backend else "unavailable: configure a thesis root.")
                             + " Writing, research generation, compilation and export are unavailable in Stone 26.",
                             data={"inspection_available": self.backend is not None,
                                   "active_scopes": self.auth_manager.scoped_manager.get_active_scopes()})

        inspection = re.search(r"\b(inspect|check|scan|analyze|analyse)\b.*\b(thesis|citations?|references?|bibliography|structure)\b", normalized)
        if inspection:
            self.context_manager.pending_intent = {}
            if re.search(r"\b(don't|never|write|delete|compile|export|run)\b|\bdo not\b", normalized):
                return ChatReply("clarification", "Please request one read-only inspection explicitly.")
            if re.search(r"\bchapter\b|[/\\]|\.tex\b|\b(?:only|except)\b", normalized):
                return ChatReply("clarification", "This inspection covers the configured thesis. Ask 'check thesis citations' for the whole workspace.")
            if self.backend is None:
                return ChatReply("unavailable", "Thesis inspection is unavailable: configure an explicit thesis root.")
            self.__cancel.clear()
            action = self.backend.prepare("thesis.inspect")
            proposal = self.auth_manager.propose(action.capability, action.agent, action.scope, action.target,
                         json.loads(action.payload_json), source_version=action.source_version,
                         mutating=action.mutating, control_key=self.__control)
            current_target, current_version = self.backend.current_binding(action)
            if self.__cancel.is_set():
                raise InterruptedError()
            allowed = self.auth_manager.consume(proposal, agent_registry=self.agent_registry,
                        permission=action.permission, resource=action.resource, origin="local_text" if local else "voice",
                        current_target=current_target, current_version=current_version, control_key=self.__control)
            if not allowed:
                return ChatReply("rejected", "Blocked by AgentPermissionRegistry or stale authorization.")
            try:
                result = self.backend.execute(action, cancel_event=self.__cancel)
                if self.__cancel.is_set():
                    raise InterruptedError()
                self.auth_manager.record("COMPLETED", proposal=proposal)
            except Exception as exc:
                self.auth_manager.record("CANCELLED" if isinstance(exc, InterruptedError) else "FAILED", proposal=proposal)
                raise
            return ChatReply("completed", result["summary"], data=result)

        intent = self.intent_engine.parse_intent(text)
        if self.context_manager.pending_intent and intent.get("task") == "unknown":
            intent = self.context_manager.resolve_pending_intent(text)
        elif intent.get("task") != "unknown":
            self.context_manager.pending_intent = {}
        if intent.get("task") != "unknown" and intent.get("status") == "ambiguous":
            return ChatReply("clarification", self.context_manager.generate_clarification_prompt(intent))
        if intent.get("status") == "resolved":
            workflow = self.task_planner.build_workflow(intent)
            for step in workflow.get("steps", []):
                if not self.agent_registry.check_permission(step.get("agent"), "EXECUTE", step.get("action", "")):
                    return ChatReply("unavailable", "Blocked by AgentPermissionRegistry: this academic workflow has no validated executable capability.")
            return ChatReply("unavailable", "This academic workflow is not connected to an executor.")
        if re.search(r"\b(write|compile|export|draft|research|generate|delete|run)\b", normalized):
            return ChatReply("unavailable", "That action is unavailable in Stone 26. No files were changed.")
        return ChatReply("unknown", "I didn't understand that request. Try 'check thesis citations' or 'status'.")
