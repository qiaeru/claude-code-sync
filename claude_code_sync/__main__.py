"""Entry point: launch the web UI, or run headless ``export`` / ``import``.

Run with ``python -m claude_code_sync`` or the installed ``claude-code-sync``
command. With no subcommand it starts the local web UI; ``export`` and
``import`` run the same core logic without a browser, for scripting and cron.
"""

from __future__ import annotations

import argparse
import getpass
import os
import sys
import threading
import webbrowser
from pathlib import Path

from . import __version__, archive, config, importer, scanner, server

#: Environment variable used to pass the archive password non-interactively.
PASSWORD_ENV = "CLAUDE_CODE_SYNC_PASSWORD"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="claude-code-sync",
        description=(
            "A small tool that syncs your Claude Code configuration "
            "across machines, offline and encrypted."
        ),
    )
    parser.add_argument("--host", default="127.0.0.1", help="Bind host (default: 127.0.0.1).")
    parser.add_argument(
        "--port", type=int, default=0, help="Bind port (default: 0 = pick a free port)."
    )
    parser.add_argument(
        "--no-browser", action="store_true", help="Do not open a browser automatically."
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")

    sub = parser.add_subparsers(dest="command")

    exp = sub.add_parser("export", help="Create an encrypted archive (no browser).")
    exp.add_argument("--root", default=None, help="Root folder to scan (default: auto).")
    exp.add_argument("--scope", choices=config.VALID_SCOPES, default=config.SCOPE_ALL)
    exp.add_argument("--out-dir", default=None, help="Folder to write the archive into.")
    exp.add_argument("--out", default=None, help="Exact output archive path (overrides --out-dir).")

    imp = sub.add_parser("import", help="Restore an archive (no browser).")
    imp.add_argument("archive", help="Path to the .zip archive.")
    imp.add_argument("--root", default=None, help="Target root folder (default: auto).")
    imp.add_argument("--scope", choices=config.VALID_SCOPES, default=config.SCOPE_ALL)
    imp.add_argument("--dry-run", action="store_true", help="Preview without writing.")
    imp.add_argument("--yes", action="store_true", help="Skip the overwrite confirmation.")

    return parser


def _get_password(confirm: bool) -> str:
    env = os.environ.get(PASSWORD_ENV)
    if env:
        return env
    pw = getpass.getpass("Password: ")
    if not pw:
        print("A password is required.", file=sys.stderr)
        raise SystemExit(2)
    if confirm and pw != getpass.getpass("Confirm password: "):
        print("Passwords do not match.", file=sys.stderr)
        raise SystemExit(2)
    return pw


def _cli_export(args: argparse.Namespace) -> int:
    root = Path(args.root).resolve() if args.root else config.default_root()
    if not root.is_dir():
        print(f"Root directory does not exist: {root}", file=sys.stderr)
        return 1

    entries = scanner.scan(root, args.scope)
    if not entries:
        print("Nothing to export: no Claude Code configuration found.", file=sys.stderr)
        return 1

    if args.out:
        out_path = Path(args.out)
    else:
        out_dir = Path(args.out_dir) if args.out_dir else root
        out_path = out_dir / config.archive_filename()

    password = _get_password(confirm=True)
    archive.create(entries, out_path, password, args.scope)
    print(f"Created {out_path} ({len(entries)} files, {scanner.total_size(entries)} bytes).")
    return 0


def _cli_import(args: argparse.Namespace) -> int:
    zip_path = Path(args.archive)
    if not zip_path.is_file():
        print(f"Archive not found: {zip_path}", file=sys.stderr)
        return 1
    root = Path(args.root).resolve() if args.root else config.default_root()
    password = _get_password(confirm=False)

    try:
        plan = importer.run_import(
            zip_path, password, root, scope=args.scope, dry_run=True
        )
    except archive.BadPassword as exc:
        print(str(exc), file=sys.stderr)
        return 1

    print(
        f"Plan: {plan.created} to create, {plan.overwritten} to overwrite, "
        f"{plan.skipped} skipped."
    )
    if args.dry_run:
        return 0
    if plan.created + plan.overwritten == 0:
        print("Nothing to restore for this scope.")
        return 0

    if not args.yes and plan.overwritten:
        reply = input(f"Overwrite {plan.overwritten} existing file(s) (backed up first)? [y/N] ")
        if reply.strip().lower() not in ("y", "yes"):
            print("Aborted.")
            return 0

    try:
        result = importer.run_import(zip_path, password, root, scope=args.scope)
    except (archive.BadPassword, archive.ArchiveTooLarge, importer.IntegrityError) as exc:
        print(str(exc), file=sys.stderr)
        return 1

    msg = f"Restored: {result.created} created, {result.overwritten} overwritten."
    if result.backup_dir:
        msg += f" Backup: {result.backup_dir}"
    print(msg)
    return 0


def _serve(args: argparse.Namespace) -> int:
    httpd = server.create_server(args.host, args.port)
    host, port = str(httpd.server_address[0]), httpd.server_address[1]
    url = f"http://{host}:{port}/"

    print(f"claude-code-sync {__version__}")
    print(f"Serving the web UI at {url}")
    print("Close the browser tab and press Ctrl+C here to stop (or use Quit in the UI).")

    if not args.no_browser:
        threading.Timer(0.4, lambda: webbrowser.open(url)).start()

    try:
        server.serve_forever(httpd)
    except KeyboardInterrupt:
        print("\nShutting down.")
        httpd.shutdown()
    return 0


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "export":
        return _cli_export(args)
    if args.command == "import":
        return _cli_import(args)
    return _serve(args)


if __name__ == "__main__":
    sys.exit(main())
