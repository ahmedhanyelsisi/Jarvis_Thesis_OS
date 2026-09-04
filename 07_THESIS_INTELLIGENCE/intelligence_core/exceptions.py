class IntelligenceLayerError(Exception):
    """Base exception for the Intelligence Layer."""
    pass

class AgentNotFoundError(IntelligenceLayerError):
    """Raised when a message is routed to an unregistered agent role."""
    pass

class SandboxViolationError(IntelligenceLayerError):
    """Raised when an agent attempts to bypass the AgentContext sandbox."""
    pass

class AgentRuntimeError(IntelligenceLayerError):
    """Raised when an agent crashes during execution."""
    pass

class LLMGatewayError(IntelligenceLayerError):
    """Raised when the LLM call fails within the gateway."""
    pass

class MemoryGatewayError(IntelligenceLayerError):
    """Raised when the memory query fails within the gateway."""
    pass
