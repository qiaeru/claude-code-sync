"""Entry point: launch the web UI, or run headless ``export`` / ``import``.

Run with ``python -m claude_code_sync`` or the installed ``claude-code-sync``
command. With no subcommand it starts the local web UI; ``export``, ``import``,
``inspect``, ``verify`` and ``backups`` run the same core logic without a
browser, for scripting and cron.
"""

from __future__ import annotations

import argparse
import getpass
import os
import sys
import threading
import webbrowser
from pathlib import Path

from . import __version__, archive, backups, config, importer, manifest, scanner, server

#: Failures a user can plausibly trigger with bad input (not-a-ZIP files,
#: archives from a newer format version via ValueError, which also covers JSON
#: errors, or a missing manifest via FileNotFoundError), reported as one-line
#: errors instead of tracebacks. ``archive.BadZipFile`` is pyzipper's own class,
#: not the stdlib's -- the stdlib one would never match.
_IMPORT_ERRORS = (
    archive.BadPassword,
    archive.ArchiveTooLarge,
    importer.IntegrityError,
    archive.BadZipFile,
    FileNotFoundError,
    ValueError,
)

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
    parser.add_argument(
        "--host",
        default="127.0.0.1",
        help="Bind host; loopback only: 127.0.0.1, localhost, or ::1 (default: 127.0.0.1).",
    )
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
    exp.add_argument(
        "--keep",
        type=int,
        default=None,
        metavar="N",
        help="After exporting, keep only the newest N archives in the output folder.",
    )

    imp = sub.add_parser("import", help="Restore an archive (no browser).")
    imp.add_argument("archive", help="Path to the .zip archive.")
    imp.add_argument("--root", default=None, help="Target root folder (default: auto).")
    imp.add_argument("--scope", choices=config.VALID_SCOPES, default=config.SCOPE_ALL)
    imp.add_argument("--dry-run", action="store_true", help="Preview without writing.")
    imp.add_argument("--yes", action="store_true", help="Skip the overwrite confirmation.")

    ins = sub.add_parser("inspect", help="Show an archive's manifest without restoring it.")
    ins.add_argument("archive", help="Path to the .zip archive.")

    ver = sub.add_parser("verify", help="Check an archive's checksums without restoring it.")
    ver.add_argument("archive", help="Path to the .zip archive.")

    bak = sub.add_parser("backups", help="List or prune the import backups.")
    bsub = bak.add_subparsers(dest="backups_command", required=True)
    bsub.add_parser("list", help="List the import backups, newest first.")
    bp = bsub.add_parser("prune", help="Keep the newest N backups, delete the rest.")
    bp.add_argument(
        "--keep",
        type=int,
        required=True,
        metavar="N",
        help="Number of newest backups to keep (0 removes them all).",
    )
    bp.add_argument("--dry-run", action="store_true", help="Preview without deleting.")

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
    try:
        man = archive.create(entries, out_path, password, args.scope)
    except OSError as exc:
        print(f"Could not write archive: {exc}", file=sys.stderr)
        return 1
    print(
        f"Created {out_path} ({man['entry_count']} files, {manifest.total_size(man)} bytes)."
    )

    if args.keep is not None and args.keep >= 1:
        removed = archive.prune_archives(out_path.parent, args.keep)
        if removed:
            print(f"Pruned {len(removed)} older archive(s), kept the newest {args.keep}.")
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
    except _IMPORT_ERRORS as exc:
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
    except _IMPORT_ERRORS as exc:
        print(str(exc), file=sys.stderr)
        return 1

    msg = f"Restored: {result.created} created, {result.overwritten} overwritten."
    if result.backup_dir:
        msg += f" Backup: {result.backup_dir}"
    print(msg)
    return 0


def _cli_inspect(args: argparse.Namespace) -> int:
    zip_path = Path(args.archive)
    if not zip_path.is_file():
        print(f"Archive not found: {zip_path}", file=sys.stderr)
        return 1
    password = _get_password(confirm=False)

    try:
        man = archive.read_manifest(zip_path, password)
    except _IMPORT_ERRORS as exc:
        print(str(exc), file=sys.stderr)
        return 1

    entries = man.get("entries", [])
    print(f"Archive: {zip_path}")
    print(f"Created: {man.get('created_at', '?')} on {man.get('hostname', '?')}")
    print(f"Scope:   {man.get('scope', '?')}")
    print(f"Entries: {len(entries)}")
    for entry in entries:
        print(f"  {entry.get('size', 0):>10}  {entry['arcname']}")
    return 0


def _cli_verify(args: argparse.Namespace) -> int:
    zip_path = Path(args.archive)
    if not zip_path.is_file():
        print(f"Archive not found: {zip_path}", file=sys.stderr)
        return 1
    password = _get_password(confirm=False)

    try:
        checked, problems = archive.verify(zip_path, password)
    except _IMPORT_ERRORS as exc:
        print(str(exc), file=sys.stderr)
        return 1

    if problems:
        for problem in problems:
            print(problem, file=sys.stderr)
        print(f"FAILED: {len(problems)} problem(s) in {zip_path}.", file=sys.stderr)
        return 1
    print(f"OK: {checked} file(s) verified in {zip_path}.")
    return 0


def _cli_backups_list() -> int:
    infos = backups.list_backups()
    if not infos:
        print(f"No backups under {config.backup_root()}.")
        return 0
    print(f"{len(infos)} backup(s) under {config.backup_root()} (newest first):")
    for b in infos:
        print(f"  {b.name}  {b.files} file(s), {b.size} bytes")
    return 0


def _cli_backups_prune(args: argparse.Namespace) -> int:
    if args.keep < 0:
        print("--keep must be >= 0.", file=sys.stderr)
        return 2
    result = backups.prune_backups(args.keep, dry_run=args.dry_run)
    verb = "Would remove" if result.dry_run else "Removed"
    print(
        f"{verb} {len(result.removed)} backup(s), kept {len(result.kept)}, "
        f"freeing {result.freed} bytes."
    )
    for b in result.removed:
        print(f"  {b.name}")
    return 0


def _serve(args: argparse.Namespace) -> int:
    # A non-loopback bind would start a server that 403s every request anyway
    # (the API rejects non-local Host headers by design), so fail fast instead.
    if args.host not in server.LOOPBACK_HOSTS:
        print(
            f"--host must be a loopback address ({', '.join(sorted(server.LOOPBACK_HOSTS))}); "
            "the API rejects non-local requests by design. "
            "For remote access, use an SSH tunnel (ssh -L).",
            file=sys.stderr,
        )
        return 2

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
    if args.command == "inspect":
        return _cli_inspect(args)
    if args.command == "verify":
        return _cli_verify(args)
    if args.command == "backups":
        if args.backups_command == "list":
            return _cli_backups_list()
        return _cli_backups_prune(args)
    return _serve(args)


if __name__ == "__main__":
    sys.exit(main())
