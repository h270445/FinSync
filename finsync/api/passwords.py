"""Set a member's web app password: ``python -m finsync.api.passwords set --user <member> [--email <address>]``.

Until the settings screen exists, this is how a member gets a password for the web app. The member
must already belong to a group (``python -m finsync.api.tokens create`` adds the membership). Only
a salted scrypt hash is stored; setting a new password ends the member's open web sessions.
"""

from __future__ import annotations

import argparse
import getpass
import sys

from finsync.core import SessionService
from finsync.core.sessions import MAX_PASSWORD_LENGTH, MIN_PASSWORD_LENGTH
from finsync.storage import FinSyncStorage


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m finsync.api.passwords", description="Manage FinSync web app passwords."
    )
    parser.add_argument("--db", default="finsync.db", help="SQLite database file (default: finsync.db)")
    commands = parser.add_subparsers(dest="command", required=True)
    set_password = commands.add_parser("set", help="Set or replace a member's password")
    set_password.add_argument("--user", required=True)
    set_password.add_argument("--email", help="also set the e-mail address the member can sign in with")
    set_password.add_argument(
        "--password-stdin", action="store_true", help="read the password from the first line of standard input"
    )
    args = parser.parse_args(argv)

    if args.password_stdin:
        password = sys.stdin.readline().rstrip("\r\n")
    else:
        password = getpass.getpass("New password: ")
        if getpass.getpass("Repeat it: ") != password:
            print("error: the two passwords differ", file=sys.stderr)
            return 2
    if not MIN_PASSWORD_LENGTH <= len(password) <= MAX_PASSWORD_LENGTH:
        print(f"error: the password must be {MIN_PASSWORD_LENGTH} to {MAX_PASSWORD_LENGTH} characters long", file=sys.stderr)
        return 2
    sessions = SessionService(FinSyncStorage(args.db))
    try:
        # The password is checked above and the e-mail goes first, so a refused command changes nothing.
        email = sessions.set_email(args.user, args.email) if args.email is not None else None
        sessions.set_password(args.user, password)
    except ValueError as error:
        print(f"error: {error}", file=sys.stderr)
        return 2
    print(f"Password set for {args.user.strip()}; their open web sessions have ended.")
    if email:
        print(f"They can sign in with {email} or {args.user.strip()}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
