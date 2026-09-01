"""Reset the admin console password from the command line.

The escape hatch for a forgotten password. There is deliberately no "email me a
reset link" flow — this project ships without any mail configuration — so the
recovery story is: get a shell on the box that holds the database, run this.

Usage::

    # Prompt for the new password (not echoed) — the normal case
    python -m scripts.reset_admin_password

    # Non-interactive, e.g. from a provisioning script
    python -m scripts.reset_admin_password --username admin --password 's3cret'

    # Forgot the username too? List what accounts exist
    python -m scripts.reset_admin_password --list

Resetting invalidates every existing session for that account: the password
hash is part of what tokens are signed against, so anyone still logged in
elsewhere is signed out at their next request.
"""
from __future__ import annotations

import argparse
import asyncio
import getpass
import sys
from pathlib import Path

# Make `src` importable when running as a script
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from loguru import logger  # noqa: E402
from sqlalchemy import select  # noqa: E402

from src.core.config import get_settings  # noqa: E402
from src.core.database import dispose_engine, session_scope  # noqa: E402
from src.core.security import hash_password  # noqa: E402
from src.models.user import AdminUser  # noqa: E402
from src.services.auth_service import (  # noqa: E402
    MAX_PASSWORD_LEN,
    MIN_PASSWORD_LEN,
)


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        prog="python -m scripts.reset_admin_password",
        description="Reset the admin console password.",
    )
    p.add_argument(
        "--username",
        help="Account to reset. Defaults to the only account when there is just one.",
    )
    p.add_argument(
        "--password",
        help="New password. Omit to be prompted (recommended: keeps it out of shell history).",
    )
    p.add_argument(
        "--list", action="store_true", dest="list_only",
        help="List the accounts in the database and exit.",
    )
    return p.parse_args()


def _read_password() -> str:
    """Prompt twice, so a typo can't lock you out a second time."""
    first = getpass.getpass("New password: ")
    second = getpass.getpass("Confirm password: ")
    if first != second:
        raise SystemExit("❌  The two passwords do not match.")
    return first


async def main() -> int:
    args = _parse_args()
    settings = get_settings()

    async with session_scope() as db:
        result = await db.execute(select(AdminUser).order_by(AdminUser.id))
        users = list(result.scalars().all())

        if not users:
            # The table is seeded on startup, so an empty one means the app has
            # never run against this database.
            print(f"❌  No admin accounts in {settings.database.url}.")
            print("    Start the backend once (it seeds the default account), or run:")
            print("      python -m scripts.init_db")
            return 1

        if args.list_only:
            print(f"Accounts in {settings.database.url}:")
            for u in users:
                state = "active" if u.is_active else "disabled"
                last = u.last_login_at.isoformat(sep=" ", timespec="seconds") if u.last_login_at else "never"
                print(f"  · {u.username}  ({state}, last login: {last})")
            return 0

        if args.username:
            user = next((u for u in users if u.username == args.username), None)
            if user is None:
                names = ", ".join(u.username for u in users)
                print(f"❌  No account named {args.username!r}. Existing accounts: {names}")
                return 1
        elif len(users) == 1:
            user = users[0]
        else:
            names = ", ".join(u.username for u in users)
            print(f"❌  Several accounts exist — pass --username. Existing accounts: {names}")
            return 1

        password = args.password if args.password is not None else _read_password()
        if not (MIN_PASSWORD_LEN <= len(password) <= MAX_PASSWORD_LEN):
            print(f"❌  Password must be {MIN_PASSWORD_LEN}-{MAX_PASSWORD_LEN} characters.")
            return 1

        # Written directly rather than through change_password(): that helper
        # verifies the old password, which is precisely what we don't have.
        user.password_hash = hash_password(password)
        # Re-enable the account while we're here — a disabled one can't log in,
        # and someone running a password reset wants to get back in.
        user.is_active = True
        await db.commit()

    logger.info("✅  Password reset for {}", user.username)
    print(f"✅  Password reset for {user.username!r}. Sign in at /admin/login.html")
    print("    Sessions on other devices have been signed out.")
    return 0


if __name__ == "__main__":
    try:
        code = asyncio.run(main())
    finally:
        asyncio.run(dispose_engine())
    raise SystemExit(code)
