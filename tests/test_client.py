import unittest
from unittest.mock import patch, AsyncMock, Mock
import json
from datetime import date
import aiohttp
from pyMyweblog.client import MyWebLogClient


class TestMyWebLogClient(unittest.IsolatedAsyncioTestCase):
    """Test cases for MyWebLogClient (aiohttp/async version)."""

    def setUp(self):
        """Set up test parameters."""
        self.username = "test_user"
        self.password = "test_pass"
        self.app_token = "test_token"
        self.ac_id = "TBD"
        self.base_url = "https://api.myweblog.se/api_mobile.php?version=2.0.3"

    async def asyncTearDown(self):
        """Clean up after each test (no manual session handling needed)."""
        pass

    @patch("aiohttp.ClientSession.post")
    async def test_get_objects_success(self, mock_post):
        """Test successful retrieval of objects."""
        # Mock API response
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.text = AsyncMock(return_value=json.dumps({
            "objects": [
                {
                    "ID": 1,
                    "regnr": "SE-ABC",
                    "club_id": 123,
                    "clubname": "Test Club",
                    "model": "Cessna 172"
                }
            ]
        }))
        # Mock raise_for_status to avoid RuntimeWarning
        mock_response.raise_for_status = Mock()
        mock_post.return_value.__aenter__.return_value = mock_response

        # Use context manager to handle session
        async with MyWebLogClient(
            self.username,
            self.password,
            self.app_token,
            self.base_url
        ) as client:
            result = await client.getObjects()

        # Verify response
        self.assertEqual(
            result,
            {
                "objects": [
                    {
                        "ID": 1,
                        "regnr": "SE-ABC",
                        "club_id": 123,
                        "clubname": "Test Club",
                        "model": "Cessna 172"
                    }
                ]
            }
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
                "language": "se"
            }
        )

    @patch("aiohttp.ClientSession.post")
    async def test_get_bookings_success(self, mock_post):
        """Test successful retrieval of bookings with default parameters."""
        # Mock API response
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.text = AsyncMock(return_value=json.dumps({
            "bookings": [
                {
                    "ID": 101,
                    "ac_id": self.ac_id,
                    "regnr": "SE-ABC",
                    "bStart": "2025-04-18 08:00:00",
                    "bEnd": "2025-04-18 10:00:00",
                    "fullname": "Test User"
                }
            ],
            "sunData": {
                "refAirport": {"name": "Test Airport"},
                "dates": {
                    "2025-04-18": {
                        "sunrise": "06:00",
                        "sunset": "20:00"
                    }
                }
            }
        }))
        mock_response.raise_for_status = Mock()  # Mock raise_for_status
        mock_post.return_value.__aenter__.return_value = mock_response

        # Use context manager to handle session
        async with MyWebLogClient(
            self.username,
            self.password,
            self.app_token,
            self.base_url
        ) as client:
            today = date.today().strftime("%Y-%m-%d")
            result = await client.getBookings(mybookings=True, includeSun=True)

        # Verify response
        self.assertEqual(
            result,
            {
                "bookings": [
                    {
                        "ID": 101,
                        "ac_id": self.ac_id,
                        "regnr": "SE-ABC",
                        "bStart": "2025-04-18 08:00:00",
                        "bEnd": "2025-04-18 10:00:00",
                        "fullname": "Test User"
                    }
                ],
                "sunData": {
                    "refAirport": {"name": "Test Airport"},
                    "dates": {
                        "2025-04-18": {
                            "sunrise": "06:00",
                            "sunset": "20:00"
                        }
                    }
                }
            }
        )

        # Verify request
        mock_post.assert_called_once_with(
            self.base_url,
            data={
                "ac_id": self.ac_id,
                "mybookings": 1,
                "from_date": today,
                "to_date": today,
                "includeSun": 1,
                "qtype": "GetBookings",
                "mwl_u": self.username,
                "mwl_p": self.password,
                "returnType": "JSON",
                "charset": "UTF-8",
                "app_token": self.app_token,
                "language": "se"
            }
        )

    @patch("aiohttp.ClientSession.post")
    async def test_get_bookings_no_sun_data(self, mock_post):
        """Test retrieval of bookings with includeSun=False."""
        # Mock API response
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.text = AsyncMock(return_value=json.dumps({
            "bookings": [
                {
                    "ID": 102,
                    "ac_id": self.ac_id,
                    "regnr": "SE-XYZ",
                    "bStart": "2025-04-18 09:00:00",
                    "bEnd": "2025-04-18 11:00:00",
                    "fullname": "Test User"
                }
            ]
        }))
        mock_response.raise_for_status = Mock()  # Mock raise_for_status
        mock_post.return_value.__aenter__.return_value = mock_response

        # Use context manager to handle session
        async with MyWebLogClient(
            self.username,
            self.password,
            self.app_token,
            self.base_url
        ) as client:
            today = date.today().strftime("%Y-%m-%d")
            result = await client.getBookings(
                mybookings=False, includeSun=False
            )

        # Verify response
        self.assertEqual(
            result,
            {
                "bookings": [
                    {
                        "ID": 102,
                        "ac_id": self.ac_id,
                        "regnr": "SE-XYZ",
                        "bStart": "2025-04-18 09:00:00",
                        "bEnd": "2025-04-18 11:00:00",
                        "fullname": "Test User"
                    }
                ]
            }
        )

        # Verify request
        mock_post.assert_called_once_with(
            self.base_url,
            data={
                "ac_id": self.ac_id,
                "mybookings": 0,
                "from_date": today,
                "to_date": today,
                "includeSun": 0,
                "qtype": "GetBookings",
                "mwl_u": self.username,
                "mwl_p": self.password,
                "returnType": "JSON",
                "charset": "UTF-8",
                "app_token": self.app_token,
                "language": "se"
            }
        )

    @patch("aiohttp.ClientSession.post")
    async def test_myweblog_post_failure(self, mock_post):
        """Test handling of HTTP request failure."""
        # Mock API failure
        mock_response = AsyncMock()
        mock_response.status = 400
        mock_response.text = AsyncMock(return_value="Bad Request")
        mock_response.raise_for_status = Mock(
            side_effect=aiohttp.ClientResponseError(
                request_info=Mock(),
                history=(),
                status=400,
                message="Bad Request"
            )
        )
        mock_post.return_value.__aenter__.return_value = mock_response

        # Use context manager to handle session
        async with MyWebLogClient(
            self.username,
            self.password,
            self.app_token,
            self.base_url
        ) as client:
            with self.assertRaises(aiohttp.ClientResponseError):
                await client.getObjects()

    @patch("aiohttp.ClientSession")
    async def test_close(self, mock_session):
        """Test session closure."""
        mock_session_instance = mock_session.return_value
        mock_session_instance.close = AsyncMock()

        async with MyWebLogClient(
            self.username,
            self.password,
            self.app_token,
            self.base_url
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
            self.username,
            self.password,
            self.app_token,
            self.base_url
        ) as client:
            self.assertIsInstance(client, MyWebLogClient)

        mock_session_instance.close.assert_awaited_once()


if __name__ == "__main__":
    unittest.main()
