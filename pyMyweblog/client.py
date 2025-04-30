import aiohttp
import json
from typing import Any, Dict
from datetime import date, timedelta


class MyWebLogClient:
    """Client for interacting with the MyWebLog API."""

    def __init__(self, username: str, password: str, app_token: str = None):
        """Initialize the MyWebLog client.

        Args:
            username (str): Username for authentication.
            password (str): Password for authentication.
        """
        self.api_version = "2.0.3"
        self.username = username
        self.password = password
        self.app_token = app_token
        self.base_url = (
            f"https://api.myweblog.se/api_mobile.php?version={self.api_version}"
        )
        self.session = None
        self.token_url = "https://myweblogtoken.netlify.app/api/app_token"

    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self

    async def __aexit__(self, exc_type, exc, tb):
        if self.session:
            await self.session.close()
            self.session = None

    async def _myWeblogPost(self, qtype: str, data: Dict[str, Any]) -> Dict[str, Any]:
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

        if self.app_token is None:
            raise RuntimeError("App token was not available.")

        payload = {
            "qtype": qtype,
            "mwl_u": self.username,
            "mwl_p": self.password,
            "returnType": "JSON",
            "charset": "UTF-8",
            "app_token": self.app_token,
            "language": "se",
            **data,
        }
        async with self.session.post(self.base_url, data=payload) as resp:
            resp.raise_for_status()
            # API returns text/plain; manually decode as JSON
            response_json = await resp.text()
            response = json.loads(response_json)
            if (
                response.get("qType") == qtype
                and response.get("APIVersion") == self.api_version
            ):
                return response.get("result", {})
            raise ValueError(f"Unexpected response from API: {response_json}")

    async def obtainAppToken(self, app_secret) -> None:
        """Obtain the app token from Netlify and log the request."""
        if self.app_token is None:
            async with aiohttp.ClientSession() as netlify_session:
                # Obtain the app token
                async with netlify_session.get(
                    self.token_url, headers={"X-app-secret": app_secret}
                ) as resp:
                    resp.raise_for_status()
                    data = await resp.json()
                    self.app_token = data.get("app_token")

                # Call getBalance to verify the token
                result = await self.getBalance()

                # Log the app token request
                async with netlify_session.post(
                    self.token_url,
                    headers={"X-app-secret": app_secret},
                    json=result,
                ) as resp:
                    resp.raise_for_status()

                # Return the app token
                return self.app_token

    async def getObjects(self) -> Dict[str, Any]:
        """Get objects from the MyWebLog API.

        Returns:
            Dict[str, Any]: Response from the API.
            Output example:
            {
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
        data = {"includeObjectThumbnail": 0}
        return await self._myWeblogPost("GetObjects", data)

    async def getBookings(
        self, airplaneId: str, mybookings: bool = False, includeSun: bool = False
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
        today_plus_tree = (date.today() + timedelta(days=3)).strftime("%Y-%m-%d")
        data = {
            "ac_id": airplaneId,
            "mybookings": int(mybookings),
            "from_date": today,
            "to_date": today_plus_tree,
            "includeSun": int(includeSun),
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
