# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [1.4.0] - 2026-07-05

### Added

- `inspect` CLI subcommand: print an archive's manifest (creation date, source machine, scope, file list) without restoring it.
- `verify` CLI subcommand: check every member against the SHA-256 recorded in the manifest, without restoring anything, so scheduled backups can be tested (password and integrity) periodically.
- `backups` CLI subcommands (`backups list`, `backups prune --keep N [--dry-run]`) to review and clean up the import backups, mirroring the web UI's Backups tab.

### Changed

- `--host` only accepts loopback addresses (`127.0.0.1`, `localhost`, `::1`) and fails fast otherwise, pointing to SSH tunneling for remote access: any other bind would start a server that rejects every request anyway, since the API only answers local Host headers.
- Skipped import entries carry a reason in the plan (outside the requested scope, not selected), and a destination that resolves outside its target folder through a symlink (e.g. a dotfile-managed `~/.claude/settings.json`) now appears as skipped instead of silently vanishing from the preview.
- Drag-and-dropped archives are streamed end to end (the browser sends the file as a Blob, the server spools it to disk in chunks) instead of each side buffering it whole in memory; a truncated upload is rejected and cleaned up rather than left as a partial file.
- An import only decompresses the archive members it will actually restore, instead of the whole archive, when a scope or selection narrows the restore.

### Fixed

- Importing a file that is not a valid ZIP, has no manifest, or uses an unsupported archive format version now returns a clear error in the web UI instead of an "unexpected server error".
- A failed archive write (unwritable output folder, disk full) surfaces as a clear message in the web UI instead of an "unexpected server error".
- The CLI prints a one-line error instead of a traceback when importing or inspecting a non-ZIP file: it caught the standard library's `BadZipFile` while pyzipper raises its own.
- Two simultaneous drag-and-drop uploads can no longer race the creation of the temporary upload directory and leak one of the two copies.
- Export retention no longer errors if an archive disappears between listing and pruning (concurrent prune, antivirus).

### Security

- The web UI is served with a strict `Content-Security-Policy` (`default-src 'self'`); the inline theme snippet moved to `theme-init.js` to make that possible.
- Import refuses a manifest entry that carries no SHA-256 checksum instead of restoring it unverified.

## [1.3.0] - 2026-06-19

### Added

- The web UI shows an attribution footer ("Developed by Qiaeru | Source code on GitHub") linking to qiae.ru and the project repository.

### Changed

- Unified prose on US English across the docs, code comments, and web UI strings (e.g. "canceled", "license").
- Static web UI assets are served with an `ETag` and `Cache-Control: no-cache`, so the browser revalidates and skips re-downloading unchanged files (fonts, logos) while never serving a stale UI after an upgrade.

### Fixed

- The temporary directory holding drag-and-dropped archives is now removed on a clean shutdown (the **Quit** button or Ctrl+C), instead of lingering in the system temp folder.
- Unexpected server errors now log a full traceback to the console for diagnosis, while the browser still receives only a short summary.

## [1.2.0] - 2026-06-12

### Added

- CI also runs on Python 3.14 and macOS, with pip caching; the PyPI classifiers list the supported Python versions.

### Changed

- Import verifies all SHA-256 checksums before writing anything, so a corrupted archive can no longer leave a half-restored tree behind; an entry listed in the manifest but missing from the ZIP also aborts the import.
- Exports are written atomically (temporary `.part` file renamed into place, unique per process), so an interrupted or concurrent export never leaves a truncated ZIP behind.
- Exports hash and compress each file in a single read, halving export I/O; a file modified mid-export can no longer produce an archive that fails checksum verification on import.
- On Windows, import backups prefix the drive letter (`C/Users/...`) so identical paths on different drives cannot collide inside a backup.

### Fixed

- Restored files keep their permissions, so hook scripts no longer lose their executable bit on the target machine.
- The overwrite-vs-create decision (and the pre-overwrite backup) is re-checked at write time, so a destination file that appeared or vanished after the preview is still handled safely.
- A failed or backup-free import no longer leaves an empty backup directory behind, and rapid successive imports get distinct backup directories.
- Handing the CLI a file that is not a ZIP, or an archive from a newer format version, prints a clean error instead of a traceback.
- Web UI: pressing Enter in a preview's filter box no longer triggers the export/restore action.
- Web UI: a preview is hidden as soon as the root, scope, or archive it was computed from changes, so a stale file selection can no longer be applied to different inputs.
- Web UI: dropping a file outside the dropzone no longer navigates the page away (losing the typed passwords).
- The local server answers a malformed `Content-Length` header with a clean HTTP 400 instead of resetting the connection.
- Drag-and-dropped archive names are percent-decoded, so files with spaces or accents keep their original name.
- CLI runs no longer create an empty upload temp directory.
- The PyInstaller spec resolves the web UI assets relative to the spec file, so building from outside the repo root no longer produces a binary without the UI.

### Security

- Symlinked project directories, project `.claude/` directories, and global include directories are excluded from the scan, as documented; previously only symlinked *sub*directories were excluded, so a symlinked scan root could export files from outside the scanned tree.
- The local server rejects DNS-rebinding requests on GET endpoints too (`Host` must be local), and API responses carry `X-Content-Type-Options: nosniff` plus `Cache-Control: no-store`.

## [1.1.0] - 2026-06-06

### Added

- `scripts/`: companion shell and batch helpers: `update-repos` (fast-forward every Git repo), `status-repos` (read-only repo status), `clean-backups` (prune import backups), and `backup-export` (unattended encrypted export with retention).
- **Backups** tab in the web UI (and `backups` core module) to list and prune the import backups under `~/.claude-code-sync-backups/`, with new endpoints `GET /api/backups` and `POST /api/backups/prune`.
- Export retention: an optional **Keep newest archives** field in the UI and `--keep N` on the CLI delete older `claude-code-sync-*.zip` in the output folder after a successful export. `POST /api/export` accepts `keep` and reports `pruned`.

### Fixed

- `run.sh` / `run.bat` report a clear error when neither `python3`/`py` nor `python` is on `PATH`, and `exec` the interpreter so Ctrl-C reaches it directly.

## [1.0.0] - 2026-05-30

- Initial release.

[Unreleased]: https://github.com/qiaeru/claude-code-sync/compare/v1.2.0...HEAD
[1.2.0]: https://github.com/qiaeru/claude-code-sync/compare/v1.1.0...v1.2.0
[1.1.0]: https://github.com/qiaeru/claude-code-sync/compare/v1.0.0...v1.1.0
[1.0.0]: https://github.com/qiaeru/claude-code-sync/releases/tag/v1.0.0
