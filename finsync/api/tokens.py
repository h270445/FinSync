"""Manage API tokens from the command line: ``python -m finsync.api.tokens``.

Until the web app's token screen exists, this is how a member gets a token for the Android app,
the Sheets script or a test client. The token is printed once and only its hash is stored.
"""

from __future__ import annotations

import argparse
import sys

from finsync.core import TokenService
from finsync.storage import FinSyncStorage


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m finsync.api.tokens", description="Manage FinSync API tokens.")
    parser.add_argument("--db", default="finsync.db", help="SQLite database file (default: finsync.db)")
    commands = parser.add_subparsers(dest="command", required=True)

    create = commands.add_parser("create", help="Add the member to the group if needed and issue a token")
    create.add_argument("--user", required=True)
    create.add_argument("--group", required=True)
    create.add_argument("--name", required=True, help='What the token is for, e.g. "Anna phone"')

    listing = commands.add_parser("list", help="List tokens (never the token itself)")
    listing.add_argument("--user")

    revoke = commands.add_parser("revoke", help="Revoke a token by id")
    revoke.add_argument("token_id", type=int)

    args = parser.parse_args(argv)
    storage = FinSyncStorage(args.db)
    tokens = TokenService(storage)

    if args.command == "create":
        # Validate everything before touching membership, so a rejected command changes nothing.
        if not args.user.strip() or not args.group.strip() or not args.name.strip():
            print("error: user, group and name are required", file=sys.stderr)
            return 2
        storage.add_group_membership(args.user.strip(), args.group.strip())
        try:
            token, record = tokens.create(args.user, args.group, args.name)
        except ValueError as error:
            print(f"error: {error}", file=sys.stderr)
            return 2
        print(f"Token {record.id} for {record.user_id} in {record.group_id} ({record.name}):")
        print(token)
        print("Store it now; it is not shown again.", file=sys.stderr)
        return 0

    if args.command == "list":
        for record in tokens.list(args.user):
            state = f"revoked {record.revoked_at:%Y-%m-%d}" if record.revoked_at else "active"
            last_used = f"{record.last_used_at:%Y-%m-%d %H:%M}" if record.last_used_at else "never"
            print(
                f"{record.id}\t{record.user_id}\t{record.group_id}\t{record.name}\t{record.prefix}…"
                f"\tcreated {record.created_at:%Y-%m-%d}\tlast used {last_used}\t{state}"
            )
        return 0

    if tokens.revoke(args.token_id):
        print(f"Token {args.token_id} revoked.")
        return 0
    print(f"error: no active token with id {args.token_id}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
