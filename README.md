# pyMyweblog

`pyMyweblog` is an asynchronous Python client library supporting both the **MyWebLog Mobile API v5** (`v5.37.0`) and **MyWebLog Main API v5** (`v5.19.0`), featuring **OAuth 2.1 + PKCE** and **OAuth 2.0 Client Credentials** authentication. It is built to power the [Home Assistant MyWebLog integration](https://github.com/faanskit/ha-myweblog) as well as standalone CLI tools and background automation scripts for pilots and aero clubs.

---

## Features

- **Modern API v5 REST Endpoints:** Direct asynchronous access to `/objects`, `/bookings`, `/flightlogs`, `/transactions`, `/organization`, `/token` (Main API), `/me`, `/sun-times`, and `/me/expiry-dates` (Mobile API).
- **Dual Authentication Architecture:**
  - **Mobile API (OAuth 2.1 PKCE):** Member login via browser redirect with PKCE `S256` code challenges. Issues access tokens (1 hour) with rolling 90-day refresh tokens.
  - **Main API (OAuth 2.0 Client Credentials):** Server-to-server integration (`POST /oauth/token` with `client_id` and `client_secret`) with indefinite automated renewal. Ideal for club appliances (e.g. engine heaters) and dashboards where tokens must never expire.
- **Smart Model Normalization & Compatibility:**
  - Automatically synthesizes `model: {"name": ..., "designator": ...}` from Main API's `type_name` and `type_designator`, providing a consistent object structure across both APIs.
  - Automatically handles query parameter differences (e.g. strips `disclaimer` and `mine` when targeting Main API to prevent HTTP 400 Bad Request).
  - Defaults `date_from=date.today()` in `get_bookings()` when targeting Main API to mirror Mobile API's default behavior and avoid fetching years of historical bookings.
- **Robust Error Handling:** Full RFC 9457 Problem Details (`application/problem+json`) and RFC 6749 OAuth error mapping:
  - `MyWebLogAuthError` (401 / OAuth error)
  - `MyWebLogForbiddenError` (403)
  - `MyWebLogNotFoundError` (404)
  - `MyWebLogRateLimitError` (429 with `retry_after`)
  - `MyWebLogMaintenanceError` (503 with maintenance code `10060` and `retry_after`)
- **Transport Resilience:** Automatic token refresh and single-retry on HTTP 401, keep-alive reconnection on `aiohttp.ServerDisconnectedError`, and conditional `If-None-Match` / `304 Not Modified` ETag caching.
- **Backward Compatibility:** Preserves legacy v3 helper aliases (`getObjects`, `getBookings`, `getBalance`, `getTransactions`, `getFlightLog`, etc.).

---

## Installation

Install the package via pip:

```bash
pip install pyMyweblog
```

Or for local development using [uv](https://docs.astral.sh/uv/):

```bash
git clone https://github.com/faanskit/pyMyweblog.git
cd pyMyweblog
uv sync
```

---

## Project Structure

```text
pyMyweblog/
├── pyMyweblog/
│   ├── __init__.py         # Package exports & version (1.1.0)
│   ├── auth.py             # OAuth 2.1 PKCE, ClientCredentialsAuth, AbstractMyWebLogAuth
│   ├── client.py           # v5 REST MyWebLogClient & legacy aliases
│   └── exceptions.py       # RFC 9457 Problem Details & error hierarchy
├── scripts/
│   ├── booking_cli.py      # Interactive aircraft booking management CLI
│   └── myweblog.py         # Multi-operation query CLI
├── tests/
│   ├── test_auth.py        # PKCE, client credentials, refresh locks, ETag & error tests
│   └── test_client.py      # v5 REST endpoints & backward-compatibility tests
├── pyproject.toml          # Package configuration (PEP 621, black, build-system)
└── .env.sample             # Sample environment configuration
```

---

## Configuration (`.env`)

For standalone scripts or local development, copy `.env.sample` to `.env`:

```env
# Mode: "mobile" (default) or "main"
MYWEBLOG_API_MODE=mobile

# Mobile API (OAuth 2.1 PKCE)
MYWEBLOG_CLIENT_ID=9
MYWEBLOG_CLIENT_SECRET=mwlm1_your_secret_here   # Optional for Public Client
MYWEBLOG_REDIRECT_URI=http://localhost:5173/callback
MYWEBLOG_AIRPLANE_ID=5599                      # Optional default aircraft ID

# Main API (OAuth 2.0 Client Credentials)
# Switch MYWEBLOG_API_MODE=main to run against Main API:
# MYWEBLOG_API_MODE=main
# MYWEBLOG_CLIENT_ID=4711
# MYWEBLOG_CLIENT_SECRET=mwla1_your_api_token_here
```

> **Note:** `.env` and `.myweblog_tokens.json` are excluded from git by `.gitignore` to prevent leaking tokens or credentials.

---

## Interactive CLI Tools

### 1. Interactive Booking CLI (`scripts/booking_cli.py`)

Manage airplane bookings directly from your terminal in either Mobile API or Main API mode:

```bash
# Mobile API mode (default):
uv run --project pyMyweblog python scripts/booking_cli.py

# Main API mode (Client Credentials):
uv run --project pyMyweblog python scripts/booking_cli.py --api-mode main
```

**Features:**
- In Mobile API mode, opens your browser on first launch to log in via OAuth 2.1 PKCE.
- In Main API mode, authenticates non-interactively using your club's Client ID and API Token.
- Displays active aircraft with models or categories (e.g. `SE-DUM (Experimental)`).
- Lists upcoming bookings for the next 7 days, highlighting your own bookings with `[YOURS]`.
- Interactive creation of new bookings (supports `owner_id` for Main API).
- Cancellation and ending ("cutting") of active bookings with automatic list refresh.

### 2. Multi-Operation Query CLI (`scripts/myweblog.py`)

Quickly inspect API v5 data:

```bash
# Interactive menu:
uv run --project pyMyweblog python scripts/myweblog.py

# Query against Main API using command line flags:
uv run --project pyMyweblog python scripts/myweblog.py --api-mode main -k   # GetToken
uv run --project pyMyweblog python scripts/myweblog.py --api-mode main -o   # GetObjects
uv run --project pyMyweblog python scripts/myweblog.py --api-mode main -b   # GetBookings
uv run --project pyMyweblog python scripts/myweblog.py --api-mode main -f   # GetFlightLog
uv run --project pyMyweblog python scripts/myweblog.py --api-mode main -t   # GetTransactions
```

---

## Python Library Usage

### 1. Main API Usage (Client Credentials)

Ideal for server-to-server integrations, Home Assistant, and IoT automation:

```python
import asyncio
import aiohttp
from pyMyweblog import MyWebLogClient, ClientCredentialsAuth

async def main():
    async with aiohttp.ClientSession() as session:
        auth = ClientCredentialsAuth(
            websession=session,
            client_id="4711",
            client_secret="mwla1_your_api_token_here",
        )
        client = MyWebLogClient(auth=auth, api_mode="main")

        # 1. Verify token & permissions
        token_info = await client.get_token()
        data = token_info.get("data", {})
        print("Connected to:", data["organization"]["name"])
        print("Token owner:", data["owner"]["name"])
        print("Permissions:", data["rights"])

        # 2. Fetch aircraft with normalized models and meters
        objects = await client.get_objects()
        for plane in objects.get("data", []):
            model = plane.get("model", {})
            time_total = plane.get("time_summary", {}).get("total", {})
            print(
                f"{plane['registration']} ({model.get('name')}): "
                f"Tach {time_total.get('tach')}, Landings {time_total.get('landings')}"
            )

asyncio.run(main())
```

### 2. Mobile API Usage (OAuth 2.1 PKCE)

Ideal for personal member accounts:

```python
import asyncio
import aiohttp
from pyMyweblog import MyWebLogClient, OAuth2PKCEAuth

async def main():
    async with aiohttp.ClientSession() as websession:
        auth = OAuth2PKCEAuth(
            websession=websession,
            client_id="9",
            client_secret="mwlm1_your_secret",  # Optional
            redirect_uri="http://localhost:5173/callback",
            token_cache_path=".myweblog_tokens.json",
        )

        # Trigger browser login if no cached refresh token exists
        if not auth.refresh_token:
            await auth.async_interactive_login()

        client = MyWebLogClient(auth=auth, api_mode="mobile")

        # Fetch current user profile
        me = await client.get_me()
        user = me.get("data", me)
        print("Logged in as:", user["name"]["full"])

asyncio.run(main())
```

### 3. Custom Auth Bridge (e.g. Home Assistant `OAuth2Session`)

Subclass `AbstractMyWebLogAuth` to connect `MyWebLogClient` to any external token manager:

```python
from aiohttp import ClientSession
from pyMyweblog import AbstractMyWebLogAuth, MyWebLogClient

class HomeAssistantAuthBridge(AbstractMyWebLogAuth):
    def __init__(self, websession: ClientSession, oauth_session) -> None:
        super().__init__(websession)
        self._oauth_session = oauth_session

    async def async_get_access_token(self) -> str:
        await self._oauth_session.async_ensure_token_valid()
        return str(self._oauth_session.token["access_token"])

# Instantiate client:
# client = MyWebLogClient(auth=HomeAssistantAuthBridge(session, oauth_session))
```

---

## Development & Testing

### Running Tests

Run the full unit test suite (30 tests covering PKCE, client credentials, 401 retry, lock rotation, ETag, and REST endpoints):

```bash
uv run pytest tests
```

### Linting & Formatting

Ensure compliance with PEP 8 and project style:

```bash
# Check formatting with Black (line-length: 88)
uv run black --check pyMyweblog scripts tests

# Format code
uv run black pyMyweblog scripts tests

# Lint with Flake8
uv run flake8 --config .flake8 pyMyweblog scripts tests
```

---

## Publishing to PyPI

This repository uses GitHub Actions for automated publishing:

- **TestPyPI:** Pushes to `main` with commit message containing `[dev-release]`.
- **PyPI (Production):** Triggered on creating and publishing a GitHub Release with tag `v1.1.0`.

---

## License

This project is licensed under the MIT License. See [LICENSE](LICENSE) for details.
Maintainer: Marcus Karlsson (<marcus.karlsson@usa.net>)
