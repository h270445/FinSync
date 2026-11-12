"""Entry point for ``python -m finsync.api``."""

import argparse
import json

from finsync.api.server import run_server

parser = argparse.ArgumentParser(prog="python -m finsync.api", description="Run the FinSync API.")
parser.add_argument("--host", default="127.0.0.1")
parser.add_argument("--port", type=int, default=8080)
parser.add_argument("--db", default="finsync.db", help="SQLite database file or database URL, e.g. postgresql+psycopg://user:password@host/finsync (default: finsync.db)")
parser.add_argument("--openapi", action="store_true", help="print the OpenAPI schema and exit")
args = parser.parse_args()
if args.openapi:
    import tempfile

    from finsync.api.server import create_app
    from finsync.storage import FinSyncStorage

    with tempfile.TemporaryDirectory() as tempdir:
        print(json.dumps(create_app(FinSyncStorage(f"{tempdir}/schema.db")).openapi(), indent=2))
else:
    run_server(args.host, args.port, args.db)
