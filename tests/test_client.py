import unittest
from unittest.mock import patch, Mock
from datetime import date
import requests
from pyMyweblog.client import MyWebLogClient


class TestMyWebLogClient(unittest.TestCase):
    """Test cases for MyWebLogClient."""

    def setUp(self):
        """Set up the test client."""
        self.username = "test_user"
        self.password = "test_pass"
        self.base_url = "https://api.myweblog.se/api_mobile.php?version=2.0."
        self.client = MyWebLogClient(
            username=self.username,
            password=self.password,
            base_url=self.base_url
        )

    def tearDown(self):
        """Clean up after each test."""
        self.client.close()

    @patch("requests.Session.post")
    def test_get_objects_success(self, mock_post):
        """Test successful retrieval of objects."""
        # Mock API response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
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
        mock_post.return_value = mock_response

        # Call method
        result = self.client.getObjects()

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
            f"{self.base_url}/getObjects",
            json={
                "includeObjectThumbnail": 0,
                "qtype": "getObjects",
                "mwl_u": self.username,
                "mwl_p": self.password,
                "returnType": "json",
                "charset": "UTF-8",
                "app_token": "mySecretApptoken",
                "language": "se"
            }
        )

    @patch("requests.Session.post")
    def test_get_bookings_success(self, mock_post):
        """Test successful retrieval of bookings with default parameters."""
        # Mock API response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "bookings": [
                {
                    "ID": 101,
                    "ac_id": "mySecretAcId",
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
        mock_post.return_value = mock_response

        # Call method
        today = date.today().strftime("%Y-%m-%d")
        result = self.client.getBookings(mybookings=True, includeSun=True)

        # Verify response
        self.assertEqual(
            result,
            {
                "bookings": [
                    {
                        "ID": 101,
                        "ac_id": "mySecretAcId",
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
            f"{self.base_url}/getBookings",
            json={
                "ac_id": "mySecretAcId",
                "mybookings": 1,
                "from_date": today,
                "to_date": today,
                "includeSun": 1,
                "qtype": "getBookings",
                "mwl_u": self.username,
                "mwl_p": self.password,
                "returnType": "json",
                "charset": "UTF-8",
                "app_token": "mySecretApptoken",
                "language": "se"
            }
        )

    @patch("requests.Session.post")
    def test_get_bookings_no_sun_data(self, mock_post):
        """Test retrieval of bookings with includeSun=False."""
        # Mock API response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "bookings": [
                {
                    "ID": 102,
                    "ac_id": "mySecretAcId",
                    "regnr": "SE-XYZ",
                    "bStart": "2025-04-18 09:00:00",
                    "bEnd": "2025-04-18 11:00:00",
                    "fullname": "Test User"
                }
            ]
        }
        mock_post.return_value = mock_response

        # Call method
        today = date.today().strftime("%Y-%m-%d")
        result = self.client.getBookings(mybookings=False, includeSun=False)

        # Verify response
        self.assertEqual(
            result,
            {
                "bookings": [
                    {
                        "ID": 102,
                        "ac_id": "mySecretAcId",
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
            f"{self.base_url}/getBookings",
            json={
                "ac_id": "mySecretAcId",
                "mybookings": 0,
                "from_date": today,
                "to_date": today,
                "includeSun": 0,
                "qtype": "getBookings",
                "mwl_u": self.username,
                "mwl_p": self.password,
                "returnType": "json",
                "charset": "UTF-8",
                "app_token": "mySecretApptoken",
                "language": "se"
            }
        )

    @patch("requests.Session.post")
    def test_myweblog_post_failure(self, mock_post):
        """Test handling of HTTP request failure."""
        # Mock API failure
        mock_response = Mock()
        mock_response.status_code = 400
        mock_response.raise_for_status.side_effect = requests.HTTPError(
            "Bad Request"
        )
        mock_post.return_value = mock_response

        # Verify exception
        with self.assertRaises(requests.HTTPError):
            self.client.getObjects()

    def test_close(self):
        """Test session closure."""
        with patch.object(self.client.session, "close") as mock_close:
            self.client.close()
            mock_close.assert_called_once()

    @patch("requests.Session")
    def test_context_manager(self, mock_session):
        """Test context manager functionality."""
        # Create a mock session instance
        mock_session_instance = mock_session.return_value
        mock_session_instance.close = Mock()

        # Use context manager
        with MyWebLogClient(
            self.username, self.password, self.base_url
        ) as client:
            self.assertIsInstance(client, MyWebLogClient)

        # Verify that close was called
        mock_session_instance.close.assert_called_once()


if __name__ == "__main__":
    unittest.main()
