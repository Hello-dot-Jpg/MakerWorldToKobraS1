class InspectorError(Exception):
    """Base class for expected, user-facing inspection failures."""


class ArchiveValidationError(InspectorError):
    """Raised when an input cannot be treated as a valid 3MF archive."""


class ProfileValidationError(InspectorError):
    """Raised when a standalone slicer profile cannot be inspected safely."""


class TargetDiscoveryError(InspectorError):
    """Raised when conversion target profiles cannot be discovered safely."""


class PlanError(InspectorError):
    """Raised when a safe conversion plan cannot be produced."""
