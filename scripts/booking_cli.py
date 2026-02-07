import os
import sys
import asyncio
from dotenv import load_dotenv
from pyMyweblog.client import MyWebLogClient
from datetime import datetime, timedelta

try:
    import questionary
except ImportError:
    print(
        "questionary is required for interactive menus. "
        "Install with: pip install questionary"
    )
    sys.exit(1)

load_dotenv()
USERNAME = os.getenv("MYWEBLOG_USERNAME")
PASSWORD = os.getenv("MYWEBLOG_PASSWORD")
APP_SECRET = os.getenv("APP_SECRET")


def format_booking(booking):
    owner = booking.get("fullname", "")
    start = booking.get("bStart", "")
    end = booking.get("bEnd", "")
    booking_id = booking.get("ID", "")

    def fmt(val):
        # Try to parse as int timestamp, else ISO string
        try:
            ts = int(val)
            return datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M")
        except (ValueError, TypeError):
            try:
                dt = datetime.fromisoformat(val)
                return dt.strftime("%Y-%m-%d %H:%M")
            except Exception:
                return str(val)

    start_fmt = fmt(start)
    end_fmt = fmt(end)
    return f"{booking_id}: {start_fmt} - {end_fmt} ({owner})"


def select_airplane_sync(airplanes):
    choices = [f"{a['regnr']} ({a['model']})" for a in airplanes]
    answer = questionary.select("Select an airplane:", choices=choices).ask()
    if not answer:
        print("Goodbye!")
        return None
    selected_idx = choices.index(answer)
    return airplanes[selected_idx]


def select_airplane_with_exit(airplanes):
    choices = [f"{a['regnr']} ({a['model']})" for a in airplanes]
    choices.append("Exit")
    answer = questionary.select("Select an airplane:", choices=choices).ask()
    if not answer or answer == "Exit":
        print("Goodbye!")
        return None
    selected_idx = choices.index(answer)
    return airplanes[selected_idx]


def select_booking_sync(bookings, current_user):
    choices = []
    for b in bookings:
        owner = b.get("fullname", "")
        label = format_booking(b)
        if owner == current_user:
            label += " [YOURS]"
        choices.append(label)
    answer = questionary.select("Select a booking to delete:", choices=choices).ask()
    if not answer:
        return None
    selected_idx = choices.index(answer)
    return bookings[selected_idx]


def prompt_new_booking():
    today = datetime.now().strftime("%Y-%m-%d")
    date_str = questionary.text("Booking date (YYYY-MM-DD):", default=today).ask()
    start_time = questionary.text("Start time (HH:MM, 24h):").ask()
    length_min = questionary.text("Length in minutes:").ask()
    try:
        start_dt = datetime.strptime(f"{date_str} {start_time}", "%Y-%m-%d %H:%M")
        length = int(length_min)
        end_dt = start_dt + timedelta(minutes=length)
        return start_dt, end_dt
    except Exception as e:
        print(f"Invalid input: {e}")
        return None, None


def run_async(coro):
    return asyncio.run(coro)


