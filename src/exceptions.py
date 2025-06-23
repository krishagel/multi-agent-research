"""Custom exceptions for the research system."""

class ResearchSystemError(Exception):
    """Base exception for all research system errors."""
    pass

class ConfigurationError(ResearchSystemError):
    """Raised when there's a configuration issue."""
    pass

class APIError(ResearchSystemError):
    """Base class for API-related errors."""
    pass

class TavilyAPIError(APIError):
    """Raised when Tavily API encounters an error."""
    pass

class BedrockAPIError(APIError):
    """Raised when AWS Bedrock API encounters an error."""
    pass

class RateLimitError(APIError):
    """Raised when API rate limits are exceeded."""
    pass

class DatabaseError(ResearchSystemError):
    """Raised when database operations fail."""
    pass

class ValidationError(ResearchSystemError):
    """Raised when input validation fails."""
    pass

class SecurityError(ResearchSystemError):
    """Raised when security checks fail."""
    pass

class ResearchQualityError(ResearchSystemError):
    """Raised when research quality is below threshold."""
    pass