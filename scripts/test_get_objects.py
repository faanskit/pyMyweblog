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


async def test_get_objects(username: str, password: str, app_secret: str) -> None:
    """Test fetching objects from MyWebLog API and print the result."""
    try:
        async with MyWebLogClient(
            username,
            password,
            app_token=None,
        ) as client:
            await client.obtainAppToken(app_secret)
            result = await client.getObjects()
            print("Objects retrieved from MyWebLog API:")
            pprint(result, indent=2)

    except aiohttp.ClientResponseError as e:
        print(f"HTTP Error: {e}")
        print(f"Status Code: {e.status}")
        print(f"Response Text: {e.message}")
        sys.exit(1)

    except aiohttp.ClientError as e:
        print(f"Request Error: {e}")
        sys.exit(1)

    except Exception as e:
        print(f"Unexpected Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    TEST_USERNAME = os.getenv("MYWEBLOG_USERNAME")
    TEST_PASSWORD = os.getenv("MYWEBLOG_PASSWORD")
    TEST_APPSECRET = os.getenv("APP_SECRET")

    if not all([TEST_USERNAME, TEST_PASSWORD, TEST_APPSECRET]):
        print(
            "Fel: Alla miljövariabler (MYWEBLOG_USERNAME, MYWEBLOG_PASSWORD) "
            " måste vara satta i .env-filen."
        )
        sys.exit(1)

    try:
        asyncio.run(test_get_objects(TEST_USERNAME, TEST_PASSWORD, TEST_APPSECRET))
    except Exception as e:
        print(f"Unexpected Error: {e}")
        sys.exit(1)
