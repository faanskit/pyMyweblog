"""OAuth 2.1 + PKCE authentication and HTTP transport for MyWebLog API v5."""

from __future__ import annotations

import asyncio
from abc import ABC, abstractmethod
import base64
import hashlib
import json
import logging
from pathlib import Path
import secrets
import time
from typing import Any
import urllib.parse
import webbrowser

import aiohttp
import aiohttp.web

from .exceptions import (
    MyWebLogAuthError,
    MyWebLogError,
    parse_problem_response,
)

logger = logging.getLogger(__name__)

DEFAULT_BASE_URL = "https://api.myweblog.se/mobile/v5"
DEFAULT_REDIRECT_URI = "http://localhost:5173/callback"


def generate_pkce_pair() -> tuple[str, str]:
    """Generate (code_verifier, code_challenge) for OAuth 2.1 PKCE.

    Returns:
        tuple[str, str]:
            - code_verifier: 64-character URL-safe random string.
            - code_challenge: BASE64URL(SHA-256(ASCII(code_verifier))) without padding.
    """
    code_verifier = secrets.token_urlsafe(48)[:64]
    digest = hashlib.sha256(code_verifier.encode("ascii")).digest()
    code_challenge = base64.urlsafe_b64encode(digest).decode("ascii").rstrip("=")
    return code_verifier, code_challenge


def build_authorize_url(
    client_id: str | int,
    redirect_uri: str,
    code_challenge: str,
    state: str | None = None,
    cl: str | None = None,
    theme: str | None = None,
    base_url: str = DEFAULT_BASE_URL,
) -> str:
    """Build the OAuth 2.1 authorize URL for browser login.

    Args:
        client_id: Registered client ID (e.g. "9").
        redirect_uri: Redirect URI registered for the client.
        code_challenge: PKCE code challenge.
        state: Optional state parameter for CSRF mitigation.
        cl: Optional language code for login page ("se", "gb", "no", "dk").
        theme: Optional theme ("light", "dark", "system").
        base_url: Base URL of the API.
    """
    params: dict[str, str] = {
        "response_type": "code",
        "client_id": str(client_id),
        "redirect_uri": redirect_uri,
        "code_challenge": code_challenge,
        "code_challenge_method": "S256",
    }
    if state:
        params["state"] = state
    if cl:
        params["cl"] = cl
    if theme:
        params["theme"] = theme

    return f"{base_url.rstrip('/')}/oauth/authorize?{urllib.parse.urlencode(params)}"


class AbstractMyWebLogAuth(ABC):
    """Abstract authentication provider and HTTP transport for MyWebLog API."""

    def __init__(
        self,
        websession: aiohttp.ClientSession,
        base_url: str = DEFAULT_BASE_URL,
        language: str | None = None,
    ) -> None:
        """Initialize base authentication handler."""
        self.websession = websession
        self.base_url = base_url.rstrip("/")
        self.language = language
        self._etag_cache: dict[str, tuple[str, Any]] = {}

    @abstractmethod
    async def async_get_access_token(self) -> str:
        """Return a valid OAuth2 access token."""

    async def request(
        self,
        method: str,
        path: str,
        **kwargs: Any,
    ) -> dict[str, Any] | list[Any] | None:
        """Execute an HTTP request with Bearer authentication and error handling."""
        if path.startswith("http://") or path.startswith("https://"):
            url = path
        else:
            url = f"{self.base_url}/{path.lstrip('/')}"

        headers = dict(kwargs.pop("headers", None) or {})
        token = await self.async_get_access_token()
        if token:
            headers["Authorization"] = f"Bearer {token}"
        if self.language and "Accept-Language" not in headers:
            headers["Accept-Language"] = self.language

        # ETag caching for GET requests
        etag_cache_key = url
        params = kwargs.get("params")
        if params:
            etag_cache_key = f"{url}?{urllib.parse.urlencode(params)}"

        if method.upper() == "GET" and etag_cache_key in self._etag_cache:
            cached_etag, _ = self._etag_cache[etag_cache_key]
            headers.setdefault("If-None-Match", cached_etag)

        for attempt in range(2):
            try:
                async with self.websession.request(
                    method, url, headers=headers, **kwargs
                ) as resp:
                    # 304 Not Modified: return cached data
                    if resp.status == 304 and etag_cache_key in self._etag_cache:
                        return self._etag_cache[etag_cache_key][1]

                    request_id = resp.headers.get("Request-Id")
                    retry_after: int | None = None
                    if "Retry-After" in resp.headers:
                        try:
                            retry_after = int(resp.headers["Retry-After"])
                        except (ValueError, TypeError):
                            pass

                    body_data: Any = None
                    ct = resp.headers.get("Content-Type", "")
                    if "application/json" in ct or "application/problem+json" in ct:
                        try:
                            body_data = await resp.json()
                        except Exception:
                            body_data = await resp.text()
                    else:
                        body_data = await resp.text()

                    # Handle error status codes (>= 400)
                    if resp.status >= 400:
                        raise parse_problem_response(
                            status=resp.status,
                            data=body_data,
                            request_id=request_id,
                            retry_after=retry_after,
                        )

                    # 204 No Content or empty body
                    if resp.status == 204 or not body_data:
                        return None

                    # Cache ETag on successful GET
                    etag = resp.headers.get("ETag")
                    if method.upper() == "GET" and etag and body_data is not None:
                        self._etag_cache[etag_cache_key] = (etag, body_data)

                    return body_data
            except aiohttp.ServerDisconnectedError:
                if attempt == 0:
                    logger.debug(
                        "Server disconnected on keep-alive connection, "
                        "retrying on fresh connection..."
                    )
                    continue
                raise


