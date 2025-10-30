class DiscordCliError(Exception):
    """Base exception for the Discord CLI bot."""


class ConfigurationError(DiscordCliError):
    """Raised when the provided configuration is invalid."""


class DiscordOperationError(DiscordCliError):
    """Raised when an operation against Discord's API fails."""


class RateLimitError(DiscordCliError):
    """Raised when rate limit handling exhausts all retries."""
