"""Error types shared by the API routes and the logic modules."""


class ApiError(Exception):
    """An error shown to the student as {"error": {"code", "message"}}."""

    def __init__(self, status: int, code: str, message: str):
        super().__init__(message)
        self.status = status
        self.code = code
        self.message = message


class ModelUnavailable(Exception):
    """The model call failed, timed out, or returned unusable output after one retry."""


class ConfigError(Exception):
    """A required environment variable is missing."""
