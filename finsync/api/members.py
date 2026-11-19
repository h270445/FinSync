"""Manage group members from the command line: ``python -m finsync.api.members``.

The web app shows the members and lets an admin change roles; adding a member, and fixing a group
whose admins are all gone, is done here. Roles: ``admin`` changes the group's settings, ``member``
does not (Alembic revision 0003).
"""

from __future__ import annotations

import argparse
import sys

from finsync.storage import ROLES, FinSyncStorage


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m finsync.api.members", description="Manage FinSync group members.")
    parser.add_argument("--db", default="finsync.db", help="SQLite database file or database URL (default: finsync.db)")
    commands = parser.add_subparsers(dest="command", required=True)

    add = commands.add_parser("add", help="Add a member (the first member of a new group becomes its admin)")
    add.add_argument("--user", required=True)
    add.add_argument("--group", required=True)
    add.add_argument("--role", choices=ROLES, help="default: admin for a new group, member otherwise")

    listing = commands.add_parser("list", help="List a group's members and roles")
    listing.add_argument("--group", required=True)

    set_role = commands.add_parser("set-role", help="Change a member's role")
    set_role.add_argument("--user", required=True)
    set_role.add_argument("--group", required=True)
    set_role.add_argument("--role", required=True, choices=ROLES)

    args = parser.parse_args(argv)
    storage = FinSyncStorage(args.db)

    if args.command == "add":
        user, group = args.user.strip(), args.group.strip()
        if not user or not group:
            print("error: user and group are required", file=sys.stderr)
            return 2
        storage.add_group_membership(user, group, args.role)
        print(f"{user} is {storage.member_role(user, group)} in {group}.")
        return 0

    if args.command == "list":
        for user, email, role in storage.list_group_members(args.group):
            print(f"{user}\t{role}\t{email or '-'}")
        return 0

    try:
        changed = storage.set_member_role(args.user, args.group, args.role)
    except ValueError as error:
        print(f"error: {error}", file=sys.stderr)
        return 2
    if not changed:
        print(f"error: {args.user} is not a member of {args.group}", file=sys.stderr)
        return 1
    print(f"{args.user} is now {args.role} in {args.group}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
