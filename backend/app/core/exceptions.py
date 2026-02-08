from __future__ import annotations


class AppException(Exception):
    """Base exception for all application-level errors.

    Attributes:
        message: Human-readable error description.
        status_code: HTTP status code to return.
        error_code: Machine-readable error identifier.
        detail: Optional additional context.
    """

    def __init__(
        self,
        message: str = "An unexpected error occurred",
        status_code: int = 500,
        error_code: str = "INTERNAL_ERROR",
        detail: dict[str, object] | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.error_code = error_code
        self.detail = detail or {}

    def to_dict(self) -> dict[str, object]:
        """Serialise the exception to a JSON-friendly dict."""
        payload: dict[str, object] = {
            "error": self.error_code,
            "message": self.message,
        }
        if self.detail:
            payload["detail"] = self.detail
        return payload


class NotFoundException(AppException):
    """Raised when a requested resource does not exist."""

    def __init__(
        self,
        resource: str = "Resource",
        identifier: str = "",
        detail: dict[str, object] | None = None,
    ) -> None:
        message = f"{resource} not found"
        if identifier:
            message = f"{resource} '{identifier}' not found"
        super().__init__(
            message=message,
            status_code=404,
            error_code="NOT_FOUND",
            detail=detail,
        )


class ValidationException(AppException):
    """Raised when request data fails validation."""

    def __init__(
        self,
        message: str = "Validation error",
        errors: list[dict[str, object]] | None = None,
        detail: dict[str, object] | None = None,
    ) -> None:
        merged_detail: dict[str, object] = dict(detail) if detail else {}
        if errors:
            merged_detail["errors"] = errors
        super().__init__(
            message=message,
            status_code=422,
            error_code="VALIDATION_ERROR",
            detail=merged_detail,
        )


class ServiceUnavailableException(AppException):
    """Raised when an upstream dependency is unreachable."""

    def __init__(
        self,
        service: str = "External service",
        detail: dict[str, object] | None = None,
    ) -> None:
        super().__init__(
            message=f"{service} is currently unavailable",
            status_code=503,
            error_code="SERVICE_UNAVAILABLE",
            detail=detail,
        )
