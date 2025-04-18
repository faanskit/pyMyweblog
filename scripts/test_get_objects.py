import asyncio
import sys
import os
from pprint import pprint
import aiohttp
from pyMyweblog.client import MyWebLogClient

# Lägg till projektets rotmapp till sys.path (för lokal utveckling)
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))


async def test_get_objects(
    username: str,
    password: str,
    app_token: str,
    base_url: str
) -> None:
    """Test fetching objects from MyWebLog API and print the result."""
    try:
        async with MyWebLogClient(
            username,
            password,
            app_token,
            base_url
        ) as client:
            result = await client.getObjects()
            print("Objects retrieved from MyWebLog API:")
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
    # Hämta autentiseringsuppgifter från miljövariabler
    TEST_USERNAME = os.getenv("MYWEBLOG_USERNAME", "51-10208")
    TEST_PASSWORD = os.getenv("MYWEBLOG_PASSWORD", "Lillkuk!0")
    TEST_APPTOKEN = os.getenv("MYWEBLOG_APPTOKEN", "uuJH67Frw42s545!!MaKa!")
    TEST_BASE_URL = os.getenv(
        "MYWEBLOG_BASE_URL",
        "https://api.myweblog.se/api_mobile.php?version=2.0.3")

    asyncio.run(test_get_objects(
        TEST_USERNAME,
        TEST_PASSWORD,
        TEST_APPTOKEN,
        TEST_BASE_URL
    ))
