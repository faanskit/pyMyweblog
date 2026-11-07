"""A Python library for interacting with the MyWebLog API."""

__version__ = "1.1.0"

from .client import MyWebLogClient
from .exceptions import (
    MyWebLogError,
    MyWebLogAuthError,
    MyWebLogForbiddenError,
    MyWebLogNotFoundError,
    MyWebLogRateLimitError,
    MyWebLogMaintenanceError,
    parse_problem_response,
)
from .auth import (
    AbstractMyWebLogAuth,
    OAuth2PKCEAuth,
    ClientCredentialsAuth,
    DEFAULT_BASE_URL,
    MAIN_API_BASE_URL,
    generate_pkce_pair,
    build_authorize_url,
)

__all__ = [
    "MyWebLogClient",
    "MyWebLogError",
    "MyWebLogAuthError",
    "MyWebLogForbiddenError",
    "MyWebLogNotFoundError",
    "MyWebLogRateLimitError",
    "MyWebLogMaintenanceError",
    "parse_problem_response",
    "AbstractMyWebLogAuth",
    "OAuth2PKCEAuth",
    "ClientCredentialsAuth",
    "DEFAULT_BASE_URL",
    "MAIN_API_BASE_URL",
    "generate_pkce_pair",
    "build_authorize_url",
]
