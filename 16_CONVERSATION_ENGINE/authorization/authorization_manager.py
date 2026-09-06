"""Session-bound proposals and one-time authorization at the dispatch boundary."""
import hashlib
import json
import threading
import time
import uuid
from dataclasses import dataclass
from security.authorization_audit_ledger import AuthorizationAuditLedger
from security.scoped_autonomous_manager import ScopedAutonomousManager


@dataclass(frozen=True)
class ActionProposal:
    proposal_id: str
    session_id: str
    capability: str
    agent: str
    scope: str
    target: str
    payload_json: str
    source_version: str
    mutating: bool
    expires_at: float

    @property
    def digest(self):
        return hashlib.sha256(json.dumps(self.__dict__, sort_keys=True, allow_nan=False).encode()).hexdigest()


class AuthorizationManager:
    def __init__(self, *, control_key=None, ledger_path=None, clock=time.monotonic):
        self.__control = control_key if control_key is not None else object()
        self.__owner = object()
        self.__clock = clock
        self.__lock = threading.RLock()
        self.session_id = str(uuid.uuid4())
        self.ledger = AuthorizationAuditLedger(owner_key=self.__owner, path=ledger_path)
        self.scoped_manager = ScopedAutonomousManager(owner_key=self.__owner, clock=clock)
        self.__pending = {}
        self.__granted = set()

    def _require_control(self, key):
        if key is not self.__control:
            raise PermissionError("Local control authority required")

    def record(self, outcome, *, proposal=None, origin="system", detail=""):
        fields = {"session_id": self.session_id, "outcome": outcome, "origin": origin, "detail": detail}
        if proposal:
            fields.update(proposal_id=proposal.proposal_id, capability=proposal.capability,
                          agent=proposal.agent, scope=proposal.scope,
                          target_digest=hashlib.sha256(proposal.target.encode()).hexdigest(),
                          proposal_digest=proposal.digest)
        return self.ledger.record_event(owner_key=self.__owner, **fields)

    def propose(self, capability, agent, scope, target, payload=None, *, source_version="", mutating=False, control_key=None):
        self._require_control(control_key)
        with self.__lock:
            self.__pending.clear()
            self.__granted.clear()
            proposal = ActionProposal(str(uuid.uuid4()), self.session_id, capability, agent, scope,
                                      target, json.dumps(payload or {}, sort_keys=True, allow_nan=False),
                                      source_version, mutating, self.__clock() + 60)
            self.record("PROPOSED", proposal=proposal)
            self.__pending[proposal.proposal_id] = proposal
            return proposal

    def _live(self, proposal):
        return (isinstance(proposal, ActionProposal) and proposal.session_id == self.session_id
                and self.__pending.get(proposal.proposal_id) == proposal
                and self.__clock() < proposal.expires_at)

    def approve(self, proposal, *, control_key=None):
        self._require_control(control_key)
        with self.__lock:
            if not self._live(proposal):
                return False
            self.record("APPROVED_LOCAL", proposal=proposal, origin="local_control")
            self.__granted.add(proposal.digest)
            return True

    def consume(self, proposal, *, agent_registry, permission, resource, origin,
                current_target, current_version, control_key=None):
        self._require_control(control_key)
        with self.__lock:
            allowed = (self._live(proposal) and current_target == proposal.target
                       and current_version == proposal.source_version
                       and agent_registry.check_permission(proposal.agent, permission, resource)
                       and (not proposal.mutating or proposal.digest in self.__granted))
            if not allowed:
                self.record("DENIED", proposal=proposal, origin=origin)
                return False
            self.record("DISPATCH_AUTHORIZED", proposal=proposal, origin=origin)
            self.__pending.pop(proposal.proposal_id, None)
            self.__granted.discard(proposal.digest)
            return True

    def enable_autonomous_mode(self, explicit_command, scopes=None, *, control_key=None, proposal=None):
        if control_key is not self.__control:
            return False
        with self.__lock:
            if (proposal is None or not self._live(proposal) or proposal.capability != "scope.enable"
                    or proposal.digest not in self.__granted):
                return False
            requested = list(scopes or [])
            if json.loads(proposal.payload_json).get("scopes") != requested:
                return False
            self.record("SCOPES_ENABLED", proposal=proposal, origin="local_control")
            success = self.scoped_manager.enable_scopes(requested, owner_key=self.__owner)
            self.__pending.pop(proposal.proposal_id, None)
            self.__granted.discard(proposal.digest)
            return success

    def is_autonomous_for_scope(self, scope, action=""):
        return not self.scoped_manager.is_action_blocked(action) and self.scoped_manager.is_scope_active(scope)

    def cancel_pending(self):
        with self.__lock:
            self.__pending.clear()
            self.__granted.clear()

    def end_session(self):
        with self.__lock:
            self.cancel_pending()
            self.scoped_manager.reset()
            self.session_id = str(uuid.uuid4())

    def log_workflow_approval(self, user_command, intent, scope, result):
        return self.record(result, detail=f"{intent}:{scope}")