def main():
    if not USERNAME or not PASSWORD or not APP_SECRET:
        print(
            "Missing required environment variables: "
            "MYWEBLOG_USERNAME, MYWEBLOG_PASSWORD, APP_SECRET"
        )
        sys.exit(1)

    # Step 1: Get user info
    async def get_user_info():
        async with MyWebLogClient(USERNAME, PASSWORD, app_token=None) as client:
            await client.obtainAppToken(APP_SECRET)
            balance = await client.getBalance()
            return balance.get("fullname")

    fullname = run_async(get_user_info())
    print(f"Welcome, {fullname}!")

    # Step 2: Get airplanes
    async def get_airplanes():
        async with MyWebLogClient(USERNAME, PASSWORD, app_token=None) as client:
            await client.obtainAppToken(APP_SECRET)
            objects = await client.getObjects()
            return [
                obj
                for obj in objects.get("Object", [])
                if obj.get("regnr")
                and obj.get("model")
                and not obj.get("model", "").lower().startswith("x")
            ]

    airplanes = run_async(get_airplanes())
    if not airplanes:
        print("No airplanes available.")
        return

    # Step 3: Select airplane
    selected_airplane = select_airplane_with_exit(airplanes)
    if not selected_airplane:
        return
    airplane_id = selected_airplane["ID"]
    regnr = selected_airplane["regnr"]
    print(f"Selected: {regnr}")

    # Step 4: Fetch and list bookings
    async def get_bookings(ac_id):
        async with MyWebLogClient(USERNAME, PASSWORD, app_token=None) as client:
            await client.obtainAppToken(APP_SECRET)
            result = await client.getBookings(ac_id)
            return result.get("Booking", [])

    now_ts = int(datetime.now().timestamp())

    # Only show bookings that are active or in the future
    def is_future_or_active(b):
        try:
            return int(b.get("bEnd", 0)) >= now_ts
        except Exception:
            return True  # fallback: show if can't parse

    def show_bookings(bookings):
        if not bookings:
            print("No bookings for this airplane.")
        else:
            print("Current bookings:")
            for b in bookings:
                print("  ", format_booking(b))

    bookings = [
        b for b in run_async(get_bookings(airplane_id)) if is_future_or_active(b)
    ]
    show_bookings(bookings)

    while True:
        own_bookings = [b for b in bookings if b.get("fullname") == fullname]
        menu_choices = ["Create a new booking"]
        if own_bookings:
            menu_choices.append("Delete one of your bookings")
        menu_choices.append("Select another airplane")
        menu_choices.append("Exit")
        action = questionary.select(
            "What would you like to do?", choices=menu_choices
        ).ask()
        if action == "Create a new booking":
            start_dt, end_dt = prompt_new_booking()
            if not start_dt or not end_dt:
                continue
            # Convert to ISO 8601 format with timezone (using system timezone offset)
            bStart = start_dt.strftime("%Y-%m-%dT%H:%M%z")
            bEnd = end_dt.strftime("%Y-%m-%dT%H:%M%z")
            # Format timezone offset to include colon: +02:00 instead of +0200
            bStart = bStart[:-2] + ":" + bStart[-2:]
            bEnd = bEnd[:-2] + ":" + bEnd[-2:]
            duration_min = int((end_dt - start_dt).total_seconds() // 60)
            # Get regnr for friendly message
            regnr = None
            for a in airplanes:
                if a["ID"] == airplane_id:
                    regnr = a["regnr"]
                    break
            regnr = regnr or str(airplane_id)
            confirm_msg = (
                f"You will now book {regnr} for {duration_min} minutes. "
                "Please confirm."
            )
            confirm = questionary.confirm(confirm_msg).ask()
            if not confirm:
                print("Booking creation cancelled.")
                continue

            async def create_booking():
                async with MyWebLogClient(USERNAME, PASSWORD, app_token=None) as client:
                    await client.obtainAppToken(APP_SECRET)
                    return await client.createBooking(
                        int(airplane_id), bStart, bEnd, fritext=fullname
                    )

            resp = run_async(create_booking())
            if resp.get("infoMessageTitle") or resp.get("infoMessage"):
                print(
                    f"Booking created successfully! "
                    f"{resp.get('infoMessageTitle', '')}: "
                    f"{resp.get('infoMessage', '').strip()}"
                )
            elif resp.get("errorMessage"):
                print(f"Booking creation failed: {resp.get('errorMessage')}")
            else:
                print(f"Booking creation failed: {resp}")
        elif action == "Delete one of your bookings":
            own_bookings = [b for b in bookings if b.get("fullname") == fullname]
            if not own_bookings:
                print("You have no bookings to delete.")
                continue
            to_delete = select_booking_sync(own_bookings, fullname)
            if not to_delete:
                continue

            async def delete_booking():
                async with MyWebLogClient(USERNAME, PASSWORD, app_token=None) as client:
                    await client.obtainAppToken(APP_SECRET)
                    return await client.deleteBooking(to_delete["ID"])

            resp = run_async(delete_booking())
            if resp.get("Result") == "OK":
                print(f"Booking deleted successfully! Booking ID: {to_delete['ID']}")
            elif resp.get("errorMessage"):
                print(f"Booking deletion failed: {resp['errorMessage']}")
            else:
                print(f"Booking deletion failed: {resp}")
        elif action == "Select another airplane":
            # Go back to airplane selection
            selected_airplane = select_airplane_sync(airplanes)
            if not selected_airplane:
                print("Goodbye!")
                break
            airplane_id = selected_airplane["ID"]
            regnr = selected_airplane["regnr"]
            print(f"Selected: {regnr}")
            bookings = [
                b
                for b in run_async(get_bookings(airplane_id))
                if is_future_or_active(b)
            ]
            show_bookings(bookings)
            continue
        elif action == "Exit":
            print("Goodbye!")
            break
        # Refresh bookings after any action
        bookings = [
            b for b in run_async(get_bookings(airplane_id)) if is_future_or_active(b)
        ]


if __name__ == "__main__":
    main()
