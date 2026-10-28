"""Exceptions for the MyWebLog API client.

These exceptions map directly to HTTP error status codes, RFC 9457 Problem Details
(application/problem+json), and RFC 6749 OAuth 2.0 error responses.
"""

from __future__ import annotations

from typing import Any


class MyWebLogError(Exception):
    """Base exception for all MyWebLog API errors."""

    def __init__(
        self,
        message: str | None = None,
        status: int | None = None,
        code: int | None = None,
        title: str | None = None,
        request_id: str | None = None,
        errors: list[Any] | None = None,
        detail: str | None = None,
    ) -> None:
        """Initialize MyWebLogError."""
        self.status = status
        self.code = code
        self.title = title
        self.request_id = request_id
        self.errors = errors
        self.detail = detail

        if not message:
            parts = []
            if status is not None:
                parts.append(f"HTTP {status}")
            if title:
                parts.append(title)
            if detail and detail != title:
                parts.append(f"({detail})")
            if errors:
                parts.append(f"errors: {errors}")
            if code is not None:
                parts.append(f"[code: {code}]")
            if request_id:
                parts.append(f"[req: {request_id}]")
            message = " - ".join(parts) if parts else "Unknown MyWebLog error"

        super().__init__(message)


class MyWebLogAuthError(MyWebLogError):
    """Raised on authentication failures (HTTP 401 or OAuth2 error response)."""


class MyWebLogForbiddenError(MyWebLogError):
    """Raised when access is forbidden (HTTP 403, e.g. code 10002 / 10302)."""


class MyWebLogNotFoundError(MyWebLogError):
    """Raised when a resource or endpoint is not found (HTTP 404)."""


class MyWebLogRateLimitError(MyWebLogError):
    """Raised when API rate limit is exceeded (HTTP 429)."""

    def __init__(
        self,
        message: str | None = None,
        retry_after: int | None = None,
        **kwargs: Any,
    ) -> None:
        """Initialize MyWebLogRateLimitError with optional retry_after in seconds."""
        self.retry_after = retry_after
        if not message and retry_after is not None:
            kwargs.setdefault("detail", f"Retry after {retry_after}s")
        super().__init__(message, **kwargs)


class MyWebLogMaintenanceError(MyWebLogError):
    """Raised when MyWebLog is closed for maintenance (HTTP 503, code 10060)."""

    def __init__(
        self,
        message: str | None = None,
        retry_after: int | None = None,
        **kwargs: Any,
    ) -> None:
        """Initialize MyWebLogMaintenanceError with optional retry_after in seconds."""
        self.retry_after = retry_after
        if not message and retry_after is not None:
            kwargs.setdefault(
                "detail",
                f"Maintenance in progress. Retry after {retry_after}s",
            )
        super().__init__(message, **kwargs)


def parse_problem_response(
    status: int,
    data: dict[str, Any] | str | None,
    request_id: str | None = None,
    retry_after: int | None = None,
) -> MyWebLogError:
    """Parse an HTTP error response into the appropriate MyWebLogError subclass.

    Handles RFC 9457 Problem Details (application/problem+json), RFC 6749 OAuthError,
    or raw string/empty responses.
    """
    title: str | None = None
    detail: str | None = None
    code: int | None = None
    errors: list[Any] | None = None

    if isinstance(data, dict):
        # OAuth 2.0 error format: {"error": "...", "error_description": "..."}
        if "error" in data:
            title = data.get("error")
            detail = data.get("error_description")
            oauth_error = str(title).lower()
            auth_errors = (
                "invalid_grant",
                "invalid_client",
                "unauthorized_client",
                "invalid_token",
            )
            if status == 401 or oauth_error in auth_errors:
                return MyWebLogAuthError(
                    status=status,
                    code=None,
                    title=title,
                    detail=detail,
                    request_id=request_id,
                )

        # RFC 9457 Problem Details format
        title = data.get("title", title)
        detail = data.get("detail", detail)
        code = data.get("code")
        request_id = data.get("request_id", request_id)
        errors = data.get("errors")

    elif isinstance(data, str) and data.strip():
        detail = data.strip()

    # Determine specific subclass based on status and code
    if status == 503 or code == 10060:
        return MyWebLogMaintenanceError(
            status=status,
            code=code,
            title=title,
            detail=detail,
            request_id=request_id,
            retry_after=retry_after,
            errors=errors,
        )

    if status == 429:
        return MyWebLogRateLimitError(
            status=status,
            code=code,
            title=title,
            detail=detail,
            request_id=request_id,
            retry_after=retry_after,
            errors=errors,
        )

    if status == 401:
        return MyWebLogAuthError(
            status=status,
            code=code,
            title=title,
            detail=detail,
            request_id=request_id,
            errors=errors,
        )

    if status == 403:
        return MyWebLogForbiddenError(
            status=status,
            code=code,
            title=title,
            detail=detail,
            request_id=request_id,
            errors=errors,
        )

    if status == 404:
        return MyWebLogNotFoundError(
            status=status,
            code=code,
            title=title,
            detail=detail,
            request_id=request_id,
            errors=errors,
        )

    return MyWebLogError(
        status=status,
        code=code,
        title=title,
        detail=detail,
        request_id=request_id,
        errors=errors,
    )
