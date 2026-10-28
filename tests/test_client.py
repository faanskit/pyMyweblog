"""Unit tests for MyWebLogClient against API v5 REST endpoints."""

from __future__ import annotations

from datetime import date
import unittest
from unittest.mock import AsyncMock, patch

import aiohttp

from pyMyweblog.auth import AbstractMyWebLogAuth
from pyMyweblog.client import MyWebLogClient


class DummyAuth(AbstractMyWebLogAuth):
    """Mock auth provider for testing MyWebLogClient."""

    def __init__(self, websession: aiohttp.ClientSession) -> None:
        super().__init__(websession=websession)
        self.request = AsyncMock()
        self.async_refresh_tokens = AsyncMock(return_value={"access_token": "new_tok"})

    async def async_get_access_token(self) -> str:
        return "mock_token"


class TestMyWebLogClientV5(unittest.IsolatedAsyncioTestCase):
    """Test suite for MyWebLogClient v5 REST endpoints."""

    def setUp(self) -> None:
        self.session = AsyncMock(spec=aiohttp.ClientSession)
        self.auth = DummyAuth(self.session)
        self.client = MyWebLogClient(auth=self.auth)
        self.airplane_id = 5599

    async def asyncTearDown(self) -> None:
        await self.client.close()

    async def test_get_client(self) -> None:
        """Test GET /client."""
        self.auth.request.return_value = {
            "id": 9,
            "name": "Marcus Testklient",
            "app_name": "Marcus Testklient",
            "rate_limit_per_minute": 600,
        }
        res = await self.client.get_client()
        self.auth.request.assert_called_once_with("GET", "/client")
        self.assertEqual(res["id"], 9)
        self.assertEqual(res["app_name"], "Marcus Testklient")

    async def test_get_me_and_get_balance(self) -> None:
        """Test GET /me and legacy getBalance() wrapper."""
        me_data = {
            "data": {
                "id": 66311,
                "username": "3-marcus",
                "name": {
                    "first": "Marcus",
                    "last": "Karlsson",
                    "full": "Marcus Karlsson",
                },
                "balance": 1500.50,
                "currency": {"code": "SEK", "symbol": "kr"},
                "organization": {"id": 1, "name": "Kalmar Flygklubb"},
            }
        }
        self.auth.request.return_value = me_data

        # Test get_me()
        res_me = await self.client.get_me()
        self.auth.request.assert_called_with("GET", "/me")
        self.assertEqual(res_me["data"]["id"], 66311)

        # Test legacy getBalance()
        res_bal = await self.client.getBalance()
        self.assertEqual(res_bal["fullname"], "Marcus Karlsson")
        self.assertEqual(res_bal["Balance"], 1500.50)
        self.assertEqual(res_bal["currency_symbol"], "kr")
        self.assertEqual(res_bal["int_curr_symbol"], "SEK")

    async def test_get_profiles_and_switch(self) -> None:
        """Test GET /me/profiles and switch_profile()."""
        self.auth.request.return_value = {
            "data": [
                {"id": 1, "organization": {"name": "Club A"}},
                {"id": 2, "organization": {"name": "Club B"}},
            ]
        }
        profiles = await self.client.get_profiles()
        self.assertEqual(len(profiles["data"]), 2)

        # Switch profile
        switch_res = await self.client.switch_profile(2)
        self.auth.async_refresh_tokens.assert_called_once_with(profile_id="2")
        self.assertEqual(switch_res["access_token"], "new_tok")

    async def test_get_organization(self) -> None:
        """Test GET /organization."""
        self.auth.request.return_value = {
            "data": {
                "id": 1,
                "name": "Kalmar Flygklubb",
                "timezone": "Europe/Stockholm",
                "currency": {"code": "SEK", "symbol": "kr"},
            }
        }
        res = await self.client.get_organization()
        self.auth.request.assert_called_once_with("GET", "/organization")
        self.assertEqual(res["data"]["timezone"], "Europe/Stockholm")

    async def test_get_objects_and_alias(self) -> None:
        """Test GET /objects and time_summary compatibility."""
        mock_objects = {
            "data": [
                {
                    "id": self.airplane_id,
                    "registration": "SE-DUM",
                    "model": {"designator": "P28A", "name": "Piper PA-28"},
                    "time_summary": {
                        "total": {
                            "airborne": 1004.58333,
                            "airborne_formatted": "1004:35",
                            "block": 1006.91666,
                            "block_formatted": "1006:55",
                            "tach": 1006,
                            "tach_formatted": "1006.0",
                            "landings": 137,
                        }
                    },
                    "active_remarks": [],
                }
            ]
        }
        self.auth.request.return_value = mock_objects

        res = await self.client.get_objects()
        self.auth.request.assert_called_with(
            "GET",
            "/objects",
            params={"include": "status,active_remarks,time_summary"},
        )
        self.assertEqual(len(res["data"]), 1)
        # Check backward-compatible Object alias
        self.assertEqual(len(res["Object"]), 1)
        self.assertEqual(res["data"][0]["registration"], "SE-DUM")

        time_sum = res["data"][0]["time_summary"]["total"]
        self.assertEqual(time_sum["airborne"], 1004.58333)
        self.assertEqual(time_sum["landings"], 137)

        # Legacy alias test
        res_legacy = await self.client.getObjects()
        self.assertEqual(len(res_legacy["Object"]), 1)

    async def test_get_bookings_and_aliases(self) -> None:
        """Test GET /bookings with params and legacy aliases."""
        self.auth.request.return_value = {
            "data": [
                {
                    "id": 101,
                    "start_at": "2026-10-28T10:00:00Z",
                    "end_at": "2026-10-28T12:00:00Z",
                    "object": {"id": self.airplane_id, "registration": "SE-DUM"},
                }
            ]
        }

        # v5 method call
        res = await self.client.get_bookings(
            object_id=self.airplane_id,
            date_from="2026-10-28",
            date_to="2026-10-31",
            mine=True,
        )
        self.auth.request.assert_called_with(
            "GET",
            "/bookings",
            params={
                "object_id": self.airplane_id,
                "date_from": "2026-10-28",
                "date_to": "2026-10-31",
                "mine": "true",
            },
        )
        self.assertEqual(len(res["data"]), 1)
        self.assertEqual(len(res["Booking"]), 1)

        # Legacy getBookingsWithDates
        await self.client.getBookingsWithDates(
            airplaneId=self.airplane_id,
            fromDate=date(2026, 10, 28),
            toDate=date(2026, 10, 30),
            mybookings=False,
        )
        self.auth.request.assert_called_with(
            "GET",
            "/bookings",
            params={
                "object_id": self.airplane_id,
                "date_from": "2026-10-28",
                "date_to": "2026-10-30",
            },
        )

    async def test_create_cut_cancel_booking(self) -> None:
        """Test POST /bookings, /bookings/{id}/cut, and /bookings/{id}/cancel."""
        # Create booking
        self.auth.request.return_value = {"id": 105, "status": "confirmed"}
        create_res = await self.client.create_booking(
            object_id=self.airplane_id,
            start_at="2026-10-29T10:00:00+02:00",
            end_at="2026-10-29T12:00:00+02:00",
            comment="Test flight",
            expected_airborne=1.5,
        )
        self.assertEqual(create_res["id"], 105)
        self.auth.request.assert_called_with(
            "POST",
            "/bookings",
            json={
                "object_id": self.airplane_id,
                "start_at": "2026-10-29T10:00:00+02:00",
                "end_at": "2026-10-29T12:00:00+02:00",
                "comment": "Test flight",
                "expected_airborne": 1.5,
            },
        )

        # Legacy createBooking alias
        await self.client.createBooking(
            ac_id=self.airplane_id,
            bStart="2026-10-29T10:00:00+02:00",
            bEnd="2026-10-29T12:00:00+02:00",
            fritext="Alias flight",
            expectedAirborne=2.0,
            platserkvar=3,
        )
        self.auth.request.assert_called_with(
            "POST",
            "/bookings",
            json={
                "object_id": self.airplane_id,
                "start_at": "2026-10-29T10:00:00+02:00",
                "end_at": "2026-10-29T12:00:00+02:00",
                "comment": "Alias flight",
                "expected_airborne": 2.0,
                "seats_left": 3,
            },
        )

        # Cut booking
        self.auth.request.return_value = {"id": 105, "cut": True}
        cut_res = await self.client.cut_booking(105)
        self.assertEqual(cut_res["cut"], True)
        self.auth.request.assert_called_with("POST", "/bookings/105/cut")

        # Cancel booking
        self.auth.request.return_value = {"id": 105, "cancelled": True}
        cancel_res = await self.client.cancel_booking(105, reason="Bad weather")
        self.assertEqual(cancel_res["cancelled"], True)
        self.auth.request.assert_called_with(
            "POST", "/bookings/105/cancel", json={"reason": "Bad weather"}
        )

    async def test_flight_logs(self) -> None:
        """Test GET /flightlogs and order parameters."""
        self.auth.request.return_value = {
            "data": [
                {
                    "id": 501,
                    "date": "2026-10-25",
                    "airborne_total": 1.2,
                }
            ]
        }
        logs_asc = await self.client.get_flight_logs(
            object_id=self.airplane_id, order="asc"
        )
        self.auth.request.assert_called_with(
            "GET",
            "/flightlogs",
            params={
                "limit": 20,
                "offset": 0,
                "order": "asc",
                "object_id": self.airplane_id,
            },
        )
        self.assertEqual(len(logs_asc["FlightLog"]), 1)

        # Legacy getFlightLogReversed (order="desc")
        await self.client.getFlightLogReversed(ac_id=self.airplane_id, limit=10)
        self.auth.request.assert_called_with(
            "GET",
            "/flightlogs",
            params={
                "limit": 10,
                "offset": 0,
                "order": "desc",
                "object_id": self.airplane_id,
            },
        )

    async def test_transactions(self) -> None:
        """Test GET /transactions."""
        self.auth.request.return_value = {
            "data": [{"id": 901, "amount": -450.0, "comment": "Avgift"}]
        }
        res = await self.client.get_transactions(limit=15, include_details=True)
        self.auth.request.assert_called_with(
            "GET",
            "/transactions",
            params={"limit": 15, "offset": 0, "include": "details"},
        )
        self.assertEqual(len(res["Transaction"]), 1)

    async def test_sun_times_and_expiry_dates(self) -> None:
        """Test GET /sun-times and GET /me/expiry-dates."""
        # Sun times
        self.auth.request.return_value = {
            "data": [{"date": "2026-10-28", "sunrise": "07:15", "sunset": "17:30"}]
        }
        sun = await self.client.get_sun_times(date_from="2026-10-28")
        self.auth.request.assert_called_with(
            "GET", "/sun-times", params={"date_from": "2026-10-28"}
        )
        self.assertEqual(len(sun["data"]), 1)

        # Expiry dates
        self.auth.request.return_value = {
            "data": [{"id": 1, "name": "Medical Class 2", "expiry_date": "2027-05-01"}]
        }
        exp = await self.client.get_expiry_dates()
        self.auth.request.assert_called_with("GET", "/me/expiry-dates")
        self.assertEqual(exp["data"][0]["name"], "Medical Class 2")

    async def test_session_lifecycle_and_deprecated_methods(self) -> None:
        """Test client session lifecycle and deprecated obtainAppToken."""
        # Deprecated obtainAppToken returns dummy without crashing
        tok = await self.client.obtainAppToken("secret")
        self.assertEqual(tok, "deprecated_v5")

        # Standalone client without explicit auth closes owned session
        with patch("aiohttp.ClientSession") as mock_session_cls:
            mock_session = AsyncMock()
            mock_session_cls.return_value = mock_session
            standalone_client = MyWebLogClient(client_id="9")
            self.assertTrue(standalone_client._owns_session)
            await standalone_client.close()
            mock_session.close.assert_called_once()
