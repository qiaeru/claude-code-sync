# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Changed

- Import verifies all SHA-256 checksums before writing anything, so a corrupted archive can no longer leave a half-restored tree behind; an entry listed in the manifest but missing from the ZIP now also aborts the import instead of being reported as restored.
- Exports are written atomically (temporary `.part` file renamed into place, unique per process), so an interrupted or concurrent export never leaves a truncated ZIP behind.
- Exports hash and compress each file in a single read, halving export I/O and removing the window where a file modified mid-export produced an archive that failed checksum verification on import.
- On Windows, import backups prefix the drive letter (`C/Users/...`) so identical paths on different drives cannot collide inside a backup.

### Fixed

- Restored files keep their permissions, so executable hook scripts no longer lose their executable bit on the target machine.
- The overwrite-vs-create decision (and thus the pre-overwrite backup) is re-checked at write time, so a destination file that appeared or vanished after the preview is still handled safely.
- A failed or backup-free import no longer leaves an empty timestamped backup directory behind, and rapid successive imports get distinct backup directories.
- Handing the CLI a file that is not a ZIP, or an archive from a newer format version, prints a clean error instead of a traceback.
- Web UI: pressing Enter in a preview's filter box (or on a row checkbox) no longer triggers the export/restore action.
- Web UI: a preview is hidden as soon as the root, scope or archive it was computed from changes, so a stale file selection can no longer be applied to different inputs.
- Web UI: dropping a file outside the dropzone no longer navigates the page away (and loses the typed passwords).
- The local server answers a malformed `Content-Length` header with a clean HTTP 400 instead of resetting the connection.
- Drag-and-dropped archive names are percent-decoded, so files with spaces or accents keep their original name.
- CLI runs no longer create an empty upload temp directory.

### Security

- Symlinked project directories, project `.claude/` directories and global include directories are excluded from the scan, as documented; previously only symlinked *sub*directories were excluded, so a symlinked scan root could export files from outside the scanned tree.
- The local server rejects DNS-rebinding requests on GET endpoints too (`Host` must be local), and responses carry `X-Content-Type-Options: nosniff` plus `Cache-Control: no-store` on the API.

## [1.1.0] - 2026-06-06

### Added

- `scripts/`: companion shell and batch helpers — `update-repos` (fast-forward every Git repo), `status-repos` (read-only repo status), `clean-backups` (prune import backups), and `backup-export` (unattended encrypted export with retention).
- **Backups** tab in the web UI (and `backups` core module) to list and prune the import backups under `~/.claude-code-sync-backups/`, with new endpoints `GET /api/backups` and `POST /api/backups/prune`.
- Export retention: an optional **Keep newest archives** field in the UI and `--keep N` on the CLI delete older `claude-code-sync-*.zip` in the output folder after a successful export. `POST /api/export` accepts `keep` and reports `pruned`.

### Fixed

- `run.sh` / `run.bat` report a clear error when neither `python3`/`py` nor `python` is on `PATH`, and `exec` the interpreter so Ctrl-C reaches it directly.

## [1.0.0] - 2026-05-30

- Initial release.

[Unreleased]: https://github.com/qiaeru/claude-code-sync/compare/v1.1.0...HEAD
[1.1.0]: https://github.com/qiaeru/claude-code-sync/compare/v1.0.0...v1.1.0
[1.0.0]: https://github.com/qiaeru/claude-code-sync/releases/tag/v1.0.0
