"""Unit tests for pyMyweblog OAuth 2.1 + PKCE authentication and transport."""

from __future__ import annotations

import asyncio
import base64
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import AsyncMock

import aiohttp

from pyMyweblog.auth import (
    AbstractMyWebLogAuth,
    ClientCredentialsAuth,
    MAIN_API_BASE_URL,
    OAuth2PKCEAuth,
    build_authorize_url,
    generate_pkce_pair,
)
from pyMyweblog.exceptions import (
    MyWebLogAuthError,
    MyWebLogForbiddenError,
    MyWebLogMaintenanceError,
    MyWebLogNotFoundError,
    MyWebLogRateLimitError,
    parse_problem_response,
)


class ConcreteAuth(AbstractMyWebLogAuth):
    """Concrete implementation for testing AbstractMyWebLogAuth."""

    def __init__(
        self,
        websession: aiohttp.ClientSession,
        token: str = "test_bearer_token",
        **kwargs,
    ) -> None:
        super().__init__(websession, **kwargs)
        self._token = token

    async def async_get_access_token(self) -> str:
        return self._token


class TestOAuth2PKCEAuth(unittest.IsolatedAsyncioTestCase):
    """Test suite for OAuth 2.1 + PKCE authentication and error parsing."""

    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.token_path = Path(self.temp_dir.name) / "test_tokens.json"
        self.session = AsyncMock(spec=aiohttp.ClientSession)

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_pkce_generation(self) -> None:
        """Test PKCE verifier and challenge generation."""
        verifier, challenge = generate_pkce_pair()

        # Verifier must be exactly 64 characters URL-safe
        self.assertEqual(len(verifier), 64)
        for char in verifier:
            self.assertTrue(char.isalnum() or char in "-._~")

        # Challenge must match SHA256 + base64url without '=' padding
        expected_digest = hashlib.sha256(verifier.encode("ascii")).digest()
        expected_challenge = (
            base64.urlsafe_b64encode(expected_digest).decode("ascii").rstrip("=")
        )
        self.assertEqual(challenge, expected_challenge)
        self.assertNotIn("=", challenge)

        # RFC 7636 Section 3 test vector
        rfc_verifier = "dBjftJeZ4CVP-mB92K27uhbUJU1p1r_wW1gFWFOEjXk"
        rfc_digest = hashlib.sha256(rfc_verifier.encode("ascii")).digest()
        rfc_challenge = base64.urlsafe_b64encode(rfc_digest).decode("ascii").rstrip("=")
        self.assertEqual(
            rfc_challenge,
            "E9Melhoa2OwvFrEMTJguCHaoeK1t8URWbuGJSstw-cM",
        )

    def test_build_authorize_url(self) -> None:
        """Test construction of authorize URL with parameters."""
        url = build_authorize_url(
            client_id="9",
            redirect_uri="http://localhost:5173/callback",
            code_challenge="test_challenge_123",
            state="state_xyz",
            cl="se",
            theme="dark",
        )
        prefix = "https://api.myweblog.se/mobile/v5/oauth/authorize?"
        self.assertTrue(url.startswith(prefix))
        self.assertIn("client_id=9", url)
        self.assertIn("response_type=code", url)
        self.assertIn("code_challenge=test_challenge_123", url)
        self.assertIn("code_challenge_method=S256", url)
        self.assertIn("state=state_xyz", url)
        self.assertIn("cl=se", url)
        self.assertIn("theme=dark", url)

    def test_problem_error_mapping(self) -> None:
        """Test parsing of RFC 9457 Problem Details and OAuth 2.0 errors."""
        # 401 Unauthorized Problem
        p401 = parse_problem_response(
            401,
            {"title": "Unauthorized", "detail": "Token expired", "code": 10001},
            request_id="req-401",
        )
        self.assertIsInstance(p401, MyWebLogAuthError)
        self.assertEqual(p401.status, 401)
        self.assertEqual(p401.request_id, "req-401")

        # 400 OAuth Error invalid_grant
        p_oauth = parse_problem_response(
            400,
            {
                "error": "invalid_grant",
                "error_description": "the app may not be used for this club",
            },
        )
        self.assertIsInstance(p_oauth, MyWebLogAuthError)
        self.assertEqual(p_oauth.title, "invalid_grant")

        # 403 Forbidden
        p403 = parse_problem_response(
            403,
            {"title": "Module forbidden", "code": 10002, "request_id": "req-403"},
        )
        self.assertIsInstance(p403, MyWebLogForbiddenError)
        self.assertEqual(p403.code, 10002)

        # 404 Not Found
        p404 = parse_problem_response(
            404,
            {"title": "Not found", "request_id": "req-404"},
        )
        self.assertIsInstance(p404, MyWebLogNotFoundError)
        self.assertEqual(p404.status, 404)

        # 429 Too Many Requests
        p429 = parse_problem_response(
            429,
            {"title": "Rate limit exceeded"},
            retry_after=45,
        )
        self.assertIsInstance(p429, MyWebLogRateLimitError)
        self.assertEqual(p429.retry_after, 45)

        # 503 Maintenance (code 10060)
        p503 = parse_problem_response(
            503,
            {"title": "Closed for maintenance", "code": 10060},
            retry_after=120,
        )
        self.assertIsInstance(p503, MyWebLogMaintenanceError)
        self.assertEqual(p503.code, 10060)
        self.assertEqual(p503.retry_after, 120)

    async def test_abstract_auth_request_success_and_etag(self) -> None:
        """Test HTTP request Bearer token injection, language, and ETag handling."""
        mock_resp = AsyncMock()
        mock_resp.status = 200
        mock_resp.headers = {
            "Content-Type": "application/json",
            "ETag": '"etag-abc"',
        }
        mock_resp.json = AsyncMock(return_value={"data": {"user": "Marcus"}})

        mock_ctx = AsyncMock()
        mock_ctx.__aenter__.return_value = mock_resp
        self.session.request.return_value = mock_ctx

        auth = ConcreteAuth(self.session, token="tok123", language="sv-SE")
        result = await auth.request("GET", "/me")

        self.assertEqual(result, {"data": {"user": "Marcus"}})
        self.session.request.assert_called_once()
        _, kwargs = self.session.request.call_args
        self.assertEqual(kwargs["headers"]["Authorization"], "Bearer tok123")
        self.assertEqual(kwargs["headers"]["Accept-Language"], "sv-SE")

        # Second request with 304 Not Modified
        mock_resp_304 = AsyncMock()
        mock_resp_304.status = 304
        mock_resp_304.headers = {}
        mock_ctx_304 = AsyncMock()
        mock_ctx_304.__aenter__.return_value = mock_resp_304
        self.session.request.return_value = mock_ctx_304

        result_cached = await auth.request("GET", "/me")
        # Should return cached data
        self.assertEqual(result_cached, {"data": {"user": "Marcus"}})
        _, kwargs_304 = self.session.request.call_args
        self.assertEqual(kwargs_304["headers"]["If-None-Match"], '"etag-abc"')

    async def test_oauth2_pkce_auth_exchange_code_option1_confidential(self) -> None:
        """Test Option 1: code exchange sends client_id & client_secret."""
        mock_resp = AsyncMock()
        mock_resp.status = 200
        mock_resp.headers = {
            "Content-Type": "application/json",
            "Request-Id": "req-exch-1",
        }
        mock_resp.json = AsyncMock(
            return_value={
                "access_token": "mwlat_initial",
                "token_type": "Bearer",
                "expires_in": 3600,
                "refresh_token": "mwlrt_initial",
                "scope": "organization:r objects:rw bookings:rw",
            }
        )
        mock_ctx = AsyncMock()
        mock_ctx.__aenter__.return_value = mock_resp
        self.session.post.return_value = mock_ctx

        auth = OAuth2PKCEAuth(
            websession=self.session,
            client_id="9",
            client_secret="mwlm1_secret_value",
            redirect_uri="http://localhost:5173/callback",
            token_cache_path=self.token_path,
        )

        tokens = await auth.async_exchange_code(
            code="code_123", code_verifier="verifier_456"
        )

        self.assertEqual(tokens["access_token"], "mwlat_initial")
        self.assertEqual(auth.access_token, "mwlat_initial")
        self.assertEqual(auth.refresh_token, "mwlrt_initial")

        # Verify POST payload sent
        self.session.post.assert_called_once()
        _, kwargs = self.session.post.call_args
        form_data = kwargs["data"]
        self.assertEqual(form_data["grant_type"], "authorization_code")
        self.assertEqual(form_data["code"], "code_123")
        self.assertEqual(form_data["code_verifier"], "verifier_456")
        self.assertEqual(form_data["client_id"], "9")
        self.assertEqual(form_data["client_secret"], "mwlm1_secret_value")

        # Verify persisted file
        self.assertTrue(self.token_path.exists())
        with open(self.token_path, "r", encoding="utf-8") as f:
            saved = json.load(f)
            self.assertEqual(saved["access_token"], "mwlat_initial")
            self.assertEqual(saved["refresh_token"], "mwlrt_initial")

    async def test_oauth2_pkce_auth_exchange_code_option2_public(self) -> None:
        """Test Option 2: code exchange sends client_id alone without secret."""
        mock_resp = AsyncMock()
        mock_resp.status = 200
        mock_resp.headers = {"Content-Type": "application/json"}
        mock_resp.json = AsyncMock(
            return_value={
                "access_token": "mwlat_public",
                "token_type": "Bearer",
                "expires_in": 3600,
                "refresh_token": "mwlrt_public",
                "scope": "organization:r objects:r",
            }
        )
        mock_ctx = AsyncMock()
        mock_ctx.__aenter__.return_value = mock_resp
        self.session.post.return_value = mock_ctx

        auth = OAuth2PKCEAuth(
            websession=self.session,
            client_id="public_client_id",
            client_secret=None,
            token_cache_path=self.token_path,
        )

        tokens = await auth.async_exchange_code(
            code="code_pub", code_verifier="verifier_pub"
        )
        self.assertEqual(tokens["access_token"], "mwlat_public")

        _, kwargs = self.session.post.call_args
        form_data = kwargs["data"]
        self.assertEqual(form_data["client_id"], "public_client_id")
        self.assertNotIn("client_secret", form_data)

    async def test_refresh_token_rotation_and_lock(self) -> None:
        """Test single-use refresh token rotation and asyncio.Lock serialization."""
        refresh_call_count = 0

        def fake_refresh_post(*args, **kwargs):
            resp = AsyncMock()
            resp.status = 200
            resp.headers = {"Content-Type": "application/json"}

            async def get_json():
                nonlocal refresh_call_count
                refresh_call_count += 1
                await asyncio.sleep(0.01)
                return {
                    "access_token": f"mwlat_rotated_{refresh_call_count}",
                    "token_type": "Bearer",
                    "expires_in": 3600,
                    "refresh_token": f"mwlrt_rotated_{refresh_call_count}",
                }

            resp.json = get_json

            ctx = AsyncMock()
            ctx.__aenter__.return_value = resp
            return ctx

        self.session.post.side_effect = fake_refresh_post

        auth = OAuth2PKCEAuth(
            websession=self.session,
            client_id="9",
            client_secret="mwlm1_secret",
            token_cache_path=self.token_path,
        )
        auth.refresh_token = "mwlrt_v1"

        # Concurrently request refresh
        results = await asyncio.gather(
            auth.async_refresh_tokens(),
            auth.async_refresh_tokens(),
        )

        # Both calls succeeded sequentially due to Lock
        self.assertEqual(len(results), 2)
        self.assertEqual(refresh_call_count, 2)
        # The final refresh token stored is the 2nd rotated one
        self.assertEqual(auth.refresh_token, "mwlrt_rotated_2")
        self.assertEqual(auth.access_token, "mwlat_rotated_2")

        # Verify disk cache holds the latest rotated tokens
        with open(self.token_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            self.assertEqual(data["refresh_token"], "mwlrt_rotated_2")

    async def test_auto_refresh_on_token_expiry(self) -> None:
        """Test that async_get_access_token auto-refreshes when expired."""
        auth = OAuth2PKCEAuth(
            websession=self.session,
            client_id="9",
            token_cache_path=self.token_path,
        )
        auth.access_token = "expired_token"
        auth.expires_at = 1000.0  # Expired in past
        auth.refresh_token = "valid_refresh_token"

        mock_resp = AsyncMock()
        mock_resp.status = 200
        mock_resp.headers = {"Content-Type": "application/json"}
        mock_resp.json = AsyncMock(
            return_value={
                "access_token": "fresh_access_token",
                "refresh_token": "fresh_refresh_token",
                "expires_in": 3600,
            }
        )
        mock_ctx = AsyncMock()
        mock_ctx.__aenter__.return_value = mock_resp
        self.session.post.return_value = mock_ctx

        token = await auth.async_get_access_token()
        self.assertEqual(token, "fresh_access_token")
        self.assertEqual(auth.refresh_token, "fresh_refresh_token")

    async def test_revoke_tokens(self) -> None:
        """Test that async_revoke_token revokes and cleans up cached file."""
        mock_resp = AsyncMock()
        mock_resp.status = 200
        mock_resp.headers = {"Content-Type": "application/json"}
        mock_ctx = AsyncMock()
        mock_ctx.__aenter__.return_value = mock_resp
        self.session.post.return_value = mock_ctx

        auth = OAuth2PKCEAuth(
            websession=self.session,
            client_id="9",
            token_cache_path=self.token_path,
        )
        auth.access_token = "at123"
        auth.refresh_token = "rt123"
        auth._save_tokens_to_file()
        self.assertTrue(self.token_path.exists())

        await auth.async_revoke_token()

        self.assertIsNone(auth.access_token)
        self.assertIsNone(auth.refresh_token)
        self.assertFalse(self.token_path.exists())


class TestClientCredentialsAuth(unittest.IsolatedAsyncioTestCase):
    """Test suite for OAuth 2.0 Client Credentials authentication (Main API)."""

    def setUp(self) -> None:
        self.session = AsyncMock(spec=aiohttp.ClientSession)
        self.auth = ClientCredentialsAuth(
            websession=self.session,
            client_id="4711",
            client_secret="mwla1_test_secret",
            base_url=MAIN_API_BASE_URL,
        )

    async def test_fetch_access_token_success(self) -> None:
        """Test successful token fetch via client_credentials grant."""
        mock_resp = AsyncMock()
        mock_resp.status = 200
        mock_resp.headers = {"Content-Type": "application/json"}
        mock_resp.json = AsyncMock(
            return_value={
                "access_token": "mwlat_test_12345",
                "expires_in": 3600,
                "scope": "objects:r bookings:rw",
                "token_type": "Bearer",
            }
        )
        mock_ctx = AsyncMock()
        mock_ctx.__aenter__.return_value = mock_resp
        self.session.post.return_value = mock_ctx

        token = await self.auth.async_get_access_token()

        self.assertEqual(token, "mwlat_test_12345")
        self.assertEqual(self.auth.scope, "objects:r bookings:rw")
        self.session.post.assert_called_once()
        call_args = self.session.post.call_args
        self.assertEqual(call_args[0][0], f"{MAIN_API_BASE_URL}/oauth/token")
        self.assertEqual(
            call_args[1]["data"],
            {
                "grant_type": "client_credentials",
                "client_id": "4711",
                "client_secret": "mwla1_test_secret",
            },
        )

    async def test_reuse_valid_token(self) -> None:
        """Test that a valid cached token is reused without extra HTTP request."""
        self.auth.access_token = "valid_cached_token"
        import time

        self.auth.expires_at = time.time() + 1800  # valid for 30 more minutes

        token = await self.auth.async_get_access_token()

        self.assertEqual(token, "valid_cached_token")
        self.session.post.assert_not_called()

    async def test_token_refresh_when_expired(self) -> None:
        """Test that an expired token triggers a new fetch."""
        self.auth.access_token = "old_expired_token"
        self.auth.expires_at = 1000.0  # past

        mock_resp = AsyncMock()
        mock_resp.status = 200
        mock_resp.headers = {"Content-Type": "application/json"}
        mock_resp.json = AsyncMock(
            return_value={
                "access_token": "new_refreshed_token",
                "expires_in": 3600,
            }
        )
        mock_ctx = AsyncMock()
        mock_ctx.__aenter__.return_value = mock_resp
        self.session.post.return_value = mock_ctx

        token = await self.auth.async_get_access_token()

        self.assertEqual(token, "new_refreshed_token")
        self.session.post.assert_called_once()

    async def test_auth_error_handling(self) -> None:
        """Test that 401 raises MyWebLogAuthError."""
        mock_resp = AsyncMock()
        mock_resp.status = 401
        mock_resp.headers = {"Content-Type": "application/json"}
        mock_resp.json = AsyncMock(
            return_value={
                "error": "invalid_client",
                "error_description": "The client id or secret is wrong",
            }
        )
        mock_ctx = AsyncMock()
        mock_ctx.__aenter__.return_value = mock_resp
        self.session.post.return_value = mock_ctx

        with self.assertRaises(MyWebLogAuthError):
            await self.auth.async_get_access_token()

    async def test_request_retries_on_401(self) -> None:
        """Test that request() refreshes token and retries when server returns 401."""
        import time

        self.auth.access_token = "stale_token"
        self.auth.expires_at = time.time() + 1000

        # First request call returns 401
        resp_401 = AsyncMock()
        resp_401.status = 401
        resp_401.headers = {"Content-Type": "application/json"}
        resp_401.json = AsyncMock(
            return_value={
                "error": "invalid_token",
                "error_description": "Token expired",
            }
        )
        ctx_401 = AsyncMock()
        ctx_401.__aenter__.return_value = resp_401

        # Token fetch call returns 200 with new token
        resp_token = AsyncMock()
        resp_token.status = 200
        resp_token.headers = {"Content-Type": "application/json"}
        resp_token.json = AsyncMock(
            return_value={
                "access_token": "fresh_token_after_401",
                "expires_in": 3600,
            }
        )
        ctx_token = AsyncMock()
        ctx_token.__aenter__.return_value = resp_token

        # Second request call returns 200 with data
        resp_success = AsyncMock()
        resp_success.status = 200
        resp_success.headers = {"Content-Type": "application/json"}
        resp_success.json = AsyncMock(return_value={"data": [{"id": 1}]})
        ctx_success = AsyncMock()
        ctx_success.__aenter__.return_value = resp_success

        self.session.request.side_effect = [ctx_401, ctx_success]
        self.session.post.return_value = ctx_token

        result = await self.auth.request("GET", "/objects")

        self.assertEqual(result, {"data": [{"id": 1}]})
        self.assertEqual(self.auth.access_token, "fresh_token_after_401")
        self.assertEqual(self.session.request.call_count, 2)
        self.session.post.assert_called_once()
