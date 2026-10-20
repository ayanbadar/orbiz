"""Domain exceptions raised by services. Mapped to HTTP in the exception handler."""


class ApplicationError(Exception):
    """Expected, user-facing failure. Maps to 400 unless a subclass says otherwise."""

    status_code = 400
    default_code = "application_error"

    def __init__(self, message: str, *, extra: dict | None = None, code: str | None = None):
        super().__init__(message)
        self.message = message
        self.extra = extra or {}
        self.code = code or self.default_code


class NotFoundError(ApplicationError):
    status_code = 404
    default_code = "not_found"


class ConflictError(ApplicationError):
    status_code = 409
    default_code = "conflict"


class ServiceUnavailableError(ApplicationError):
    status_code = 503
    default_code = "service_unavailable"


class BadGatewayError(ApplicationError):
    status_code = 502
    default_code = "bad_gateway"
