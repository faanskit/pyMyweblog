"""CLI tool for interacting with the MyWebLog API v5."""

from __future__ import annotations

import argparse
import asyncio
import os
from pathlib import Path
from pprint import pprint
import sys
from typing import Any

import aiohttp
from dotenv import find_dotenv, load_dotenv

# Ensure pyMyweblog is in sys.path
SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from pyMyweblog.auth import OAuth2PKCEAuth  # noqa: E402
from pyMyweblog.client import MyWebLogClient  # noqa: E402

AVAILABLE_OPERATIONS = [
    ("GetObjects", "get_objects", "-o"),
    ("GetBookings", "get_bookings", "-b"),
    ("GetMe", "get_me", "-m"),
    ("GetTransactions", "get_transactions", "-t"),
    ("GetFlightLog", "get_flight_log", "-f"),
    ("GetFlightLogReversed", "get_flight_log_reversed", "-r"),
    ("GetSunTimes", "get_sun_times", "-s"),
    ("GetExpiryDates", "get_expiry_dates", "-e"),
]


def ask_select(message: str, choices: list[str]) -> str | None:
    """Prompt user to select from a list using standard input."""
    print(f"\n{message}")
    for i, choice in enumerate(choices, 1):
        print(f"  [{i}] {choice}")
    while True:
        try:
            prompt_str = f"Select choice (1-{len(choices)} or 'q' to quit): "
            raw = input(prompt_str).strip()
            if raw.lower() in ("q", "quit", "exit"):
                return None
            idx = int(raw)
            if 1 <= idx <= len(choices):
                return choices[idx - 1]
            print(f"Please enter a number between 1 and {len(choices)}.")
        except (ValueError, EOFError, KeyboardInterrupt):
            return None


def ask_checkbox(message: str, choices: list[str]) -> list[str]:
    """Prompt user to select multiple items using standard input."""
    print(f"\n{message}")
    for i, choice in enumerate(choices, 1):
        print(f"  [{i}] {choice}")
    try:
        raw = input("Enter comma-separated numbers (e.g. 1, 3) or 'all': ").strip()
        if raw.lower() == "all":
            return choices
        if not raw:
            return []
        selected = []
        for part in raw.split(","):
            part = part.strip()
            if part.isdigit() and 1 <= int(part) <= len(choices):
                selected.append(choices[int(part) - 1])
        return selected
    except (EOFError, KeyboardInterrupt):
        return []


def load_env() -> None:
    """Load environment variables from .env."""
    env_file = find_dotenv(usecwd=True)
    if env_file:
        load_dotenv(env_file)
    else:
        local_env = REPO_ROOT / ".env"
        if local_env.exists():
            load_dotenv(local_env)


def select_airplane_sync(
    airplanes: list[dict[str, Any]],
) -> tuple[int, str] | None:
    """Prompt user to select an airplane from a list."""
    choices = []
    for a in airplanes:
        reg = a.get("registration") or a.get("regnr") or str(a.get("id"))
        model_info = a.get("model")
        model_name = (
            (model_info.get("name") or model_info.get("designator"))
            if isinstance(model_info, dict)
            else str(model_info or "")
        )
        if not model_name:
            cat_info = a.get("category")
            model_name = (
                cat_info.get("name")
                if isinstance(cat_info, dict)
                else (a.get("comment") or "")
            )
        label = f"{reg} ({model_name})" if model_name else str(reg)
        choices.append(label)

    answer = ask_select("Select airplane to fetch bookings for:", choices=choices)
    if not answer:
        print("Goodbye!")
        return None
    selected_idx = choices.index(answer)
    chosen = airplanes[selected_idx]
    reg = chosen.get("registration") or chosen.get("regnr") or str(chosen.get("id"))
    return int(chosen["id"]), reg


async def run_operation(client: MyWebLogClient, op: str) -> None:
    """Run an individual API operation."""
    if op in ("get_objects", "getObjects"):
        result = await client.get_objects()
        print(f"Result for {op}:")
        pprint(result)
    elif op in ("get_bookings", "getBookings"):
        objects_result = await client.get_objects()
        objects_list = objects_result.get("data", objects_result.get("Object", []))
        airplanes = [
            obj for obj in objects_list if (obj.get("registration") or obj.get("regnr"))
        ]
        if not airplanes:
            print("No airplanes found for bookings.")
            return

        selection = await asyncio.to_thread(select_airplane_sync, airplanes)
        if not selection:
            return
        airplane_id, regnr = selection
        result = await client.get_bookings(object_id=airplane_id)
        print(f"Result for {op} ({regnr}):")
        pprint(result)
    elif op in ("get_me", "getBalance", "GetMe"):
        result = await client.get_me()
        print(f"Result for {op}:")
        pprint(result)
    elif op in ("get_transactions", "getTransactions"):
        result = await client.get_transactions(limit=20)
        print(f"Result for {op}:")
        pprint(result)
    elif op in ("get_flight_log", "getFlightLog"):
        result = await client.get_flight_logs(limit=20, order="asc")
        print(f"Result for {op}:")
        pprint(result)
    elif op in ("get_flight_log_reversed", "getFlightLogReversed"):
        result = await client.get_flight_logs(limit=20, order="desc")
        print(f"Result for {op}:")
        pprint(result)
    elif op in ("get_sun_times", "GetSunTimes"):
        result = await client.get_sun_times()
        print(f"Result for {op}:")
        pprint(result)
    elif op in ("get_expiry_dates", "GetExpiryDates"):
        result = await client.get_expiry_dates()
        print(f"Result for {op}:")
        pprint(result)
    else:
        print(f"Unknown operation: {op}")


async def main(selected_ops: list[str]) -> None:
    """Main CLI entrypoint."""
    load_env()
    client_id = os.getenv("MYWEBLOG_CLIENT_ID", "9")
    client_secret = os.getenv("MYWEBLOG_CLIENT_SECRET")
    redirect_uri = os.getenv("MYWEBLOG_REDIRECT_URI", "http://localhost:5173/callback")
    token_cache_path = REPO_ROOT / ".myweblog_tokens.json"

    async with aiohttp.ClientSession() as session:
        auth = OAuth2PKCEAuth(
            websession=session,
            client_id=client_id,
            client_secret=client_secret,
            redirect_uri=redirect_uri,
            token_cache_path=token_cache_path,
        )

        if not auth.refresh_token:
            print("[OAuth] No valid token found. Starting browser login...")
            await auth.async_interactive_login()

        client = MyWebLogClient(auth=auth)
        for op in selected_ops:
            await run_operation(client, op)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="MyWebLog API v5 Utility")
    for op_name, op_func, short_code in AVAILABLE_OPERATIONS:
        parser.add_argument(
            short_code,
            f"--{op_func.replace('_', '-')}",
            dest=op_func,
            action="store_true",
            help=f"Run {op_name}",
        )
    args = parser.parse_args()

    selected = [
        op_func
        for _, op_func, _ in AVAILABLE_OPERATIONS
        if getattr(args, op_func, False)
    ]

    if not selected:
        menu_choices = [op_name for op_name, _, _ in AVAILABLE_OPERATIONS]
        answer = ask_checkbox(
            "Select one or more operations to run:", choices=menu_choices
        )
        if not answer:
            print("Goodbye!")
            sys.exit(0)
        selected = [AVAILABLE_OPERATIONS[menu_choices.index(sel)][1] for sel in answer]

    try:
        asyncio.run(main(selected))
    except KeyboardInterrupt:
        print("\nCancelled by user.")
        sys.exit(0)
