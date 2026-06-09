# Security

Claude Code Sync is built to move sensitive configuration between machines without an online service. This page describes what protects your data and the limits you should know about.

## Encryption

- Archives are standard **WinZip-AES (AES-256)** ZIPs, interoperable with 7-Zip, WinRAR, and any AES-capable ZIP tool using the same password.
- **Choose a strong passphrase.** WinZip-AES derives its key with PBKDF2-HMAC-SHA1 (~1000 iterations). This is interoperable but not hardened against a determined offline brute-force of a weak password. A long, random passphrase is your real protection. Anyone with the archive **and** the password can read your config.
- Passwords are only held in memory and passed straight to the ZIP layer; they are never written to disk or passed as command-line arguments. The CLI reads them from a hidden prompt or the `CLAUDE_CODE_SYNC_PASSWORD` environment variable.

## What is (and is not) archived

The global scope uses an **allow list**, not a deny list: only known-safe files are collected. Secrets such as `~/.claude/.credentials.json`, your chat history, `projects/`, `todos/`, and `settings.local.json` are never archived, and a file added by a future Claude Code version is missed rather than leaked. See [what-is-collected.md](./what-is-collected.md) for the exact rules.

Symlinks are not followed during a scan by default, so a symlinked file inside a scanned tree cannot pull in content from outside it (configurable via `follow_symlinks`).

## Import safety

- **Path-traversal rejection.** Archive entries that try to escape the target folders (`..` segments, absolute paths, drive letters) are rejected, so a malicious or corrupted archive cannot write outside the chosen directories.
- **Integrity verification.** Each entry carries a SHA-256 in `manifest.json`. All checksums are verified against the extracted files *before anything is written*, so a corrupted archive aborts the restore without leaving a half-restored tree behind. (The hash guards against accidental corruption; the authenticated WinZip-AES encryption already blocks tampering by anyone *without* the password.)
- **Bounded extraction.** Members are streamed out with a cap on the total decompressed size (1 GiB by default), counting the bytes actually written rather than the sizes declared in the ZIP, so a decompression bomb cannot exhaust the disk.
- **Backups before overwrite.** Existing files are copied to `~/.claude-code-sync-backups/<timestamp>/` before being replaced, so an import is reversible.

## Local server

- Binds to `127.0.0.1` only and is never exposed to the network.
- Rejects cross-site and DNS-rebinding requests on **every** route (GET and POST): the `Host` header must be present and local and the `Origin` (when sent) must be local, which blocks other websites or processes from driving the API or reading local information from it.
- Serves only the bundled web UI assets; static-file requests are confined to the `webui/` directory.
- Responses carry `X-Content-Type-Options: nosniff`, and API responses are marked `Cache-Control: no-store` so local paths never land in a browser cache.

## Reporting a vulnerability

Please open a private security advisory on GitHub rather than a public issue.
