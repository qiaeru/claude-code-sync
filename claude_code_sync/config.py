"""Constants describing what to collect, what to skip, and where things live.

Security note: for the global ``~/.claude`` directory we use an *allow list*
(:data:`GLOBAL_INCLUDE`) rather than a deny list. This guarantees that secrets
such as ``.credentials.json`` are never added to an archive by accident, even if
Claude Code introduces new files in the future.
"""

from __future__ import annotations

import socket
from dataclasses import dataclass, replace
from datetime import datetime
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Project scope (each direct sub-directory of the chosen root)
# ---------------------------------------------------------------------------

#: File looked up at the project root and recursively in sub-directories.
PROJECT_MEMORY_FILE = "CLAUDE.md"

#: Per-project config directory copied wholesale (minus PROJECT_CLAUDE_EXCLUDE).
PROJECT_CLAUDE_DIR = ".claude"

#: Entries inside a project ``.claude/`` that must never be exported
#: (machine-specific or potentially secret).
PROJECT_CLAUDE_EXCLUDE = frozenset(
    {
        "settings.local.json",
        ".credentials.json",
    }
)

#: Directory names pruned while walking a project tree. They are noisy, huge,
#: and never contain Claude Code configuration.
PRUNE_DIRS = frozenset(
    {
        ".git",
        "node_modules",
        ".venv",
        "venv",
        "__pycache__",
        "dist",
        "build",
        "vendor",
        "target",
        ".next",
        ".cache",
        ".idea",
        ".tox",
        ".mypy_cache",
        ".pytest_cache",
        ".ruff_cache",
    }
)

# ---------------------------------------------------------------------------
# Global scope (~/.claude)
# ---------------------------------------------------------------------------

#: Global config directory, relative to the user's home.
GLOBAL_DIR_NAME = ".claude"

#: Top-level files inside ~/.claude that are exported when present.
GLOBAL_INCLUDE_FILES = (
    "settings.json",
    "keybindings.json",
    "CLAUDE.md",
)

#: Top-level directories inside ~/.claude that are exported when present.
GLOBAL_INCLUDE_DIRS = (
    "skills",
    "agents",
    "commands",
    "hooks",
    "plugins",
)

#: Combined allow list used by the scanner for the global scope.
GLOBAL_INCLUDE = GLOBAL_INCLUDE_FILES + GLOBAL_INCLUDE_DIRS

#: File/dir names that must never be exported even from an allowed directory.
SECRET_NAMES = frozenset(
    {
        ".credentials.json",
        "credentials.json",
        ".env",
    }
)

# ---------------------------------------------------------------------------
# Archive layout
# ---------------------------------------------------------------------------

ARCHIVE_MANIFEST = "manifest.json"
ARCHIVE_GLOBAL_PREFIX = "global"
ARCHIVE_PROJECTS_PREFIX = "projects"

#: Archive format version, bumped when the on-disk layout changes.
ARCHIVE_VERSION = 1

# ---------------------------------------------------------------------------
# Scope selection
# ---------------------------------------------------------------------------

SCOPE_PROJECTS = "projects"
SCOPE_GLOBAL = "global"
SCOPE_ALL = "all"
VALID_SCOPES = (SCOPE_ALL, SCOPE_PROJECTS, SCOPE_GLOBAL)


def default_root() -> Path:
    """Return the default root to scan: the parent of this tool's directory.

    The tool lives inside the projects folder (e.g. ``GitHub/claude-code-sync``),
    so its parent (``GitHub/``) is the directory holding the sibling projects.
    """
    return Path(__file__).resolve().parent.parent.parent


def tool_dir_name() -> str:
    """Name of this tool's own directory, excluded from project scans."""
    return Path(__file__).resolve().parent.parent.name


def global_claude_dir() -> Path:
    """Absolute path to the user's global ``~/.claude`` directory."""
    return Path.home() / GLOBAL_DIR_NAME


#: Directory under the user's home where an import backs up files it overwrites.
BACKUP_DIR_NAME = ".claude-code-sync-backups"


