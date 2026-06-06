# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

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
