# pyMyweblog Python Library

`pyMyweblog` is a Python library for interacting with the MyWebLog API, designed to fetch objects and bookings for aviation-related data. It is intended for use in Home Assistant integrations or other Python applications requiring access to MyWebLog services.

## Installation

Install the library via pip:

```bash
pip install pyMyweblog
```

Alternatively, for local development, clone the repository and install it in editable mode:

```bash
git clone https://github.com/faanskit/pyMyweblog.git
cd pyMyweblog
pip install -e .
```

---

## Project Structure

- `pyMyweblog/` — Main package, contains the API client (`client.py`).
- `scripts/myweblog.py` — Interactive CLI utility for querying MyWebLog API.
- `tests/test_client.py` — Unit tests for the API client.

---

## Prerequisites

To use the library or CLI, you need:
- A valid MyWebLog username and password.
- A valid **App Secret** (not app_token) for the MyWebLog API.

Set these as environment variables:
- `MYWEBLOG_USERNAME`
- `MYWEBLOG_PASSWORD`
- `APP_SECRET`

## Usage

### Interactive CLI Utility

You can use the interactive CLI to fetch objects, bookings, balance, transactions, and flight logs:

```bash
python -m scripts.myweblog
```

You will be prompted to select an operation and, for bookings, to select an airplane. Make sure the required environment variables are set or exported before running.

### Booking CLI Utility (`scripts/booking_cli.py`)

This script provides an interactive command-line interface for managing airplane bookings via the MyWebLog API.

**Features:**
- View available airplanes
- Create new bookings with confirmation prompts
- Delete your own bookings with confirmation prompts
- User-friendly and structured output

**How to Run:**

```bash
python -m scripts.booking_cli
```

**Requirements:**
- Environment variables must be set: `MYWEBLOG_USERNAME`, `MYWEBLOG_PASSWORD`, `APP_SECRET`
- The `questionary` package must be installed for interactive prompts:

```bash
pip install questionary
```

**Usage Flow:**
- On start, you will be welcomed and asked to select an airplane
- You can view, create, or delete bookings for the selected airplane
- All critical actions (creation/deletion) require confirmation before proceeding
- Exit the CLI at any time by selecting "Exit" from the menu

### Library Usage: MyWebLogClient

You can also use the API client in your own Python code:

```python
from pyMyweblog.client import MyWebLogClient
import asyncio
import os

async def main():
    client = MyWebLogClient(
        username=os.getenv("MYWEBLOG_USERNAME"),
        password=os.getenv("MYWEBLOG_PASSWORD"),
        app_token=None,  # Will be fetched using APP_SECRET
    )
    await client.obtainAppToken(os.getenv("APP_SECRET"))
    objects = await client.getObjects()
    print(objects)
    await client.close()

asyncio.run(main())
```

## Testing

Unit tests are located in `tests/test_client.py` and use the `unittest` framework. To run all tests:

```bash
python -m unittest discover tests
```

You can also run a specific test file:

```bash
python -m unittest tests.test_client
```

### Requirements

For development and running tests, install all dependencies (including test and CLI requirements):

```bash
pip install -e .[dev]
```

If you only want to use the CLI utility, you must also install `questionary`:

```bash
pip install questionary
```

## Development

### Setting Up the Development Environment

1. **Clone the repository**:
   ```bash
   git clone https://github.com/faanskit/pyMyweblog.git
   cd pyMyweblog
   ```

2. **Create and activate a virtual environment**:
   ```bash
   python -m venv venv
   # On Unix/macOS:
   source venv/bin/activate
   # On Windows:
   .\venv\Scripts\activate
   ```

3. **Install dependencies**:
   ```bash
   pip install -e .[dev]
   ```

4. **Format and lint your code**:
   ```bash
   black .
   flake8 .
   ```

5. **Run unit tests**:
   ```bash
   python -m unittest discover tests
   ```

### Modifying the Code

- The main API client is in `pyMyweblog/client.py`.
- Add or update methods in `MyWebLogClient` for additional API endpoints as needed.
- The CLI utility is in `scripts/myweblog.py` and can be extended for more interactive features.

## CI/CD and Publishing to PyPI and TestPyPI

This project uses **GitHub Actions** to automatically build and publish the package to **TestPyPI** and **PyPI**. Two separate workflows are configured:

---

### 🔁 Publishing to TestPyPI

This workflow runs **on every push to `main`** _if_ the commit message contains `[dev-release]`.

#### How to trigger a TestPyPI release:

1. **Update the version in `pyproject.toml`**  
   Use a development version (ending in `.devN`), for example:
   ```toml
   version = "0.2.0.dev1"
   ```

2. **Commit and push with a trigger message**:
   ```bash
   git add pyproject.toml
   git commit -m "test release 0.2.0.dev1 [dev-release]"
   git push origin main
   ```

3. The workflow will run and upload the package to:  
   [https://test.pypi.org/project/pyMyweblog](https://test.pypi.org/project/pyMyweblog)

---

### 🚀 Publishing to PyPI (Production)

This workflow runs **only when a GitHub Release is published**. Use this for stable releases (i.e., versions without `.dev`).

#### How to publish a production release:

1. **Update the version in `pyproject.toml`**, for example:
   ```toml
   version = "0.2.0"
   ```

2. **Commit and push**:
   ```bash
   git add pyproject.toml
   git commit -m "release 0.2.0"
   git push origin main
   ```

3. **Create a GitHub Release**:
   - Go to [Releases](https://github.com/faanskit/pyMyweblog/releases)
   - Click **"Draft a new release"**
   - Tag: `v0.2.0`
   - Title/message: `Release 0.2.0`
   - Click **"Publish release"**

4. The workflow will run and upload the package to:  
   [https://pypi.org/project/pyMyweblog](https://pypi.org/project/pyMyweblog)

---

### 🔐 API Tokens

To enable publishing from CI/CD, you need to configure the following GitHub Secrets:

- `TEST_PYPI_API_TOKEN` – from [TestPyPI](https://test.pypi.org/manage/account/)
- `PYPI_API_TOKEN` – from [PyPI](https://pypi.org/manage/account/)

Add these under:  
**GitHub Repo → Settings → Secrets and variables → Actions → New repository secret**

## Contributing

Contributions are welcome! Please submit issues or pull requests to the [GitHub repository](https://github.com/faanskit/pyMyweblog).

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.

For support, contact the maintainer at [marcus.karlsson@usa.net].