def backup_root() -> Path:
    """Absolute path to the import-backups directory (``~/.claude-code-sync-backups``)."""
    return Path.home() / BACKUP_DIR_NAME


def is_secret(name: str) -> bool:
    """True if *name* is a known secret that must never be exported."""
    return name in SECRET_NAMES


#: Glob matching archives produced by :func:`archive_filename`, used for retention.
ARCHIVE_GLOB = "claude-code-sync-*.zip"


def archive_filename(host: str | None = None, when: datetime | None = None) -> str:
    """Default archive name: ``claude-code-sync-<host>-<YYYYMMDD-HHMMSS>.zip``."""
    host = host or socket.gethostname()
    stamp = (when or datetime.now()).strftime("%Y%m%d-%H%M%S")
    return f"claude-code-sync-{host}-{stamp}.zip"


# ---------------------------------------------------------------------------
# Optional per-root configuration file (.claude-code-sync.toml)
# ---------------------------------------------------------------------------

#: Optional TOML config file looked up in the scanned root directory.
CONFIG_FILENAME = ".claude-code-sync.toml"


@dataclass(frozen=True)
class ScanConfig:
    """Effective inclusion/exclusion settings for a scan.

    Built from the module defaults and optionally extended by a
    ``.claude-code-sync.toml`` file in the scanned root. All overrides are
    **additive** (they extend the defaults); secret/exclusion lists can never be
    shrunk via the config file, which keeps the safety guarantees intact.
    """

    memory_file: str
    claude_dir: str
    project_claude_exclude: frozenset[str]
    prune_dirs: frozenset[str]
    global_include_files: tuple[str, ...]
    global_include_dirs: tuple[str, ...]
    secret_names: frozenset[str]
    follow_symlinks: bool = False

    @classmethod
    def default(cls) -> ScanConfig:
        return cls(
            memory_file=PROJECT_MEMORY_FILE,
            claude_dir=PROJECT_CLAUDE_DIR,
            project_claude_exclude=PROJECT_CLAUDE_EXCLUDE,
            prune_dirs=PRUNE_DIRS,
            global_include_files=GLOBAL_INCLUDE_FILES,
            global_include_dirs=GLOBAL_INCLUDE_DIRS,
            secret_names=SECRET_NAMES,
            follow_symlinks=False,
        )

    @classmethod
    def load(cls, root: Path | None) -> ScanConfig:
        """Load defaults, merged with ``root/.claude-code-sync.toml`` if present."""
        cfg = cls.default()
        if root is None:
            return cfg
        path = Path(root) / CONFIG_FILENAME
        if not path.is_file():
            return cfg
        return cfg._merged(_read_toml(path))

    def _merged(self, data: dict[str, Any]) -> ScanConfig:
        scan = data.get("scan", {})
        proj = data.get("project", {})
        glob = data.get("global", {})
        secrets = data.get("secrets", {})

        def extend(base: tuple[str, ...], extra: Any) -> tuple[str, ...]:
            return tuple(dict.fromkeys(base + tuple(extra or ())))

        return ScanConfig(
            memory_file=self.memory_file,
            claude_dir=self.claude_dir,
            project_claude_exclude=self.project_claude_exclude | set(proj.get("exclude", []) or []),
            prune_dirs=self.prune_dirs | set(scan.get("prune_dirs", []) or []),
            global_include_files=extend(self.global_include_files, glob.get("include_files")),
            global_include_dirs=extend(self.global_include_dirs, glob.get("include_dirs")),
            secret_names=self.secret_names | set(secrets.get("names", []) or []),
            follow_symlinks=bool(scan.get("follow_symlinks", self.follow_symlinks)),
        )

    def is_secret(self, name: str) -> bool:
        return name in self.secret_names

    def with_pruned(self, *names: str) -> ScanConfig:
        """Return a copy with *names* added to the pruned-directory set."""
        return replace(self, prune_dirs=self.prune_dirs | frozenset(names))


def _read_toml(path: Path) -> dict[str, Any]:
    import tomllib  # stdlib on Python 3.11+

    with open(path, "rb") as fh:
        return tomllib.load(fh)
