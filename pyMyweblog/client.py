"""MyWebLog API client for Mobile API v5 (v5.25.0).

This module provides the high-level MyWebLogClient class supporting OAuth 2.1
authentication, typed endpoint methods, and legacy v3 backward-compatibility aliases.

Note on time_summary structure (from GET /objects?include=time_summary):
-----------------------------------------------------------------------
{
    "total": {
        "airborne": float | null,          # Decimal hours (e.g. 1004.58333)
        "airborne_formatted": str,         # HH:MM string (e.g. "1004:35")
        "block": float | null,             # Decimal hours (e.g. 1006.91666)
        "block_formatted": str,            # HH:MM string (e.g. "1006:55")
        "tach": float | int | null,        # Tach hours/meter (e.g. 1006 or 8001.3)
        "tach_formatted": str,             # Formatted string (e.g. "1006.0")
        "landings": int | null             # Integer landings count (e.g. 137)
    }
}
"""

from __future__ import annotations

from datetime import date, datetime, timedelta
import logging
from pathlib import Path
from typing import Any

import aiohttp

from .auth import AbstractMyWebLogAuth, OAuth2PKCEAuth

logger = logging.getLogger(__name__)


class MyWebLogClient:
    """Client for interacting with the MyWebLog API v5."""

    def __init__(
        self,
        auth: AbstractMyWebLogAuth | None = None,
        *,
        client_id: str | int | None = None,
        client_secret: str | None = None,
        redirect_uri: str = "http://localhost:5173/callback",
        token_cache_path: str | Path | None = ".myweblog_tokens.json",
        websession: aiohttp.ClientSession | None = None,
        base_url: str = "https://api.myweblog.se/mobile/v5",
        language: str | None = None,
        # Legacy compatibility parameters
        username: str | None = None,
        password: str | None = None,
        app_token: str | None = None,
    ) -> None:
        """Initialize the MyWebLog API v5 client.

        Args:
            auth: Concrete AbstractMyWebLogAuth instance (e.g. for Home Assistant).
            client_id: OAuth 2.1 client ID (default "9" in dev mode).
            client_secret: Optional OAuth 2.1 client secret.
            redirect_uri: OAuth redirect URI.
            token_cache_path: File path for persisting cached tokens.
            websession: Optional shared aiohttp.ClientSession.
            base_url: Base URL for MyWebLog Mobile v5 API.
            language: Optional language code ("se", "gb", etc.).
            username: Legacy v3 username (ignored in v5 OAuth).
            password: Legacy v3 password (ignored in v5 OAuth).
            app_token: Legacy v3 token (ignored in v5 OAuth).
        """
        self.api_version = "5.25.0"
        self._owns_session = False
        self.websession = websession
        self.username = username
        self.app_token = app_token

        if auth is not None:
            self.auth = auth
            self.session = auth.websession
        else:
            if self.websession is None:
                self.websession = aiohttp.ClientSession()
                self._owns_session = True
            self.session = self.websession
            self.auth = OAuth2PKCEAuth(
                websession=self.websession,
                client_id=client_id or "9",
                client_secret=client_secret,
                redirect_uri=redirect_uri,
                token_cache_path=token_cache_path,
                base_url=base_url,
                language=language,
            )

    async def __aenter__(self) -> MyWebLogClient:
        """Enter async context manager."""
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Exit async context manager."""
        await self.close()

    async def close(self) -> None:
        """Close the underlying HTTP session if owned by this client."""
        if self._owns_session and self.websession:
            is_closed = getattr(self.websession, "closed", False)
            if is_closed is not True:
                await self.websession.close()
            self.websession = None

    async def obtainAppToken(self, app_secret: str | None = None) -> str:
        """Legacy v3 method to obtain an app token (deprecated in v5)."""
        logger.warning(
            "obtainAppToken is deprecated in MyWebLog API v5 (OAuth 2.1 is used)."
        )
        return "deprecated_v5"

    # ==========================================
    # v5 REST Endpoints
    # ==========================================

    async def get_client(self) -> dict[str, Any]:
        """Fetch client info, module rights, and rate limits (GET /client)."""
        res = await self.auth.request("GET", "/client")
        return res if isinstance(res, dict) else {"data": res}

    async def get_me(self) -> dict[str, Any]:
        """Fetch authenticated user profile, organization, and balance (GET /me)."""
        res = await self.auth.request("GET", "/me")
        return res if isinstance(res, dict) else {"data": res}

    async def get_profiles(self) -> dict[str, Any]:
        """List member profiles across organizations (GET /me/profiles)."""
        res = await self.auth.request("GET", "/me/profiles")
        return res if isinstance(res, dict) else {"data": res}

    async def switch_profile(self, profile_id: str | int) -> dict[str, Any]:
        """Switch active organization profile using refresh token."""
        if hasattr(self.auth, "async_refresh_tokens"):
            return await self.auth.async_refresh_tokens(profile_id=str(profile_id))
        raise NotImplementedError(
            "Current auth provider does not support switch_profile."
        )

    async def get_organization(self) -> dict[str, Any]:
        """Fetch organization timezone, location, currency, and booking rules."""
        res = await self.auth.request("GET", "/organization")
        return res if isinstance(res, dict) else {"data": res}

    async def get_objects(
        self,
        include: str = "status,active_remarks,time_summary",
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Fetch airplanes and objects (GET /objects).

        Args:
            include: Comma-separated list of extras:
                     "status,active_remarks,time_summary,disclaimer"
        """
        params: dict[str, Any] = {"include": include}
        params.update(kwargs)
        res = await self.auth.request("GET", "/objects", params=params)
        result = res if isinstance(res, dict) else {"data": res}
        # Provide backwards-compatible 'Object' alias key
        if "data" in result and "Object" not in result:
            result["Object"] = result["data"]
        return result

    async def get_bookings(
        self,
        object_id: int | str | None = None,
        date_from: date | str | None = None,
        date_to: date | str | None = None,
        mine: bool = False,
        limit: int | None = None,
        offset: int | None = None,
        exclude: str | None = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Fetch bookings (GET /bookings)."""
        params: dict[str, Any] = {}
        if object_id is not None:
            params["object_id"] = int(object_id)
        if date_from is not None:
            params["date_from"] = (
                date_from.strftime("%Y-%m-%d")
                if isinstance(date_from, (date, datetime))
                else str(date_from)
            )
        if date_to is not None:
            params["date_to"] = (
                date_to.strftime("%Y-%m-%d")
                if isinstance(date_to, (date, datetime))
                else str(date_to)
            )
        if mine:
            params["mine"] = "true"
        if limit is not None:
            params["limit"] = limit
        if offset is not None:
            params["offset"] = offset
        if exclude is not None:
            params["exclude"] = exclude

        res = await self.auth.request("GET", "/bookings", params=params)
        result = res if isinstance(res, dict) else {"data": res}
        if "data" in result and "Booking" not in result:
            result["Booking"] = result["data"]
        return result

    async def create_booking(
        self,
        object_id: int | str,
        start_at: str,
        end_at: str,
        comment: str | None = None,
        expected_airborne: float | None = None,
        seats_left: int | None = None,
        booking_type: str | None = None,
        booking_type_id: int | None = None,
        reminders: dict[str, bool] | None = None,
    ) -> dict[str, Any]:
        """Create a new booking (POST /bookings)."""
        payload: dict[str, Any] = {
            "object_id": int(object_id),
            "start_at": start_at,
            "end_at": end_at,
        }
        if comment is not None:
            payload["comment"] = comment
        if expected_airborne is not None:
            payload["expected_airborne"] = float(expected_airborne)
        if seats_left is not None:
            payload["seats_left"] = int(seats_left)
        if booking_type is not None:
            payload["type"] = booking_type
        if booking_type_id is not None:
            payload["booking_type_id"] = int(booking_type_id)
        if reminders is not None:
            payload["reminders"] = reminders

        res = await self.auth.request("POST", "/bookings", json=payload)
        return res if isinstance(res, dict) else {"data": res}

    async def cut_booking(self, booking_id: int | str) -> dict[str, Any]:
        """End a booking immediately (POST /bookings/{id}/cut)."""
        res = await self.auth.request("POST", f"/bookings/{booking_id}/cut")
        return res if isinstance(res, dict) else {"data": res}

    async def cancel_booking(
        self, booking_id: int | str, reason: str | None = None
    ) -> dict[str, Any]:
        """Cancel a booking (POST /bookings/{id}/cancel)."""
        json_data = {"reason": reason} if reason else None
        res = await self.auth.request(
            "POST", f"/bookings/{booking_id}/cancel", json=json_data
        )
        return res if isinstance(res, dict) else {"data": res}

    async def get_flight_logs(
        self,
        object_id: int | str | None = None,
        date_from: date | str | None = None,
        date_to: date | str | None = None,
        mine: bool = False,
        limit: int = 20,
        offset: int = 0,
        order: str = "asc",
    ) -> dict[str, Any]:
        """Fetch flight logs (GET /flightlogs)."""
        params: dict[str, Any] = {
            "limit": limit,
            "offset": offset,
            "order": order,
        }
        if object_id is not None:
            params["object_id"] = int(object_id)
        if date_from is not None:
            params["date_from"] = (
                date_from.strftime("%Y-%m-%d")
                if isinstance(date_from, (date, datetime))
                else str(date_from)
            )
        if date_to is not None:
            params["date_to"] = (
                date_to.strftime("%Y-%m-%d")
                if isinstance(date_to, (date, datetime))
                else str(date_to)
            )
        if mine:
            params["mine"] = "true"

        res = await self.auth.request("GET", "/flightlogs", params=params)
        result = res if isinstance(res, dict) else {"data": res}
        if "data" in result and "FlightLog" not in result:
            result["FlightLog"] = result["data"]
        return result

    async def get_transactions(
        self,
        limit: int = 20,
        offset: int = 0,
        date_from: date | str | None = None,
        date_to: date | str | None = None,
        include_details: bool = False,
    ) -> dict[str, Any]:
        """Fetch member transactions and account balance (GET /transactions)."""
        params: dict[str, Any] = {"limit": limit, "offset": offset}
        if date_from is not None:
            params["date_from"] = (
                date_from.strftime("%Y-%m-%d")
                if isinstance(date_from, (date, datetime))
                else str(date_from)
            )
        if date_to is not None:
            params["date_to"] = (
                date_to.strftime("%Y-%m-%d")
                if isinstance(date_to, (date, datetime))
                else str(date_to)
            )
        if include_details:
            params["include"] = "details"

        res = await self.auth.request("GET", "/transactions", params=params)
        result = res if isinstance(res, dict) else {"data": res}
        if "data" in result and "Transaction" not in result:
            result["Transaction"] = result["data"]
        return result

    async def get_sun_times(
        self,
        date_from: date | str | None = None,
        date_to: date | str | None = None,
    ) -> dict[str, Any]:
        """Fetch sun times at reference airfield (GET /sun-times)."""
        params: dict[str, Any] = {}
        if date_from is not None:
            params["date_from"] = (
                date_from.strftime("%Y-%m-%d")
                if isinstance(date_from, (date, datetime))
                else str(date_from)
            )
        if date_to is not None:
            params["date_to"] = (
                date_to.strftime("%Y-%m-%d")
                if isinstance(date_to, (date, datetime))
                else str(date_to)
            )

        res = await self.auth.request("GET", "/sun-times", params=params)
        return res if isinstance(res, dict) else {"data": res}

    async def get_expiry_dates(self) -> dict[str, Any]:
        """Fetch member certificates and expiry dates (GET /me/expiry-dates)."""
        res = await self.auth.request("GET", "/me/expiry-dates")
        return res if isinstance(res, dict) else {"data": res}

    # ==========================================
    # Legacy v3 Backward-Compatibility Wrappers
    # ==========================================

    async def getObjects(
        self, include: str = "status,active_remarks,time_summary"
    ) -> dict[str, Any]:
        """Legacy alias for get_objects()."""
        return await self.get_objects(include=include)

    async def getBookings(
        self,
        airplaneId: int | str | None = None,
        mybookings: bool = False,
        includeSun: bool = False,
    ) -> dict[str, Any]:
        """Legacy alias for get_bookings() for today + 3 days."""
        today = date.today()
        today_plus_3 = today + timedelta(days=3)
        return await self.get_bookings(
            object_id=airplaneId,
            date_from=today,
            date_to=today_plus_3,
            mine=mybookings,
        )

    async def getBookingsWithDates(
        self,
        airplaneId: int | str | None,
        fromDate: date | str,
        toDate: date | str,
        mybookings: bool = False,
        includeSun: bool = False,
    ) -> dict[str, Any]:
        """Legacy alias for get_bookings() with explicit dates."""
        return await self.get_bookings(
            object_id=airplaneId,
            date_from=fromDate,
            date_to=toDate,
            mine=mybookings,
        )

    async def getBalance(self) -> dict[str, Any]:
        """Legacy alias for get_me() with v3 key mapping."""
        res = await self.get_me()
        data = res.get("data", res) if isinstance(res, dict) else {}
        compat: dict[str, Any] = dict(res) if isinstance(res, dict) else {}
        name = data.get("name") or {}
        full_name = name.get("full") if isinstance(name, dict) else str(name)
        curr = data.get("currency") or {}
        curr_sym = curr.get("symbol") if isinstance(curr, dict) else ""
        int_curr = curr.get("code") if isinstance(curr, dict) else ""

        compat.setdefault("fullname", full_name)
        compat.setdefault("Balance", data.get("balance"))
        compat.setdefault("currency_symbol", curr_sym)
        compat.setdefault("int_curr_symbol", int_curr)
        return compat

    async def getTransactions(
        self,
        limit: int = 20,
        from_date: date | str | None = None,
        to_date: date | str | None = None,
    ) -> dict[str, Any]:
        """Legacy alias for get_transactions()."""
        return await self.get_transactions(
            limit=limit, date_from=from_date, date_to=to_date
        )

    async def getFlightLog(
        self,
        limit: int = 20,
        from_date: date | str | None = None,
        to_date: date | str | None = None,
        myflights: bool = False,
        ac_id: int | str | None = None,
    ) -> dict[str, Any]:
        """Legacy alias for get_flight_logs(..., order='asc')."""
        return await self.get_flight_logs(
            object_id=ac_id,
            date_from=from_date,
            date_to=to_date,
            mine=myflights,
            limit=limit,
            order="asc",
        )

    async def getFlightLogReversed(
        self,
        limit: int = 20,
        from_date: date | str | None = None,
        to_date: date | str | None = None,
        myflights: bool = False,
        ac_id: int | str | None = None,
    ) -> dict[str, Any]:
        """Legacy alias for get_flight_logs(..., order='desc')."""
        return await self.get_flight_logs(
            object_id=ac_id,
            date_from=from_date,
            date_to=to_date,
            mine=myflights,
            limit=limit,
            order="desc",
        )

    async def createBooking(
        self,
        ac_id: int | str,
        bStart: str,
        bEnd: str,
        fritext: str | None = None,
        expectedAirborne: float | None = None,
        platserkvar: int | None = None,
    ) -> dict[str, Any]:
        """Legacy alias for create_booking()."""
        return await self.create_booking(
            object_id=ac_id,
            start_at=bStart,
            end_at=bEnd,
            comment=fritext,
            expected_airborne=expectedAirborne,
            seats_left=platserkvar,
        )

    async def cutBooking(self, booking_id: int | str) -> dict[str, Any]:
        """Legacy alias for cut_booking()."""
        return await self.cut_booking(booking_id=booking_id)

    async def deleteBooking(self, booking_id: int | str) -> dict[str, Any]:
        """Legacy alias for cancel_booking()."""
        return await self.cancel_booking(booking_id=booking_id)
