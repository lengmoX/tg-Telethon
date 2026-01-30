"""
Custom Exceptions for TGF
"""


class TGFError(Exception):
    """Base exception for TGF"""
    pass


class ConfigError(TGFError):
    """Configuration related errors"""
    pass


class AuthError(TGFError):
    """Authentication related errors"""
    pass


class ForwardError(TGFError):
    """Forwarding related errors"""
    pass


class ChatNotFoundError(ForwardError):
    """Chat/channel not found error"""
    pass


class MediaDownloadError(ForwardError):
    """Media download error"""
    pass


class MediaUploadError(ForwardError):
    """Media upload error"""
    pass


class RateLimitError(TGFError):
    """Rate limit exceeded error"""
    
    def __init__(self, message: str, wait_seconds: int = 0):
        super().__init__(message)
        self.wait_seconds = wait_seconds


class RestrictedChannelError(ForwardError):
    """Channel restricts forwarding"""
    pass
