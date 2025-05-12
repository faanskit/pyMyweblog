import unittest
from unittest.mock import patch, AsyncMock, Mock
import json
from datetime import date, timedelta
import aiohttp
from pyMyweblog.client import MyWebLogClient


class TestMyWebLogClient(unittest.IsolatedAsyncioTestCase):
    """Test cases for MyWebLogClient (aiohttp/async version)."""

    def setUp(self):
        """Set up test parameters."""
        self.username = "test_user"
        self.password = "test_pass"
        self.app_token = "test_token"
        self.airplaneId = "TBD"
        self.base_url = "https://api.myweblog.se/api_mobile.php?version=2.0.3"
        self.token_url = "https://myweblogtoken.netlify.app/api/app_token"

    async def asyncTearDown(self):
        """Clean up after each test (no manual session handling needed)."""
        pass

    @patch("aiohttp.ClientSession.post")
    async def test_get_objects_success(self, mock_post):
        """Test successful retrieval of objects."""
        # Mock API response
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.text = AsyncMock(
            return_value=json.dumps(
                {
                    "APIVersion": "2.0.3",
                    "qType": "GetObjects",
                    "result": {
                        "Object": [
                            {
                                "ID": self.airplaneId,
                                "activeRemarks": [
                                    {
                                        "remarkBy": "Test Pilot",
                                        "remarkCategory": "2",
                                        "remarkDate": "2024-12-31",
                                        "remarkID": "25026",
                                        "remarkText": (
                                            "Kraftiga vibrationer efter start, "
                                            "svajande varvtal"
                                        ),
                                    }
                                ],
                                "club_id": "123",
                                "clubname": "Test Club",
                                "flightData": {
                                    "initial": {
                                        "airborne": "2854.9833",
                                        "block": None,
                                        "landings": "10000",
                                        "tachtime": "0.40",
                                    },
                                    "logged": {
                                        "airborne": "3896.73346",
                                        "block": "4655.71658",
                                        "landings": "9180",
                                        "tachtime": "3962.80000",
                                    },
                                    "total": {
                                        "airborne": 6751.71676,
                                        "airborneText": ("6751:43"),
                                        "block": 4655.71658,
                                        "blockText": "4655:43",
                                        "hobbsMeter": "0.0000",
                                        "hobbsMeterText": "0.0",
                                        "landings": 19180,
                                        "landingsText": "19180",
                                        "tachoMeter": "6759.1000",
                                        "tachoMeterText": "6759.1",
                                        "tachtime": 3963.2,
                                        "tachtimeText": "3963.2",
                                    },
                                },
                                "ftData": {
                                    "airborne": "6751.71676",
                                    "block": "0",
                                    "landings": 19180,
                                    "tachometer": "6759.1000",
                                    "tachtime": "3963.2",
                                },
                                "maintTimeDate": {
                                    "daysToGoValue": 40,
                                    "flightStop_daysToGoValue": 40,
                                    "flightStop_hoursToGoText": "49:17",
                                    "flightStop_hoursToGoValue": 49.28324,
                                    "hoursToGoText": "44:17",
                                    "hoursToGoValue": 44.28324,
                                },
                                "model": "Cessna 172",
                                "regnr": "SE-ABC",
                            }
                        ]
                    },
                }
            )
        )
        mock_response.raise_for_status = Mock()
        mock_post.return_value.__aenter__.return_value = mock_response

        # Use context manager to handle session
        async with MyWebLogClient(
            self.username, self.password, self.app_token
        ) as client:
            await client.obtainAppToken("Dummy")
            result = await client.getObjects()

        # Verify response
        self.assertEqual(
            result,
            {
                "Object": [
                    {
                        "ID": self.airplaneId,
                        "activeRemarks": [
                            {
                                "remarkBy": "Test Pilot",
                                "remarkCategory": "2",
                                "remarkDate": "2024-12-31",
                                "remarkID": "25026",
                                "remarkText": (
                                    "Kraftiga vibrationer efter start, "
                                    "svajande varvtal"
                                ),
                            }
                        ],
                        "club_id": "123",
                        "clubname": "Test Club",
                        "flightData": {
                            "initial": {
                                "airborne": "2854.9833",
                                "block": None,
                                "landings": "10000",
                                "tachtime": "0.40",
                            },
                            "logged": {
                                "airborne": "3896.73346",
                                "block": "4655.71658",
                                "landings": "9180",
                                "tachtime": "3962.80000",
                            },
                            "total": {
                                "airborne": 6751.71676,
                                "airborneText": "6751:43",
                                "block": 4655.71658,
                                "blockText": "4655:43",
                                "hobbsMeter": "0.0000",
                                "hobbsMeterText": "0.0",
                                "landings": 19180,
                                "landingsText": "19180",
                                "tachoMeter": "6759.1000",
                                "tachoMeterText": "6759.1",
                                "tachtime": 3963.2,
                                "tachtimeText": "3963.2",
                            },
                        },
                        "ftData": {
                            "airborne": "6751.71676",
                            "block": "0",
                            "landings": 19180,
                            "tachometer": "6759.1000",
                            "tachtime": "3963.2",
                        },
                        "maintTimeDate": {
                            "daysToGoValue": 40,
                            "flightStop_daysToGoValue": 40,
                            "flightStop_hoursToGoText": "49:17",
                            "flightStop_hoursToGoValue": 49.28324,
                            "hoursToGoText": "44:17",
                            "hoursToGoValue": 44.28324,
                        },
                        "model": "Cessna 172",
                        "regnr": "SE-ABC",
                    }
                ]
            },
        )

        # Verify request
        mock_post.assert_called_once_with(
            self.base_url,
            data={
                "includeObjectThumbnail": 0,
                "qtype": "GetObjects",
                "mwl_u": self.username,
                "mwl_p": self.password,
                "returnType": "JSON",
                "charset": "UTF-8",
                "app_token": self.app_token,
                "language": "se",
            },
        )

    @patch("aiohttp.ClientSession.post")
    async def test_get_bookings_success(self, mock_post):
        """Test successful retrieval of bookings with default parameters."""
        # Mock API response
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.text = AsyncMock(
            return_value=json.dumps(
                {
                    "APIVersion": "2.0.3",
                    "qType": "GetBookings",
                    "result": {
                        "bookings": [
                            {
                                "ID": 101,
                                "ac_id": self.airplaneId,
                                "regnr": "SE-ABC",
                                "bStart": "2025-04-18 08:00:00",
                                "bEnd": "2025-04-18 10:00:00",
                                "fullname": "Test User",
                            }
                        ],
                        "sunData": {
                            "refAirport": {"name": "Test Airport"},
                            "dates": {
                                "2025-04-18": {"sunrise": "06:00", "sunset": "20:00"}
                            },
                        },
                    },
                }
            )
        )
        mock_response.raise_for_status = Mock()
        mock_post.return_value.__aenter__.return_value = mock_response

        # Use context manager to handle session
        async with MyWebLogClient(
            self.username, self.password, self.app_token
        ) as client:
            await client.obtainAppToken("Dummy")
            today = date.today().strftime("%Y-%m-%d")
            today_plus_tree = (date.today() + timedelta(days=3)).strftime("%Y-%m-%d")
            result = await client.getBookings(
                self.airplaneId, mybookings=True, includeSun=True
            )

        # Verify response
        self.assertEqual(
            result,
            {
                "bookings": [
                    {
                        "ID": 101,
                        "ac_id": self.airplaneId,
                        "regnr": "SE-ABC",
                        "bStart": "2025-04-18 08:00:00",
                        "bEnd": "2025-04-18 10:00:00",
                        "fullname": "Test User",
                    }
                ],
                "sunData": {
                    "refAirport": {"name": "Test Airport"},
                    "dates": {"2025-04-18": {"sunrise": "06:00", "sunset": "20:00"}},
                },
            },
        )

        # Verify request
        mock_post.assert_called_once_with(
            self.base_url,
            data={
                "ac_id": self.airplaneId,
                "mybookings": 1,
                "from_date": today,
                "to_date": today_plus_tree,
                "includeSun": 1,
                "qtype": "GetBookings",
                "mwl_u": self.username,
                "mwl_p": self.password,
                "returnType": "JSON",
                "charset": "UTF-8",
                "app_token": self.app_token,
                "language": "se",
            },
        )

    @patch("aiohttp.ClientSession.post")
    async def test_create_booking_success(self, mock_post):
        """Test successful creation of a booking."""
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.text = AsyncMock(
            return_value=json.dumps(
                {
                    "APIVersion": "2.0.3",
                    "qType": "CreateBooking",
                    "result": {
                        "Result": "OK",
                        "bookingID": 1234,
                    },
                }
            )
        )
        mock_response.raise_for_status = Mock()
        mock_post.return_value.__aenter__.return_value = mock_response

        async with MyWebLogClient(
            self.username, self.password, self.app_token
        ) as client:
            await client.obtainAppToken("Dummy")
            result = await client.createBooking(
                ac_id="1118",
                bStart="2025-05-01 10:00:00",
                bEnd="2025-05-01 12:00:00",
                fullname="Test User",
                comment="Test flight",
            )
        self.assertEqual(result["Result"], "OK")
        self.assertEqual(result["bookingID"], 1234)
        mock_post.assert_called_once_with(
            self.base_url,
            data={
                "ac_id": "1118",
                "bStart": "2025-05-01 10:00:00",
                "bEnd": "2025-05-01 12:00:00",
                "fullname": "Test User",
                "comment": "Test flight",
                "qtype": "CreateBooking",
                "mwl_u": self.username,
                "mwl_p": self.password,
                "returnType": "JSON",
                "charset": "UTF-8",
                "app_token": self.app_token,
                "language": "se",
            },
        )

    @patch("aiohttp.ClientSession.post")
    async def test_cut_booking_success(self, mock_post):
        """Test successful cut of a booking."""
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.text = AsyncMock(
            return_value=json.dumps(
                {
                    "APIVersion": "2.0.3",
                    "qType": "CutBooking",
                    "result": {
                        "Result": "OK",
                        "bookingID": 1234,
                    },
                }
            )
        )
        mock_response.raise_for_status = Mock()
        mock_post.return_value.__aenter__.return_value = mock_response

        async with MyWebLogClient(
            self.username, self.password, self.app_token
        ) as client:
            await client.obtainAppToken("Dummy")
            result = await client.cutBooking(booking_id="1234")
        self.assertEqual(result["Result"], "OK")
        self.assertEqual(result["bookingID"], 1234)
        mock_post.assert_called_once_with(
            self.base_url,
            data={
                "bookingID": "1234",
                "qtype": "CutBooking",
                "mwl_u": self.username,
                "mwl_p": self.password,
                "returnType": "JSON",
                "charset": "UTF-8",
                "app_token": self.app_token,
                "language": "se",
            },
        )

    @patch("aiohttp.ClientSession.post")
    async def test_delete_booking_success(self, mock_post):
        """Test successful deletion of a booking."""
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.text = AsyncMock(
            return_value=json.dumps(
                {
                    "APIVersion": "2.0.3",
                    "qType": "DeleteBooking",
                    "result": {
                        "Result": "OK",
                        "bookingID": 1234,
                    },
                }
            )
        )
        mock_response.raise_for_status = Mock()
        mock_post.return_value.__aenter__.return_value = mock_response

        async with MyWebLogClient(
            self.username, self.password, self.app_token
        ) as client:
            await client.obtainAppToken("Dummy")
            result = await client.deleteBooking(booking_id="1234")
        self.assertEqual(result["Result"], "OK")
        self.assertEqual(result["bookingID"], 1234)
        mock_post.assert_called_once_with(
            self.base_url,
            data={
                "bookingID": "1234",
                "qtype": "DeleteBooking",
                "mwl_u": self.username,
                "mwl_p": self.password,
                "returnType": "JSON",
                "charset": "UTF-8",
                "app_token": self.app_token,
                "language": "se",
            },
        )

    @patch("aiohttp.ClientSession.post")
    async def test_get_bookings_no_sun_data(self, mock_post):
        """Test retrieval of bookings with includeSun=False."""
        # Mock API response
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.text = AsyncMock(
            return_value=json.dumps(
                {
                    "APIVersion": "2.0.3",
                    "qType": "GetBookings",
                    "result": {
                        "bookings": [
                            {
                                "ID": 102,
                                "ac_id": self.airplaneId,
                                "regnr": "SE-XYZ",
                                "bStart": "2025-04-18 09:00:00",
                                "bEnd": "2025-04-18 11:00:00",
                                "fullname": "Test User",
                            }
                        ]
                    },
                }
            )
        )
        mock_response.raise_for_status = Mock()
        mock_post.return_value.__aenter__.return_value = mock_response

        # Use context manager to handle session
        async with MyWebLogClient(
            self.username, self.password, self.app_token
        ) as client:
            await client.obtainAppToken("Dummy")
            today = date.today().strftime("%Y-%m-%d")
            today_plus_tree = (date.today() + timedelta(days=3)).strftime("%Y-%m-%d")
            result = await client.getBookings(
                self.airplaneId, mybookings=False, includeSun=False
            )

        # Verify response
        self.assertEqual(
            result,
            {
                "bookings": [
                    {
                        "ID": 102,
                        "ac_id": self.airplaneId,
                        "regnr": "SE-XYZ",
                        "bStart": "2025-04-18 09:00:00",
                        "bEnd": "2025-04-18 11:00:00",
                        "fullname": "Test User",
                    }
                ]
            },
        )

        # Verify request
        mock_post.assert_called_once_with(
            self.base_url,
            data={
                "ac_id": self.airplaneId,
                "mybookings": 0,
                "from_date": today,
                "to_date": today_plus_tree,
                "includeSun": 0,
                "qtype": "GetBookings",
                "mwl_u": self.username,
                "mwl_p": self.password,
                "returnType": "JSON",
                "charset": "UTF-8",
                "app_token": self.app_token,
                "language": "se",
            },
        )

    @patch("aiohttp.ClientSession.post")
    async def test_get_balance_success(self, mock_post):
        """Test successful retrieval of user balance."""
        # Mock API response
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.text = AsyncMock(
            return_value=json.dumps(
                {
                    "APIVersion": "2.0.3",
                    "qType": "GetBalance",
                    "result": {
                        "Balance": "1500.75",
                        "Efternamn": "User",
                        "Fornamn": "Test",
                        "Partikel": None,
                        "Result": "OK",
                        "currency_symbol": "kr",
                        "fullname": "Test User",
                        "int_curr_symbol": "SEK",
                    },
                }
            )
        )
        mock_response.raise_for_status = Mock()
        mock_post.return_value.__aenter__.return_value = mock_response

        # Use context manager to handle session
        async with MyWebLogClient(
            self.username, self.password, self.app_token
        ) as client:
            await client.obtainAppToken("Dummy")
            result = await client.getBalance()

        # Verify response
        self.assertEqual(
            result,
            {
                "Balance": "1500.75",
                "Efternamn": "User",
                "Fornamn": "Test",
                "Partikel": None,
                "Result": "OK",
                "currency_symbol": "kr",
                "fullname": "Test User",
                "int_curr_symbol": "SEK",
            },
        )

        # Verify request
        mock_post.assert_called_once_with(
            self.base_url,
            data={
                "qtype": "GetBalance",
                "mwl_u": self.username,
                "mwl_p": self.password,
                "returnType": "JSON",
                "charset": "UTF-8",
                "app_token": self.app_token,
                "language": "se",
            },
        )

    @patch("aiohttp.ClientSession.post")
    async def test_myweblog_post_failure(self, mock_post):
        """Test handling of HTTP request failure."""
        # Mock API failure
        mock_response = AsyncMock()
        mock_response.status = 400
        mock_response.real_url = self.base_url
        mock_response.text = AsyncMock(return_value="Bad Request")
        error = aiohttp.ClientResponseError(
            request_info=Mock(), history=(), status=400, message="Bad Request"
        )
        mock_response.raise_for_status = Mock(side_effect=error)
        mock_post.return_value.__aenter__.return_value = mock_response

        # Use context manager to handle session
        async with MyWebLogClient(
            self.username, self.password, self.app_token
        ) as client:
            client.app_token = "test_token"  # set directly to avoid extra API call
            with self.assertRaises(aiohttp.ClientResponseError) as context:
                await client.getObjects()
            self.assertEqual(context.exception.status, 400)
            self.assertIn("Bad Request", str(context.exception))

    @patch("aiohttp.ClientSession")
    async def test_close(self, mock_session):
        """Test session closure."""
        mock_session_instance = mock_session.return_value
        mock_session_instance.close = AsyncMock()

        async with MyWebLogClient(
            self.username, self.password, self.app_token
        ) as client:
            pass  # No explicit close call; rely on context manager

        mock_session_instance.close.assert_awaited_once()
        # Verify session is None after closure
        self.assertIsNone(client.session)

    @patch("aiohttp.ClientSession")
    async def test_context_manager(self, mock_session):
        """Test context manager functionality."""
        mock_session_instance = mock_session.return_value
        mock_session_instance.close = AsyncMock()

        async with MyWebLogClient(
            self.username, self.password, self.app_token
        ) as client:
            self.assertIsInstance(client, MyWebLogClient)

        mock_session_instance.close.assert_awaited_once()

    @patch("aiohttp.ClientSession.post")
    async def test_get_flight_log_reversed_success(self, mock_post):
        """Test successful retrieval of reversed flight logs."""
        # Mock API response
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.text = AsyncMock(
            return_value=json.dumps(
                {
                    "APIVersion": "2.0.3",
                    "qType": "GetFlightLogReversed",
                    "result": {
                        "FlightLog": [
                            {
                                "flight_datum": "2024-04-30",
                                "ac_id": "1118",
                                "regnr": "LN-ABC",
                                "departure": "ESTA",
                                "via": None,
                                "arrival": "ESTL",
                                "block_start": None,
                                "block_end": None,
                                "block_total": "0.0000",
                                "airborne_start": "12:00",
                                "airborne_end": "13:00",
                                "airborne_total": "1.0000",
                                "nature_beskr": "PRIVAT",
                                "comment": "Test comment",
                            }
                        ]
                    },
                }
            )
        )
        mock_response.raise_for_status = Mock()
        mock_post.return_value.__aenter__.return_value = mock_response

        async with MyWebLogClient(
            self.username, self.password, self.app_token
        ) as client:
            await client.obtainAppToken("Dummy")
            result = await client.getFlightLogReversed()

        self.assertIn("FlightLog", result)
        self.assertIsInstance(result["FlightLog"], list)
        self.assertGreater(len(result["FlightLog"]), 0)
        flight = result["FlightLog"][0]
        self.assertEqual(flight["flight_datum"], "2024-04-30")
        self.assertEqual(flight["ac_id"], "1118")
        self.assertEqual(flight["regnr"], "LN-ABC")
        self.assertEqual(flight["departure"], "ESTA")
        self.assertEqual(flight["arrival"], "ESTL")
        self.assertEqual(flight["airborne_total"], "1.0000")
        self.assertEqual(flight["nature_beskr"], "PRIVAT")
        self.assertEqual(flight["comment"], "Test comment")

        # Verify request
        mock_post.assert_called_once_with(
            self.base_url,
            data={
                "qtype": "GetFlightLogReversed",
                "mwl_u": self.username,
                "mwl_p": self.password,
                "returnType": "JSON",
                "charset": "UTF-8",
                "app_token": self.app_token,
                "language": "se",
            },
        )

    @patch("aiohttp.ClientSession.post")
    async def test_get_flight_log_success(self, mock_post):
        """Test successful retrieval of flight logs."""
        # Mock API response
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.text = AsyncMock(
            return_value=json.dumps(
                {
                    "APIVersion": "2.0.3",
                    "qType": "GetFlightLog",
                    "result": {
                        "FlightLog": [
                            {
                                "flight_datum": "2024-04-30",
                                "ac_id": "1118",
                                "regnr": "LN-ABC",
                                "departure": "ESTA",
                                "via": None,
                                "arrival": "ESTL",
                                "block_start": None,
                                "block_end": None,
                                "block_total": "0.0000",
                                "airborne_start": "12:00",
                                "airborne_end": "13:00",
                                "airborne_total": "1.0000",
                                "nature_beskr": "PRIVAT",
                                "comment": "Test comment",
                            }
                        ]
                    },
                }
            )
        )
        mock_response.raise_for_status = Mock()
        mock_post.return_value.__aenter__.return_value = mock_response

        async with MyWebLogClient(
            self.username, self.password, self.app_token
        ) as client:
            await client.obtainAppToken("Dummy")
            result = await client.getFlightLog()

        self.assertIn("FlightLog", result)
        self.assertIsInstance(result["FlightLog"], list)
        self.assertGreater(len(result["FlightLog"]), 0)
        flight = result["FlightLog"][0]
        self.assertEqual(flight["flight_datum"], "2024-04-30")
        self.assertEqual(flight["ac_id"], "1118")
        self.assertEqual(flight["regnr"], "LN-ABC")
        self.assertEqual(flight["departure"], "ESTA")
        self.assertEqual(flight["arrival"], "ESTL")
        self.assertEqual(flight["airborne_total"], "1.0000")
        self.assertEqual(flight["nature_beskr"], "PRIVAT")
        self.assertEqual(flight["comment"], "Test comment")

        # Verify request
        mock_post.assert_called_once_with(
            self.base_url,
            data={
                "qtype": "GetFlightLog",
                "mwl_u": self.username,
                "mwl_p": self.password,
                "returnType": "JSON",
                "charset": "UTF-8",
                "app_token": self.app_token,
                "language": "se",
            },
        )

    @patch("aiohttp.ClientSession.post")
    async def test_get_transactions_success(self, mock_post):
        """Test successful retrieval of transactions."""
        # Mock API response
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.text = AsyncMock(
            return_value=json.dumps(
                {
                    "APIVersion": "2.0.3",
                    "qType": "GetTransactions",
                    "result": {
                        "Balance": "1234.56",
                        "Transaction": [
                            {
                                "bookedby_fullname": "giroDirect",
                                "amount": "-100.00",
                                "date": "2024-04-30",
                                "description": "Landing fee",
                                "transaction_id": "TX123456",
                            }
                        ],
                    },
                }
            )
        )
        mock_response.raise_for_status = Mock()
        mock_post.return_value.__aenter__.return_value = mock_response

        async with MyWebLogClient(
            self.username, self.password, self.app_token
        ) as client:
            await client.obtainAppToken("Dummy")
            result = await client.getTransactions()

        # Check response structure
        self.assertIn("Balance", result)
        self.assertIn("Transaction", result)
        self.assertEqual(result["Balance"], "1234.56")
        self.assertIsInstance(result["Transaction"], list)
        self.assertGreater(len(result["Transaction"]), 0)
        self.assertEqual(result["Transaction"][0]["bookedby_fullname"], "giroDirect")
        self.assertEqual(result["Transaction"][0]["amount"], "-100.00")
        self.assertEqual(result["Transaction"][0]["date"], "2024-04-30")
        self.assertEqual(result["Transaction"][0]["description"], "Landing fee")
        self.assertEqual(result["Transaction"][0]["transaction_id"], "TX123456")

        # Verify request
        mock_post.assert_called_once_with(
            self.base_url,
            data={
                "qtype": "GetTransactions",
                "mwl_u": self.username,
                "mwl_p": self.password,
                "returnType": "JSON",
                "charset": "UTF-8",
                "app_token": self.app_token,
                "language": "se",
            },
        )

    @patch("aiohttp.ClientSession.get")
    @patch("aiohttp.ClientSession.post")
    @patch("pyMyweblog.client.MyWebLogClient.getBalance", new_callable=AsyncMock)
    async def test_obtain_app_token(self, mock_get_balance, mock_post, mock_get):
        """Test the obtainAppToken method and validate GetBalance POST request."""

        # Mock GET request to obtain app_token
        mock_get_response = AsyncMock()
        mock_get_response.status = 200
        mock_get_response.json = AsyncMock(return_value={"app_token": "mock_app_token"})
        mock_get_response.raise_for_status = Mock()
        mock_get_response.real_url = self.token_url
        mock_get.return_value.__aenter__.return_value = mock_get_response

        # Mock getBalance call
        getBalanceResult = {
            "Balance": "1500.75",
            "Efternamn": "User",
            "Fornamn": "Test",
            "Partikel": None,
            "Result": "OK",
            "currency_symbol": "kr",
            "fullname": "Test User",
            "int_curr_symbol": "SEK",
        }
        mock_get_balance.return_value = getBalanceResult

        # Mock POST request to log app_token
        mock_post_response = AsyncMock()
        mock_post_response.status = 200
        mock_post_response.raise_for_status = Mock()
        mock_post_response.real_url = self.token_url
        mock_post.return_value.__aenter__.return_value = mock_post_response

        # Initialize client with app_token=None
        async with MyWebLogClient(
            self.username, self.password, app_token=None
        ) as client:
            # Obtain app_token
            app_token = await client.obtainAppToken("mock_app_secret")

            # Verify app_token was set
            self.assertEqual(client.app_token, "mock_app_token")
            self.assertEqual(app_token, "mock_app_token")

        # Verify GET request to obtain app_token
        mock_get.assert_called_once_with(
            self.token_url,
            headers={"X-app-secret": "mock_app_secret"},
        )

        # Verify GET request to obtain app_token
        mock_get.assert_called_once_with(
            self.token_url,
            headers={"X-app-secret": "mock_app_secret"},
        )

        # Verify POST request to log app_token
        mock_post.assert_called_once_with(
            self.token_url,
            headers={"X-app-secret": "mock_app_secret"},
            json=getBalanceResult,
        )


if __name__ == "__main__":
    unittest.main()
