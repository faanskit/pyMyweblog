"""Interactive CLI for managing MyWebLog bookings using API v5."""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta
import os
from pathlib import Path
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
from pyMyweblog.exceptions import MyWebLogError  # noqa: E402


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


def ask_text(message: str, default: str = "") -> str:
    """Prompt user for text using standard input."""
    try:
        prompt_str = f"{message} [{default}]: " if default else f"{message}: "
        val = input(prompt_str).strip()
        return val if val else default
    except (EOFError, KeyboardInterrupt):
        return default


def load_env() -> None:
    """Load environment variables from .env."""
    env_file = find_dotenv(usecwd=True)
    if env_file:
        load_dotenv(env_file)
    else:
        local_env = REPO_ROOT / ".env"
        if local_env.exists():
            load_dotenv(local_env)


def format_booking(booking: dict[str, Any]) -> str:
    """Format a booking object into a readable line."""
    booking_id = booking.get("id") or booking.get("ID")
    start = (
        booking.get("start_local") or booking.get("start_at") or booking.get("bStart")
    )
    end = booking.get("end_local") or booking.get("end_at") or booking.get("bEnd")

    user_info = booking.get("user")
    if isinstance(user_info, dict):
        user_name = user_info.get("name") or str(user_info.get("id"))
    else:
        user_name = booking.get("fullname") or "Unknown"

    def fmt(val: Any) -> str:
        if not val:
            return ""
        try:
            ts = int(val)
            return datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M")
        except (ValueError, TypeError):
            try:
                dt = datetime.fromisoformat(str(val))
                return dt.strftime("%Y-%m-%d %H:%M")
            except Exception:
                return str(val)

    start_str = fmt(start)
    end_str = fmt(end)
    is_own = booking.get("is_own", False)
    own_badge = " [YOURS]" if is_own else ""
    return f"{booking_id}: {start_str} - {end_str} ({user_name}){own_badge}"


def select_airplane_sync(
    airplanes: list[dict[str, Any]],
) -> dict[str, Any] | None:
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
    choices.append("Exit")

    answer = ask_select("Select an airplane:", choices=choices)
    if not answer or answer == "Exit":
        print("Goodbye!")
        return None
    selected_idx = choices.index(answer)
    return airplanes[selected_idx]


def prompt_new_booking() -> tuple[datetime, datetime] | tuple[None, None]:
    """Prompt user for new booking times."""
    today = datetime.now().strftime("%Y-%m-%d")
    date_str = ask_text("Booking date (YYYY-MM-DD):", default=today)
    start_time = ask_text("Start time (HH:MM, 24h):")
    length_min = ask_text("Length in minutes:")
    try:
        start_dt = datetime.strptime(f"{date_str} {start_time}", "%Y-%m-%d %H:%M")
        length = int(length_min)
        end_dt = start_dt + timedelta(minutes=length)
        return start_dt, end_dt
    except Exception as e:
        print(f"Invalid input: {e}")
        return None, None


