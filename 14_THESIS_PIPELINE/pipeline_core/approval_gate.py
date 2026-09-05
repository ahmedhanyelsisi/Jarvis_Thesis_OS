import uuid
from typing import Dict, Optional
from .models import ApprovalRequest
from .exceptions import ApprovalError

class ApprovalGate:
    """Manages strict human-in-the-loop checkpoints."""
    
    def __init__(self):
        self._pending_requests: Dict[str, ApprovalRequest] = {}

    def create_request(self, target_state: str, context: str) -> ApprovalRequest:
        req = ApprovalRequest(
            request_id=str(uuid.uuid4()),
            target_state=target_state,
            context=context,
            secure_token=str(uuid.uuid4())
        )
        self._pending_requests[req.request_id] = req
        return req

    def process_approval(self, request_id: str, provided_token: str) -> bool:
        """Validates the approval using the secure token."""
        if request_id not in self._pending_requests:
            raise ApprovalError(f"Approval request {request_id} not found.")
            
        req = self._pending_requests[request_id]
        if req.secure_token != provided_token:
            raise ApprovalError("Fake approval injection detected: Invalid secure token.")
            
        # Clear it once approved to prevent replay attacks
        del self._pending_requests[request_id]
        return True

    def has_pending(self) -> bool:
        return len(self._pending_requests) > 0