class OAuth2PKCEAuth(AbstractMyWebLogAuth):
    """Standalone / CLI / Dev OAuth 2.1 authentication handler supporting PKCE.

    Supports Option 1 (Confidential Client with client_secret)
    and Option 2 (Public Client with client_id only).
    """

    def __init__(
        self,
        websession: aiohttp.ClientSession,
        client_id: str | int,
        client_secret: str | None = None,
        redirect_uri: str = DEFAULT_REDIRECT_URI,
        token_cache_path: str | Path | None = ".myweblog_tokens.json",
        device_name: str = "pyMyweblog",
        base_url: str = DEFAULT_BASE_URL,
        language: str | None = None,
    ) -> None:
        """Initialize OAuth2PKCEAuth handler."""
        super().__init__(websession=websession, base_url=base_url, language=language)
        self.client_id = str(client_id)
        self.client_secret = client_secret.strip() if client_secret else None
        self.redirect_uri = redirect_uri
        self.token_cache_path = Path(token_cache_path) if token_cache_path else None
        self.device_name = device_name

        self.access_token: str | None = None
        self.refresh_token: str | None = None
        self.expires_at: float | None = None
        self.scope: str | None = None
        self._refresh_lock = asyncio.Lock()

        if self.token_cache_path and self.token_cache_path.exists():
            self._load_tokens_from_file()

    def _load_tokens_from_file(self) -> None:
        """Load stored tokens from disk if present."""
        if not self.token_cache_path or not self.token_cache_path.exists():
            return
        try:
            with open(self.token_cache_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                self.access_token = data.get("access_token")
                self.refresh_token = data.get("refresh_token")
                self.expires_at = data.get("expires_at")
                self.scope = data.get("scope")
        except Exception as err:
            logger.warning(
                "Could not read token cache %s: %s",
                self.token_cache_path,
                err,
            )

    def _save_tokens_to_file(self) -> None:
        """Persist current tokens to disk."""
        if not self.token_cache_path:
            return
        try:
            data = {
                "access_token": self.access_token,
                "refresh_token": self.refresh_token,
                "expires_at": self.expires_at,
                "scope": self.scope,
                "saved_at": time.time(),
            }
            with open(self.token_cache_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
        except Exception as err:
            logger.warning(
                "Could not save token cache %s: %s",
                self.token_cache_path,
                err,
            )

    def _update_tokens(self, body: dict[str, Any]) -> None:
        """Update in-memory tokens and write to cache."""
        self.access_token = body.get("access_token")
        if "refresh_token" in body:
            self.refresh_token = body["refresh_token"]
        expires_in = body.get("expires_in", 3600)
        self.expires_at = time.time() + expires_in
        self.scope = body.get("scope")
        self._save_tokens_to_file()

    def _is_token_expired(self) -> bool:
        """Check if current access token is missing or expiring within 60 seconds."""
        if not self.access_token:
            return True
        if self.expires_at and time.time() >= self.expires_at - 60:
            return True
        return False

    async def async_get_access_token(self) -> str:
        """Return a valid access token, automatically refreshing if expired."""
        if self._is_token_expired() and self.refresh_token:
            async with self._refresh_lock:
                # Double-check inside lock so concurrent callers don't double-rotate
                if self._is_token_expired() and self.refresh_token:
                    await self._async_refresh_tokens_unlocked()

        if not self.access_token:
            raise MyWebLogAuthError("No valid access token available. Please log in.")
        return self.access_token

    async def async_exchange_code(
        self, code: str, code_verifier: str
    ) -> dict[str, Any]:
        """Exchange authorization code and PKCE verifier for tokens."""
        url = f"{self.base_url}/oauth/token"
        form_data: dict[str, str] = {
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": self.redirect_uri,
            "code_verifier": code_verifier,
            "client_id": self.client_id,
        }
        if self.client_secret:
            form_data["client_secret"] = self.client_secret
        if self.device_name:
            form_data["device_name"] = self.device_name

        headers = {"Content-Type": "application/x-www-form-urlencoded"}

        async with self.websession.post(url, data=form_data, headers=headers) as resp:
            request_id = resp.headers.get("Request-Id")
            retry_after: int | None = None
            if "Retry-After" in resp.headers:
                try:
                    retry_after = int(resp.headers["Retry-After"])
                except (ValueError, TypeError):
                    pass

            try:
                body = await resp.json()
            except Exception:
                body = await resp.text()

            if resp.status >= 400:
                raise parse_problem_response(
                    status=resp.status,
                    data=body,
                    request_id=request_id,
                    retry_after=retry_after,
                )

            if isinstance(body, dict):
                self._update_tokens(body)
                return body

            raise MyWebLogError(f"Unexpected token response format: {body}")

    async def async_refresh_tokens(
        self, profile_id: str | None = None
    ) -> dict[str, Any]:
        """Renew tokens using refresh_token, locked to prevent concurrency."""
        async with self._refresh_lock:
            return await self._async_refresh_tokens_unlocked(profile_id=profile_id)

    async def _async_refresh_tokens_unlocked(
        self, profile_id: str | None = None
    ) -> dict[str, Any]:
        """Internal refresh method; caller must hold self._refresh_lock."""
        if not self.refresh_token:
            raise MyWebLogAuthError("No refresh token available.")

        url = f"{self.base_url}/oauth/token"
        form_data: dict[str, str] = {
            "grant_type": "refresh_token",
            "refresh_token": self.refresh_token,
            "client_id": self.client_id,
        }
        if self.client_secret:
            form_data["client_secret"] = self.client_secret
        if profile_id:
            form_data["profile_id"] = str(profile_id)

        headers = {"Content-Type": "application/x-www-form-urlencoded"}

        async with self.websession.post(url, data=form_data, headers=headers) as resp:
            request_id = resp.headers.get("Request-Id")
            retry_after: int | None = None
            if "Retry-After" in resp.headers:
                try:
                    retry_after = int(resp.headers["Retry-After"])
                except (ValueError, TypeError):
                    pass

            try:
                body = await resp.json()
            except Exception:
                body = await resp.text()

            if resp.status >= 400:
                raise parse_problem_response(
                    status=resp.status,
                    data=body,
                    request_id=request_id,
                    retry_after=retry_after,
                )

            if isinstance(body, dict):
                self._update_tokens(body)
                return body

            raise MyWebLogError(f"Unexpected token response format: {body}")

    async def async_revoke_token(self) -> None:
        """Revoke current refresh_token and access tokens at POST /oauth/revoke."""
        if not self.refresh_token:
            return

        url = f"{self.base_url}/oauth/revoke"
        form_data: dict[str, str] = {
            "token": self.refresh_token,
            "token_type_hint": "refresh_token",
            "client_id": self.client_id,
        }
        if self.client_secret:
            form_data["client_secret"] = self.client_secret

        headers = {"Content-Type": "application/x-www-form-urlencoded"}

        try:
            async with self.websession.post(url, data=form_data, headers=headers):
                pass
        finally:
            self.access_token = None
            self.refresh_token = None
            self.expires_at = None
            if self.token_cache_path and self.token_cache_path.exists():
                try:
                    self.token_cache_path.unlink()
                except OSError:
                    pass

    async def async_interactive_login(self, timeout: int = 180) -> dict[str, Any]:
        """Start local loopback server, open browser for consent, and exchange code."""
        parsed_uri = urllib.parse.urlparse(self.redirect_uri)
        raw_host = parsed_uri.hostname or "127.0.0.1"
        bind_host = "127.0.0.1" if raw_host in ("localhost", "127.0.0.1") else raw_host
        port = parsed_uri.port or 5173
        callback_path = parsed_uri.path or "/callback"

        code_verifier, code_challenge = generate_pkce_pair()
        expected_state = secrets.token_urlsafe(16)

        auth_url = build_authorize_url(
            client_id=self.client_id,
            redirect_uri=self.redirect_uri,
            code_challenge=code_challenge,
            state=expected_state,
            base_url=self.base_url,
        )

        loop = asyncio.get_running_loop()
        callback_future: asyncio.Future[tuple[str, str | None]] = loop.create_future()

        async def handle_callback(
            request: aiohttp.web.Request,
        ) -> aiohttp.web.Response:
            error = request.query.get("error")
            error_desc = request.query.get("error_description")
            code = request.query.get("code")
            state = request.query.get("state")

            if error:
                if not callback_future.done():
                    callback_future.set_exception(
                        MyWebLogAuthError(f"OAuth error: {error} - {error_desc or ''}")
                    )
                html = (
                    "<html><body><h2>Authentication Failed</h2>"
                    f"<p>{error}: {error_desc or ''}</p>"
                    "<p>You can close this window.</p></body></html>"
                )
                return aiohttp.web.Response(
                    text=html, content_type="text/html", status=400
                )

            if state != expected_state:
                if not callback_future.done():
                    callback_future.set_exception(
                        MyWebLogAuthError("OAuth state parameter mismatch.")
                    )
                html = (
                    "<html><body><h2>Authentication Failed</h2>"
                    "<p>State parameter mismatch.</p>"
                    "<p>You can close this window.</p></body></html>"
                )
                return aiohttp.web.Response(
                    text=html, content_type="text/html", status=400
                )

            if not code:
                if not callback_future.done():
                    callback_future.set_exception(
                        MyWebLogAuthError("No authorization code received in callback.")
                    )
                html = (
                    "<html><body><h2>Authentication Failed</h2>"
                    "<p>No code received.</p>"
                    "<p>You can close this window.</p></body></html>"
                )
                return aiohttp.web.Response(
                    text=html, content_type="text/html", status=400
                )

            if not callback_future.done():
                callback_future.set_result((code, state))

            html = """<!DOCTYPE html>
<html>
<head><title>MyWebLog Login Success</title></head>
<body style="font-family: sans-serif; text-align: center; padding-top: 60px;">
  <h2 style="color: #2e7d32;">Authentication Successful!</h2>
  <p>You may now close this browser tab and return to the terminal or application.</p>
</body>
</html>"""
            return aiohttp.web.Response(text=html, content_type="text/html")

        app = aiohttp.web.Application()
        app.router.add_get(callback_path, handle_callback)

        runner = aiohttp.web.AppRunner(app)
        await runner.setup()
        site = aiohttp.web.TCPSite(runner, bind_host, port)

        try:
            await site.start()
            print(f"\n[MyWebLog OAuth] Opening browser to log in:\n  {auth_url}\n")
            try:
                webbrowser.open(auth_url)
            except Exception as err:
                logger.warning("Could not launch browser automatically: %s", err)

            code, _ = await asyncio.wait_for(callback_future, timeout=timeout)
            tokens = await self.async_exchange_code(
                code=code, code_verifier=code_verifier
            )
            return tokens
        finally:
            await runner.cleanup()
