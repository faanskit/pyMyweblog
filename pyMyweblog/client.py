import aiohttp
import json
from typing import Any, Dict
from datetime import date


class MyWebLogClient:
    """Client for interacting with the MyWebLog API."""

    def __init__(
        self,
        username: str,
        password: str,
        app_token: str,
        base_url: str = "https://api.myweblog.se/api_mobile.php?version=2.0.3"
    ):
        """Initialize the MyWebLog client.

        Args:
            username (str): Username for authentication.
            password (str): Password for authentication.
            app_token (str): Application token for API access.
            ac_id (str): Aircraft ID for API requests.
            base_url (str): Base URL for the MyWebLog API
            (default: https://api.myweblog.se/api_mobile.php?version=2.0.3).
        """
        self.username = username
        self.password = password
        self.app_token = app_token
        self.ac_id = "TBD"
        self.base_url = base_url.rstrip("/")
        self.session = None
        print(
            f"Connecting to MyWebLog API at {self.base_url} "
            f"with user {self.username}"
        )

    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self

    async def __aexit__(self, exc_type, exc, tb):
        if self.session:
            await self.session.close()
            self.session = None

    async def _myWeblogPost(
        self, qtype: str, data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Send a POST request to the MyWebLog API.

        Args:
            qtype (str): Query type for the API request (e.g., 'GetObjects').
            data (Dict[str, Any]): Data to include in the request body.

        Returns:
            Dict[str, Any]: Response from the API.
        """
        if not self.session:
            raise RuntimeError(
                "ClientSession is not initialized. Use 'async with' context."
            )
        payload = {
            "qtype": qtype,
            "mwl_u": self.username,
            "mwl_p": self.password,
            "returnType": "JSON",
            "charset": "UTF-8",
            "app_token": self.app_token,
            "language": "se",
            **data
        }
        async with self.session.post(self.base_url, data=payload) as resp:
            resp.raise_for_status()
            # API returns text/plain; manually decode as JSON
            response = await resp.text()
            return json.loads(response)

    async def getObjects(self) -> Dict[str, Any]:
        """Get objects from the MyWebLog API.

        Returns:
            Dict[str, Any]: Response from the API.
            Output example:
            {
                'APIVersion': str,
                'qType': str,
                'result': {
                'Object': [
                    {
                    'ID': str,
                    'regnr': str,
                    'model': str,
                    'club_id': str,
                    'clubname': str,
                    'bobject_cat': str (optional),
                    'comment': str (optional),
                    'activeRemarks': [
                        {
                        'remarkID': str,
                        'remarkBy': str,
                        'remarkCategory': str,
                        'remarkDate': str,
                        'remarkText': str
                        },
                        ...
                    ] (optional),
                    'flightData': {
                        'initial': {...},
                        'logged': {...},
                        'total': {...}
                    },
                    'ftData': {...},
                    'maintTimeDate': {...} (optional)
                    },
                    ...
                ],
                'Result': str
                }
            }
            Notable fields per object:
            - ID (str): Object ID
            - regnr (str): Registration or name
            - model (str): Model/type
            - club_id (str): Club ID
            - clubname (str): Club name
            - bobject_cat (str, optional): Object category
            - comment (str, optional): Comment/description
            - activeRemarks (list, optional): List of active remarks
            - flightData (dict): Flight time and usage data
            - ftData (dict): Flight totals
            - maintTimeDate (dict, optional): Maintenance info
        """
        data = {
            "includeObjectThumbnail": 0
        }
        return await self._myWeblogPost("GetObjects", data)

    async def getBookings(
        self, mybookings: bool = True, includeSun: bool = True
    ) -> Dict[str, Any]:
        """Get bookings from the MyWebLog API.

        Args:
            mybookings (bool): Whether to fetch only user's bookings.
            includeSun (bool): Whether to include sunrise/sunset data.

        Returns:
            Dict[str, Any]: Response from the API.
            Output:
                ID (int)
                ac_id (int)
                regnr (string)
                bobject_cat (int)
                club_id (int)
                user_id (int)
                bStart (timestamp)
                bEnd (timestamp)
                typ (string)
                primary_booking (bool)
                fritext (string)
                elevuserid (int)
                platserkvar (int)
                fullname (string)
                email (string)
                completeMobile (string)
                sunData (dict): Reference airport data and dates
        """
        today = date.today().strftime("%Y-%m-%d")
        data = {
            "ac_id": self.ac_id,
            "mybookings": int(mybookings),
            "from_date": today,
            "to_date": today,
            "includeSun": int(includeSun)
        }
        return await self._myWeblogPost("GetBookings", data)

    async def getBalance(self) -> Dict[str, Any]:
        """Get the balance of the current user from the MyWebLog API.

        Returns:
            Dict[str, Any]: Response from the API.
            Output example:
            {
                'Fornamn': str,
                'Partikel': str,
                'Efternamn': str,
                'fullname': str,
                'Balance': float,
                'currency_symbol': str,
                'int_curr_symbol': str
            }
        """
        data = {}
        return await self._myWeblogPost("GetBalance", data)

    async def close(self) -> None:
        """Close the HTTP session."""
        if self.session:
            await self.session.close()
            self.session = None