async def main() -> None:
    """Main interactive booking loop."""
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

        # 1. Fetch user info
        me_resp = await client.get_me()
        user_data = me_resp.get("data", me_resp)
        name_obj = user_data.get("name") or {}
        fullname = (
            name_obj.get("full")
            if isinstance(name_obj, dict)
            else user_data.get("username", "Member")
        )
        print(f"\nWelcome, {fullname}!")

        # 2. Fetch airplanes
        objects_resp = await client.get_objects()
        objects_list = objects_resp.get("data", objects_resp.get("Object", []))
        airplanes = [
            obj for obj in objects_list if (obj.get("registration") or obj.get("regnr"))
        ]
        if not airplanes:
            print("No airplanes found in this organization.")
            return

        while True:
            # 3. Select airplane
            selected = select_airplane_sync(airplanes)
            if not selected:
                break
            airplane_id = int(selected["id"])
            reg = selected.get("registration") or selected.get("regnr")
            print(f"\n--- Selected aircraft: {reg} (ID: {airplane_id}) ---")

            # 4. Fetch bookings helper
            today = datetime.now().date()
            to_date = today + timedelta(days=7)

            async def refresh_bookings() -> list[dict[str, Any]]:
                resp = await client.get_bookings(
                    object_id=airplane_id,
                    date_from=today,
                    date_to=to_date,
                )
                b_list = resp.get("data", resp.get("Booking", []))
                print(f"\nCurrent bookings for {reg} (next 7 days):")
                if not b_list:
                    print("  No upcoming bookings.")
                else:
                    for b in b_list:
                        print("  ", format_booking(b))
                return b_list

            bookings = await refresh_bookings()

            while True:
                own_bookings = [
                    b
                    for b in bookings
                    if b.get("is_own") or b.get("fullname") == fullname
                ]
                menu_choices = ["Create a new booking"]
                if own_bookings:
                    menu_choices.append("Cancel one of your bookings")
                    menu_choices.append("Cut (end now) an active booking")
                menu_choices.append("Select another airplane")
                menu_choices.append("Exit")

                action = ask_select("What would you like to do?", choices=menu_choices)

                if action == "Create a new booking":
                    start_dt, end_dt = prompt_new_booking()
                    if not start_dt or not end_dt:
                        continue
                    # Local ISO 8601 with timezone
                    now_tz = datetime.now().astimezone().tzinfo
                    start_dt = start_dt.replace(tzinfo=now_tz)
                    end_dt = end_dt.replace(tzinfo=now_tz)
                    b_start = start_dt.isoformat()
                    b_end = end_dt.isoformat()

                    comment = ask_text("Comment (optional):")
                    print(f"Creating booking for {reg} ({b_start} -> {b_end})...")
                    try:
                        res = await client.create_booking(
                            object_id=airplane_id,
                            start_at=b_start,
                            end_at=b_end,
                            comment=comment or None,
                        )
                        print("Booking successfully created!")
                        if "messages" in res:
                            for msg in res["messages"]:
                                print(f"  Note: {msg}")
                        bookings = await refresh_bookings()
                    except MyWebLogError as err:
                        print(f"Failed to create booking: {err}")

                elif action == "Cancel one of your bookings":
                    choices = [format_booking(b) for b in own_bookings]
                    choices.append("Back")
                    b_ans = ask_select("Select booking to cancel:", choices=choices)
                    if b_ans and b_ans != "Back":
                        idx = choices.index(b_ans)
                        target_id = own_bookings[idx]["id"]
                        reason = ask_text("Cancellation reason (optional):")
                        try:
                            res = await client.cancel_booking(
                                booking_id=target_id, reason=reason or None
                            )
                            print(f"Booking {target_id} cancelled.")
                            if "messages" in res:
                                for msg in res["messages"]:
                                    if isinstance(msg, dict):
                                        msg_text = msg.get("text", msg)
                                    else:
                                        msg_text = msg
                                    print(f"  Note: {msg_text}")
                            bookings = await refresh_bookings()
                        except MyWebLogError as err:
                            print(f"Failed to cancel booking: {err}")

                elif action == "Cut (end now) an active booking":
                    choices = [format_booking(b) for b in own_bookings]
                    choices.append("Back")
                    b_ans = ask_select("Select booking to cut:", choices=choices)
                    if b_ans and b_ans != "Back":
                        idx = choices.index(b_ans)
                        target_id = own_bookings[idx]["id"]
                        try:
                            res = await client.cut_booking(booking_id=target_id)
                            print(f"Booking {target_id} cut (ended now).")
                            if "messages" in res:
                                for msg in res["messages"]:
                                    if isinstance(msg, dict):
                                        msg_text = msg.get("text", msg)
                                    else:
                                        msg_text = msg
                                    print(f"  Note: {msg_text}")
                            bookings = await refresh_bookings()
                        except MyWebLogError as err:
                            print(f"Failed to cut booking: {err}")

                elif action == "Select another airplane":
                    break
                elif action in ("Exit", None):
                    print("Goodbye!")
                    return


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nCancelled by user.")
        sys.exit(0)
