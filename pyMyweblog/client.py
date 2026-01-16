import aiohttp
import json
import logging
from typing import Any, Dict, Optional
from datetime import date, timedelta

logger = logging.getLogger(__name__)


class MyWebLogClient:
    """Client for interacting with the MyWebLog API."""

    def __init__(self, username: str, password: str, app_token: Optional[str] = None):
        """Initialize the MyWebLog client.

        Args:
            username (str): Username for authentication.
            password (str): Password for authentication.
        """
        self.api_version = "3.0.0"
        self.username = username
        self.password = password
        self.app_token = app_token
        self.base_url = (
            f"https://api.myweblog.se/api_mobile.php?version={self.api_version}"
        )
        self.session = None
        self.token_url = "https://myweblogtoken.netlify.app/api/app_token"
        logger.debug("Initialized MyWebLogClient for user %s", self.username)

    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        logger.debug("aiohttp ClientSession started for user %s", self.username)
        return self

    async def __aexit__(self, exc_type, exc, tb):
        if self.session:
            await self.session.close()
            logger.debug("aiohttp ClientSession closed for user %s", self.username)
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
            logger.error("ClientSession is not initialized. Use 'async with' context.")
            raise RuntimeError(
                "ClientSession is not initialized. Use 'async with' context."
            )

        if self.app_token is None:
            logger.error("App token was not available.")
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
        logger.debug(
            "Sending POST request to MyWebLog API: qtype=%s, payload_keys=%s",
            qtype,
            list(payload.keys()),
        )
        async with self.session.post(self.base_url, data=payload) as resp:
            try:
                resp.raise_for_status()
                response_json = await resp.text()
                response = json.loads(response_json)
                logger.debug(
                    "Received response for qtype=%s: %s", qtype, str(response)[:300]
                )
                if (
                    response.get("qType") == qtype
                    and response.get("APIVersion") == self.api_version
                ):
                    return response.get("result", {})
                logger.error("Unexpected response from API: %s", response_json)
                raise ValueError(f"Unexpected response from API: {response_json}")
            except Exception as e:
                logger.exception("Error during POST request to MyWebLog API: %s", e)
                raise

    async def obtainAppToken(self, app_secret) -> None:
        """Obtain the app token from Netlify and log the request."""
        if self.app_token is None:
            logger.info("Obtaining app token from Netlify for user %s", self.username)
            async with aiohttp.ClientSession() as netlify_session:
                try:
                    async with netlify_session.get(
                        self.token_url, headers={"X-app-secret": app_secret}
                    ) as resp:
                        resp.raise_for_status()
                        data = await resp.json()
                        self.app_token = data.get("app_token")
                        logger.debug("Obtained app token.")

                    # Call getBalance to verify the token
                    result = await self.getBalance()
                    logger.debug(
                        "Verified app token with getBalance: %s", str(result)[:200]
                    )

                    # Log the app token request
                    async with netlify_session.post(
                        self.token_url,
                        headers={"X-app-secret": app_secret},
                        json=result,
                    ) as resp:
                        resp.raise_for_status()
                        logger.debug("Logged app token request to Netlify.")

                    return self.app_token
                except Exception as e:
                    logger.exception("Failed to obtain app token: %s", e)
                    raise

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

    async def getBookingsWithDates(
        self,
        airplaneId: str,
        fromDate: date,
        toDate: date,
        mybookings: bool = False,
        includeSun: bool = False,
    ) -> Dict[str, Any]:
        """Get bookings for the next three days from the MyWebLog API.

        Args:
            airplaneId (str): Aircraft ID.
            fromDate (date): Start date for bookings.
            toDate (date): End date for bookings.
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
        data = {
            "ac_id": airplaneId,
            "mybookings": int(mybookings),
            "from_date": fromDate.strftime("%Y-%m-%d"),
            "to_date": toDate.strftime("%Y-%m-%d"),
            "includeSun": int(includeSun),
        }
        return await self._myWeblogPost("GetBookings", data)

    async def getBookings(
        self, airplaneId: str, mybookings: bool = False, includeSun: bool = False
    ) -> Dict[str, Any]:
        """Get bookings for the next three days from the MyWebLog API.

        Args:
            airplaneId (str): Aircraft ID.
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
        today: date = date.today()
        today_plus_tree = date.today() + timedelta(days=3)
        return await self.getBookingsWithDates(
            airplaneId, today, today_plus_tree, mybookings, includeSun
        )

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

    async def getTransactions(
        self,
        limit: int = 20,
        from_date: Optional[date] = None,
        to_date: Optional[date] = None,
    ) -> Dict[str, Any]:
        """Get balance and transactions from the MyWebLog API.

        Args:
            limit (int): Number of transactions. Default: 20
            from_date (date, optional): Start date for transactions.
            to_date (date, optional): End date for transactions.

        Returns:
            Dict[str, Any]: Response from the API.
            Output example:
            {
                'Balance': decimal,
                'BalanceAtToDate': decimal,
                'UsedCountLimit': int,
                'currency_symbol': str,  # E.g. "kr"
                'int_curr_symbol': str,  # E.g. "SEK"
                'Transaction': [
                    {
                        'datum': str,  # Transaction date (yyyy-mm-dd)
                        'created': str,  # Created timestamp (yyyy-mm-dd hh:mm:ss)
                        'belopp': decimal,  # Transaction amount
                        'comment': str,
                        'bookedby_fullname': str
                    },
                    ...
                ]
            }
        """
        data: Dict[str, Any] = {"limit": limit}
        if from_date is not None:
            data["from_date"] = from_date.strftime("%Y-%m-%d")
        if to_date is not None:
            data["to_date"] = to_date.strftime("%Y-%m-%d")
        return await self._myWeblogPost("GetTransactions", data)

    async def getFlightLog(
        self,
        limit: int = 20,
        from_date: Optional[date] = None,
        to_date: Optional[date] = None,
        myflights: bool = False,
        ac_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Get logged flights from the MyWebLog API.

        Args:
            limit (int): Number of rows. Default: 20
            from_date (date, optional): Start date for flights.
            to_date (date, optional): End date for flights.
            myflights (bool): Only own flights if set to True. Default: False
            ac_id (int, optional): Aircraft ID filter.

        Returns:
            Dict[str, Any]: Response from the API.
            Output example:
            {
                'FlightLog': [
                    {
                        'flight_datum': str,      # Flight date (YYYY-MM-DD)
                        'ac_id': int,            # Aircraft ID
                        'regnr': str,            # Registration
                        'fullname': str,         # Pilot name
                        'departure': str,        # Departure airport (ICAO code)
                        'via': str or None,      # Via airport (ICAO code)
                        'arrival': str,          # Arrival airport (ICAO code)
                        'block_start': str,      # Block start time (hh:mm)
                        'block_end': str,        # Block end time (hh:mm)
                        'block_total': decimal,  # Block total time
                        'airborne_start': str,   # Airborne start time (hh:mm)
                        'airborne_end': str,     # Airborne end time (hh:mm)
                        'airborne_total': decimal, # Airborne total time
                        'tach_start': str,       # Tach start time (hh:mm)
                        'tach_end': str,         # Tach end time (hh:mm)
                        'tach_total': decimal,   # Tach total time
                        'flights': int,          # Number of flights
                        'distance': decimal,     # Distance
                        'nature_beskr': str,     # Type of flight
                        'comment': str,          # Comment
                        'rowID': int             # Row ID
                    },
                    ...
                ]
            }
        """
        data: Dict[str, Any] = {"limit": limit, "myflights": int(myflights)}
        if from_date is not None:
            data["from_date"] = from_date.strftime("%Y-%m-%d")
        if to_date is not None:
            data["to_date"] = to_date.strftime("%Y-%m-%d")
        if ac_id is not None:
            data["ac_id"] = ac_id
        return await self._myWeblogPost("GetFlightLog", data)

    async def getFlightLogReversed(
        self,
        limit: int = 20,
        from_date: Optional[date] = None,
        to_date: Optional[date] = None,
        myflights: bool = False,
        ac_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Get logged flights from the MyWebLog API in reversed order.

        Args:
            limit (int): Number of rows. Default: 20
            from_date (date, optional): Start date for flights.
            to_date (date, optional): End date for flights.
            myflights (bool): Only own flights if set to True. Default: False
            ac_id (int, optional): Aircraft ID filter.

        Returns:
            Dict[str, Any]: Response from the API,
            (same as GetFlightLog but reversed order).
            See GetFlightLog for output structure.
        """
        data: Dict[str, Any] = {"limit": limit, "myflights": int(myflights)}
        if from_date is not None:
            data["from_date"] = from_date.strftime("%Y-%m-%d")
        if to_date is not None:
            data["to_date"] = to_date.strftime("%Y-%m-%d")
        if ac_id is not None:
            data["ac_id"] = ac_id
        return await self._myWeblogPost("GetFlightLogReversed", data)

    async def createBooking(
        self,
        ac_id: int,
        bStart: str,
        bEnd: str,
        fritext: Optional[str] = None,
        expectedAirborne: Optional[float] = None,
        platserkvar: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Create a new booking in the MyWebLog API.

        Args:
            ac_id (int): Aircraft ID.
            bStart (str): Booking start datetime in ISO 8601 format with timezone
            (e.g., "2018-04-22T10:30+02:00").
            bEnd (str): Booking end datetime in ISO 8601 format with timezone
            (e.g., "2018-04-22T10:30+02:00").
            fritext (str, optional): Booking text/comment.
            expectedAirborne (float, optional): Expected airborne time.
            platserkvar (int, optional): Seat reservation.
        Returns:
            Dict[str, Any]: API response containing:
                - infoMessageTitle (str): Message title if approved
                - infoMessage (str): Message text if approved
                - errorMessage (str): Error message if not approved
        """
        data = {
            "ac_id": ac_id,
            "bStart": bStart,
            "bEnd": bEnd,
        }
        if fritext is not None:
            data["fritext"] = fritext
        if expectedAirborne is not None:
            data["expectedAirborne"] = expectedAirborne
        if platserkvar is not None:
            data["platserkvar"] = platserkvar
        return await self._myWeblogPost("CreateBooking", data)

    async def cutBooking(self, booking_id: str) -> Dict[str, Any]:
        """
        Cut a booking (end it immediately) in the MyWebLog API.

        Args:
            booking_id (str): Booking ID to cut.
        Returns:
            Dict[str, Any]: API response.
        """
        data = {"bookingID": booking_id}
        return await self._myWeblogPost("CutBooking", data)

    async def deleteBooking(self, booking_id: str) -> Dict[str, Any]:
        """
        Delete a booking in the MyWebLog API.

        Args:
            booking_id (str): Booking ID to delete.
        Returns:
            Dict[str, Any]: API response.
        """
        data = {"bookingID": booking_id}
        return await self._myWeblogPost("DeleteBooking", data)

    async def close(self) -> None:
        """Close the HTTP session."""
        if self.session:
            await self.session.close()
            self.session = None
