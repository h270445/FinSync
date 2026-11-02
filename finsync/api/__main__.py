"""Entry point for ``python -m finsync.api``."""

import argparse

from finsync.api.server import run_server

parser = argparse.ArgumentParser(prog="python -m finsync.api", description="Run the FinSync API.")
parser.add_argument("--host", default="127.0.0.1")
parser.add_argument("--port", type=int, default=8080)
parser.add_argument("--db", default="finsync.db", help="SQLite database file (default: finsync.db)")
args = parser.parse_args()
run_server(args.host, args.port, args.db)
