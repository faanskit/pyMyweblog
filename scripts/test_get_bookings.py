import asyncio
import sys
import os
from pprint import pprint
import aiohttp
from pyMyweblog.client import MyWebLogClient
import dotenv

# Use WindowsSelectorEventLoopPolicy to avoid "Event loop is closed" error on Windows
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

# Ladda miljövariabler från .env-filen
dotenv.load_dotenv()

# Lägg till projektets rotmapp till sys.path (för lokal utveckling)
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))


async def test_get_bookings(
    username: str, password: str, app_secret: str, airplaneId: str
) -> None:
    """Test fetching balance from MyWebLog API and print the result."""
    try:
        async with MyWebLogClient(
            username,
            password,
            app_token=None,
        ) as client:
            await client.obtainAppToken(app_secret)
            result = await client.getBookings(airplaneId)
            print("Bookings retrieved from MyWebLog API:")
            pprint(result, indent=2)

    except aiohttp.ClientResponseError as e:
        # Hantera HTTP-fel (t.ex. 401, 403, 404)
        print(f"HTTP Error: {e}")
        print(f"Status Code: {e.status}")
        print(f"Response Text: {e.message}")
        sys.exit(1)

    except aiohttp.ClientError as e:
        # Hantera andra nätverksrelaterade fel
        print(f"Request Error: {e}")
        sys.exit(1)
        # Hantera JSON-parsningsfel
        print(f"JSON Decode Error: {e}")
        # Försök att få rått svar från det senaste anropet
        # (kräver ändring i client.py)
        print("Check response text in client.py logs for more details.")
        sys.exit(1)

    except Exception as e:
        # Fånga oväntade fel
        print(f"Unexpected Error: {e}")
        sys.exit(1)
    finally:
        # client.close() is not needed because 'async with' handles cleanup
        pass


if __name__ == "__main__":
    # Hämta autentiseringsuppgifter från miljövariabler (ingen default)
    TEST_USERNAME = os.getenv("MYWEBLOG_USERNAME")
    TEST_PASSWORD = os.getenv("MYWEBLOG_PASSWORD")
    TEST_APPSECRET = os.getenv("APP_SECRET")
    TEST_AIRPLANE = os.getenv("MYWEBLOG_AIRPLANE_ID")

    if not all([TEST_USERNAME, TEST_PASSWORD, TEST_AIRPLANE, TEST_APPSECRET]):
        print(
            "Fel: Alla miljövariabler (MYWEBLOG_USERNAME, MYWEBLOG_PASSWORD, "
            "MYWEBLOG_AIRPLANE_ID, TEST_APPSECRET) måste vara satta i .env-filen."
        )
        sys.exit(1)

    try:
        asyncio.run(
            test_get_bookings(
                TEST_USERNAME, TEST_PASSWORD, TEST_APPSECRET, TEST_AIRPLANE
            )
        )
    except Exception as e:
        print(f"Unexpected Error: {e}")
        sys.exit(1)
