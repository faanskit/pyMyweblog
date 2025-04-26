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

## Prerequisites

To use the library, you need:
- A valid MyWebLog username and password.
- A valid `app_token` for MyWebLog [Mobile API](https://api.myweblog.se/index.php?page=mobile)

## Usage

The `MyWebLogClient` class provides methods to interact with the MyWebLog API, such as fetching objects and bookings.

### Example: Fetching Objects

```python
from pyMyweblog.client import MyWebLogClient

# Initialize the client
client = MyWebLogClient(
    username="your_username",
    password="your_password",
    app_token="your_apptoken",
)

# Fetch objects
objects = client.getObjects()
print(objects)

# Close the session
client.close()

# Alternatively, use as a context manager
with MyWebLogClient(
    username="your_username",
    password="your_password",
    app_token="your_apptoken",
) as client:
    objects = client.getObjects()
    print(objects)
```

### Example: Fetching Bookings

```python
from pyMyweblog.client import MyWebLogClient

with MyWebLogClient(
    username="your_username",
    password="your_password",
    app_token="your_apptoken",
) as client:
    bookings = client.getBookings(mybookings=True, includeSun=True)
    print(bookings)
```

## Testing the API

Before pushing any changes, please follow these steps to ensure everything works locally.

1. **Set environment variables** (recommended for security):
   ```bash
   export MYWEBLOG_USERNAME="your_username"
   export MYWEBLOG_PASSWORD="your_password"
   export MYWEBLOG_APPTOKEN="your_apptoken"
   ```

2. **Run the test script**:
   ```bash
   python scripts/test_get_objects.py
   ```

   This will fetch objects and print the API response in a formatted way using `pprint`.

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
   source venv/bin/activate  # On Windows: .\venv\Scripts\activate
   ```

3. **Install dependencies**:
   ```bash
   pip install -e .[dev]
   ```

### Running Tests Locally Before Pushing

To ensure your code adheres to the standards and passes tests, follow these steps before you push your changes:

1. **Install dependencies** (if not already done):
   ```bash
   pip install -e .[dev]
   ```

2. **Run format and lint checks**:
   - **Black**: Automatically formats your code to conform to Python’s PEP 8 style.
     ```bash
     black .
     ```

   - **Flake8**: Lints your code for style issues, such as unused imports or incorrect indentation.
     ```bash
     flake8 .
     ```

3. **Run unit tests**:
   - **Pytest**: Run all the tests in the `tests/` directory and verify they pass.
     ```bash
     pytest --ignore=scripts/test_get_objects.py --ignore=scripts/test_get_balance.py
     ```

   If all tests pass without errors, you're good to go!

### Running Unit Tests

Unit tests are located in the `tests/` directory and use `unittest`.

```bash
python -m unittest discover tests
```

### Modifying the Code

- The main API client is in `pyMyweblog/client.py`.
- Update `app_token` and `ac_id` in `MyWebLogClient` with valid values or make them configurable.
- Add new methods to `MyWebLogClient` for additional API endpoints as needed.

### Running Test Scripts

Test scripts are located in the `scripts/` directory and use `python`.

**Example #1**:
To test the GetObjects function, you can run this script:
```bash
python -m scripts.test_get_objects
```

**Example #2**:
To test the GetBalance function, you can run this script:
```bash
python -m scripts.test_get_balance
```

**Example #3**:
To test the GetBookings function, you can run this script:
```bash
python -m scripts.test_get_bookings
```

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
