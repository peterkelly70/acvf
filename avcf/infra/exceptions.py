"""
Exception classes for the AVCF system.
"""


class AVCFError(Exception):
    """Base exception for all AVCF errors."""
    pass


class AVCFCryptoError(AVCFError):
    """Exception raised for cryptographic errors."""
    pass


class AVCFContainerError(AVCFError):
    """Exception raised for container format errors."""
    pass


class AVCFValidationError(AVCFError):
    """Exception raised for validation errors."""
    pass


class AVCFKeyError(AVCFError):
    """Exception raised for key management errors."""
    pass
