"""
Pyrite Exception Hierarchy

Typed exceptions for distinct error conditions, replacing generic ValueError/PermissionError.
"""


class PyriteError(Exception):
    """Base exception for all Pyrite errors."""


class EntryNotFoundError(PyriteError):
    """Raised when an entry cannot be found."""


class KBNotFoundError(PyriteError):
    """Raised when a knowledge base cannot be found."""


class KBReadOnlyError(PyriteError):
    """Raised when attempting to write to a read-only KB."""


class ValidationError(PyriteError):
    """Raised when entry data fails validation."""


class PluginError(PyriteError):
    """Raised when a plugin operation fails."""


class StorageError(PyriteError):
    """Raised when a storage operation fails."""


class ConfigError(PyriteError):
    """Raised when configuration is invalid."""
