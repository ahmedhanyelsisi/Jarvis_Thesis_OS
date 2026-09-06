"""Compatibility facade: simulated responses can no longer authorize dispatch."""


class ApprovalGate:
    def __init__(self, auth_manager):
        self.auth_manager = auth_manager

    def request_approval(self, workflow_description, scope="thesis_writing", action="",
                         critical=False, simulated_user_response="", user_command=""):
        return False  # use the manager's session-bound proposal API
