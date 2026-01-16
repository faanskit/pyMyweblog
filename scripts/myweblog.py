import os
import sys
import argparse
import asyncio
from dotenv import load_dotenv
from pyMyweblog.client import MyWebLogClient
from pprint import pprint

try:
    import questionary
except ImportError:
    print(
        (
            "questionary is required for interactive menus. "
            "Install with: pip install questionary"
        )
    )
    sys.exit(1)

# Load environment variables from .env
load_dotenv()

USERNAME = os.getenv("MYWEBLOG_USERNAME")
PASSWORD = os.getenv("MYWEBLOG_PASSWORD")
APP_SECRET = os.getenv("APP_SECRET")

AVAILABLE_OPERATIONS = [
    ("GetObjects", "getObjects", "-o"),
    ("GetBookings", "getBookings", "-b"),
    ("GetBalance", "getBalance", "-c"),
    ("GetTransactions", "getTransactions", "-t"),
    ("GetFlightLog", "getFlightLog", "-f"),
    ("GetFlightLogReversed", "getFlightLogReversed", "-r"),
]


def select_airplane_sync(airplanes):
    import questionary

    choices = [f"{a['regnr']} ({a['model']})" for a in airplanes]
    answer = questionary.select(
        "Select airplane to fetch bookings for:", choices=choices
    ).ask()
    if not answer:
        print("Goodbye!")
        return None
    selected_idx = choices.index(answer)
    return airplanes[selected_idx]["ID"], airplanes[selected_idx]["regnr"]


async def run_operation(client, op: str):
    if op == "getObjects":
        result = await client.getObjects()
        print(f"Result for {op}:")
        pprint(result)
        return
    elif op == "getBookings":
        # Fetch objects and filter for airplanes (async)
        objects_result = await client.getObjects()
        airplanes = [
            obj
            for obj in objects_result.get("Object", [])
            if obj.get("regnr")
            and obj.get("model")
            and not obj.get("model", "").lower().startswith("x")
        ]
        if not airplanes:
            print("No airplanes found for bookings.")
            return
        # Prompt user to select an airplane (sync)
        import asyncio

        selection = await asyncio.to_thread(select_airplane_sync, airplanes)
        if not selection:
            return
        airplane_id, regnr = selection
        result = await client.getBookings(airplane_id)
        print(f"Result for {op} ({regnr}):")
        pprint(result)
        return
    elif op == "getBalance":
        result = await client.getBalance()
        print(f"Result for {op}:")
        pprint(result)
        return
    elif op == "getTransactions":
        # Get transactions with default limit of 20, can be enhanced with date filters
        result = await client.getTransactions(limit=20)
        print(f"Result for {op}:")
        pprint(result)
        return
    elif op == "getFlightLog":
        # Get flight log with default limit of 20, can be enhanced with date filters
        result = await client.getFlightLog(limit=20)
        print(f"Result for {op}:")
        pprint(result)
        return
    elif op == "getFlightLogReversed":
        # Get reversed flight log with default limit of 20
        result = await client.getFlightLogReversed(limit=20)
        print(f"Result for {op}:")
        pprint(result)
        return
    else:
        print(f"Unknown operation: {op}")
        return
    print(f"Result for {op}:")
    pprint(result, indent=2)


async def main(selected_ops):
    if not USERNAME or not PASSWORD or not APP_SECRET:
        print(
            (
                "Missing required environment variables: "
                "MYWEBLOG_USERNAME, MYWEBLOG_PASSWORD, APP_SECRET"
            )
        )
        sys.exit(1)

    async with MyWebLogClient(USERNAME, PASSWORD, app_token=None) as client:
        await client.obtainAppToken(APP_SECRET)
        for op in selected_ops:
            await run_operation(client, op)


if __name__ == "__main__":

    class SingleLineHelpFormatter(argparse.HelpFormatter):
        def _format_action(self, action):
            # Format options and help string on a single line
            parts = []
            if action.option_strings:
                opts = ", ".join(action.option_strings)
                help_str = self._expand_help(action)
                # Pad so all help text starts at the same column
                pad = " " * (30 - len(opts)) if len(opts) < 30 else "  "
                parts.append(f"  {opts}{pad}{help_str}\n")
            else:
                parts.append(f"  {action.dest}\n")
            return "".join(parts)

    parser = argparse.ArgumentParser(
        description="MyWebLog API Utility",
        formatter_class=SingleLineHelpFormatter,
        add_help=True,
    )
    for op_name, op_func, short_code in AVAILABLE_OPERATIONS:
        parser.add_argument(
            short_code,
            f"--{op_func.lower()}",
            action="store_true",
            help=f"Run {op_name}",
        )
    args = parser.parse_args()
    selected_ops = [
        op_func
        for op_name, op_func, short_code in AVAILABLE_OPERATIONS
        if getattr(args, op_func.lower())
    ]

    # If no CLI arguments, show interactive menu (outside async)
    if not selected_ops:
        # Show only operation names in the menu
        menu_choices = [op_name for op_name, _, _ in AVAILABLE_OPERATIONS]
        answer = questionary.checkbox(
            "Select one or more operations to run:", choices=menu_choices
        ).ask()
        if not answer:
            print("Goodbye!")
            sys.exit(0)
        # Map menu selection back to function names
        selected_ops = [
            AVAILABLE_OPERATIONS[menu_choices.index(sel)][1] for sel in answer
        ]

    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main(selected_ops))
