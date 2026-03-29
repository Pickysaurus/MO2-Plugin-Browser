class NexusModsAPIError(Exception):
    """Base class for all Nexus API issues."""
    pass

class NexusModsAuthError(NexusModsAPIError):
    """Raised for 401/403 errors (Invalid/Missing API Key)."""
    pass

class NexusModsRateLimitError(NexusModsAPIError):
    """Raised for 429 errors."""
    pass

class NexusModsNetworkError(NexusModsAPIError):
    """Raised for transport issues (DNS, Timeout, No Internet)."""
    pass

class NexusModsAPIKeyMissingError(NexusModsAPIError):
    """Raised if the user's API key is not present"""
    pass