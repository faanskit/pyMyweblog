from typing import Any, Dict
import requests
from datetime import date
# from typing import Dict, Any, Optional


class MyWebLogClient:
    """Client for interacting with the MyWebLog API."""

    def __init__(self,
                 username: str,
                 password: str,
                 base_url: str =
                 "https://api.myweblog.se/api_mobile.php?version=2.0.3"):
        """Initialize the MyWebLog client.

        Args:
            api_key (str): API key for authentication.
            base_url (str): Base UR§L for the MyWebLog API
                            (default: https://api.myweblog.com).
        """
        self.apptoken = "mySecretApptoken"
        self.ac_id = "mySecretAcId"
        self.username = username
        self.password = password
        self.base_url = base_url.rstrip("/")
        self.session = requests.Session()

    def _myWeblogPost(
        self, endpoint: str, qtype: str, data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Send a POST request to the MyWebLog API.

        Args:
            endpoint (str): API endpoint to send the request to.
            data (Dict[str, Any]): Data to include in the request body.

        Returns:
            Dict[str, Any]: Response from the API.
        """
        url = f"{self.base_url}/{endpoint}"

        # Build data from the provided parameters and basic setup:
        # ========================================================
        # Input	        Format	Mandatory	Comment
        # qtype	        string	Y
        # mwl_u	        string	Y
        # mwl_p	        string	Y
        # returnType	string		        JSON
        # charset	    string              UTF-8
        # app_token	    string	Y
        # language	    string		        se
        # ========================================================
        data["qtype"] = qtype
        data["mwl_u"] = self.username
        data["mwl_p"] = self.password
        data["returnType"] = "json"
        data["charset"] = "UTF-8"
        data["app_token"] = self.apptoken
        data["language"] = "se"
        response = self.session.post(url, json=data)
        response.raise_for_status()
        return response.json()

    def getObjects(self) -> Dict[str, Any]:
        """Get objects from the MyWebLog API.

        Returns:
            Dict[str, Any]: Response from the API.
            Output	    Format	Comment
            ID	        int
            regnr	    string
            club_id	    int
            clubname	string
            model	    string
            objectThumbnail	jpg	150x100 px
        """
        # Build data from the provided parameters and basic setup:
        # ========================================================
        # Input	Format	Mandatory	Comment
        # includeObjectThumbnail	bool		0|1
        # ========================================================
        data = {
            "includeObjectThumbnail": 0
        }
        return self._myWeblogPost("getObjects", "getObjects", data)

    def getBookings(
        self, mybookings: bool = True, includeSun: bool = True
    ) -> Dict[str, Any]:
        """Get bookings from the MyWebLog API.

        Returns:
            Dict[str, Any]: Response from the API.
            Output	        Format	Comment
            ===============================
            ID	            int
            ac_id	        int
            regnr	        string
            bobject_cat	    int
            club_id	        int
            user_id	        int
            bStart	        timestamp
            bEnd	        timestamp
            typ	            string
            primary_booking	bool
            fritext	        string
            elevuserid	    int
            platserkvar	    int
            fullname	    string
            email	        string
            completeMobile	string

            sunData Output	Format	Comment
            ===============================
            refAirport	    Misc	Reference airport data
                                    such as name,
                                    designators and coordinates.
            dates	        Misc	Data for each included date,
                                    including morning twillight,
                                    sunrise, sunset and evening
                                    twillight.
        """
        # Build data from the provided parameters and basic setup:
        # ========================================================
        # Input	        Format	Mandatory	Comment
        # ac_id	        int
        # mybookings	bool		        0|1
        # from_date	    yyyy-mm-dd		    Default: [Today]
        # to_date	    yyyy-mm-dd
        # includeSun	bool		        0|1. Will include
        #               sunrise/sunset data for the user's reference
        #               airport and the selected dates. If no to_date
        #               is specified, one month will be used.
        # ========================================================
        today = date.today().strftime("%Y-%m-%d")
        data = {
            "ac_id": self.ac_id,
            "mybookings": int(mybookings),
            "from_date": today,
            "to_date": today,
            "includeSun": int(includeSun)
        }
        return self._myWeblogPost("getBookings", "getBookings", data)

    def close(self) -> None:
        """Close the HTTP session."""
        self.session.close()

    def __enter__(self) -> "MyWebLogClient":
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.close()
