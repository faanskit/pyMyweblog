# pyMyweblog

`pyMyweblog` is an asynchronous Python client library for the **MyWebLog Mobile API v5** (`v5.25.0`), featuring **OAuth 2.1 + PKCE** authentication. It is built to power the [Home Assistant MyWebLog integration](https://github.com/faanskit/ha-myweblog) as well as standalone CLI tools and automation scripts for pilots and aero clubs.

---

## Features

- **Modern API v5 REST Endpoints:** Direct asynchronous access to `/me`, `/objects`, `/bookings`, `/flightlogs`, `/transactions`, `/sun-times`, `/organization`, and `/me/expiry-dates`.
- **OAuth 2.1 with PKCE (`S256`):**
  - **Option 2 (Public Client):** Client ID only, no client secret required.
  - **Option 1 (Confidential Client):** Client ID + Client Secret (supported for Home Assistant `application_credentials`).
  - Single-use refresh token rotation with `asyncio.Lock` serialization.
  - Local loopback server (`http://localhost:5173/callback`) for one-time interactive browser login in CLI/dev mode.
- **Robust Error Handling:** Full RFC 9457 Problem Details (`application/problem+json`) mapping:
  - `MyWebLogAuthError` (401 / OAuth error)
  - `MyWebLogForbiddenError` (403)
  - `MyWebLogNotFoundError` (404)
  - `MyWebLogRateLimitError` (429 with `retry_after`)
  - `MyWebLogMaintenanceError` (503 with maintenance code `10060` and `retry_after`)
- **Transport Resilience:** Automatic single-retry recovery on stale keep-alive TCP connections (`aiohttp.ServerDisconnectedError`) and conditional `If-None-Match` / `304 Not Modified` ETag caching.
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
│   ├── __init__.py         # Package exports & version (1.0.0)
│   ├── auth.py             # OAuth 2.1 + PKCE, AbstractMyWebLogAuth, OAuth2PKCEAuth
│   ├── client.py           # v5 REST MyWebLogClient & legacy aliases
│   └── exceptions.py       # RFC 9457 Problem Details & error hierarchy
├── scripts/
│   ├── booking_cli.py      # Interactive aircraft booking management CLI
│   ├── myweblog.py         # Multi-operation query CLI
│   ├── reproduce_queue_bug.py # Live bug repro script and Markdown logger
│   └── verify_m1_live.py   # Live OAuth 2.1 PKCE verification utility
├── tests/
│   ├── test_auth.py        # PKCE, exchange, lock rotation, ETag & error tests
│   └── test_client.py      # v5 REST endpoints & backward-compatibility tests
├── pyproject.toml          # Package configuration (PEP 621, black, build-system)
└── .env.sample             # Sample environment configuration
```

---

## Configuration (`.env`)

For standalone scripts or local development, copy `.env.sample` to `.env`:

```env
MYWEBLOG_CLIENT_ID=9
MYWEBLOG_CLIENT_SECRET=mwlm1_your_secret_here   # Optional; omit for Public Client
MYWEBLOG_REDIRECT_URI=http://localhost:5173/callback
MYWEBLOG_AIRPLANE_ID=5599                      # Optional default aircraft ID
```

> **Note:** `.env` and `.myweblog_tokens.json` are excluded from git by `.gitignore` to prevent leaking tokens or credentials.

---

## Interactive CLI Tools

### 1. Interactive Booking CLI (`scripts/booking_cli.py`)

Manage airplane bookings directly from your terminal:

```bash
uv run --project pyMyweblog python scripts/booking_cli.py
```

**Features:**
- On first launch, opens your browser to log in via OAuth 2.1 and saves tokens to `.myweblog_tokens.json`.
- Displays active aircraft with models or categories (e.g. `SE-DUM (Aircraft)`).
- Lists upcoming bookings for the next 7 days, highlighting your own bookings with `[YOURS]`.
- Interactive creation of new bookings with custom dates, start times, and durations.
- Cancellation and ending ("cutting") of active bookings with automatic list refresh.

### 2. Multi-Operation Query CLI (`scripts/myweblog.py`)

Quickly inspect API v5 data:

```bash
# Interactive menu:
uv run --project pyMyweblog python scripts/myweblog.py

# Or via command line flags:
uv run --project pyMyweblog python scripts/myweblog.py -o   # GetObjects
uv run --project pyMyweblog python scripts/myweblog.py -m   # GetMe
uv run --project pyMyweblog python scripts/myweblog.py -b   # GetBookings
uv run --project pyMyweblog python scripts/myweblog.py -t   # GetTransactions
uv run --project pyMyweblog python scripts/myweblog.py -s   # GetSunTimes
uv run --project pyMyweblog python scripts/myweblog.py -e   # GetExpiryDates
```

---

## Python Library Usage

### Standalone Usage (with `OAuth2PKCEAuth`)

```python
import asyncio
import aiohttp
from pyMyweblog import MyWebLogClient, OAuth2PKCEAuth

async def main():
    async with aiohttp.ClientSession() as websession:
        auth = OAuth2PKCEAuth(
            websession=websession,
            client_id="9",
            client_secret="mwlm1_your_secret",  # Optional for Option 1
            redirect_uri="http://localhost:5173/callback",
            token_cache_path=".myweblog_tokens.json",
        )

        # Trigger browser login if no cached refresh token exists
        if not auth.refresh_token:
            await auth.async_interactive_login()

        client = MyWebLogClient(auth=auth)

        # Fetch current user
        me = await client.get_me()
        user = me.get("data", me)
        print("Logged in as:", user["name"]["full"])

        # Fetch aircraft
        objects = await client.get_objects()
        for obj in objects.get("data", []):
            time_total = obj.get("time_summary", {}).get("total", {})
            print(f"{obj['registration']}: Tach {time_total.get('tach')}, Landings {time_total.get('landings')}")

asyncio.run(main())
```

### Custom Auth Bridge (e.g. Home Assistant `OAuth2Session`)

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

Run the full unit test suite (20 tests covering auth, PKCE, lock rotation, ETag, and REST endpoints):

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
- **PyPI (Production):** Triggered on creating and publishing a GitHub Release with tag `v1.0.0`.

---

## License

This project is licensed under the MIT License. See [LICENSE](LICENSE) for details.
Maintainer: Marcus Karlsson (<marcus.karlsson@usa.net>)
