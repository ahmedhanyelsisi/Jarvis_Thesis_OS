class JarvisRuntimeError(Exception):
    """Base exception for Stone 24 JARVIS Runtime Layer."""
    pass

class BootSequenceError(JarvisRuntimeError):
    """Raised when critical dependencies fail to initialize."""
    pass

class SubsystemHealthError(JarvisRuntimeError):
    """Raised when a core subsystem fails health checks."""
    pass

class CommandRouterError(JarvisRuntimeError):
    """Raised when command interpretation fails or violates boundaries."""
    pass
