"""Security tests: path-traversal rejection and checksum integrity."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest
import pyzipper

from claude_code_sync import archive, config, importer


def _can_symlink() -> bool:
    """True if this platform/account can create symlinks (Windows often cannot)."""
    with tempfile.TemporaryDirectory() as d:
        link = Path(d) / "link"
        try:
            link.symlink_to(Path(d))
        except (OSError, NotImplementedError):
            return False
        return True


_SYMLINKS_OK = _can_symlink()


def _make_archive(
    path: Path,
    password: str,
    members: dict[str, bytes],
    entries: list[dict],
    format_version: int = config.ARCHIVE_VERSION,
) -> None:
    """Write a hand-crafted encrypted archive with an arbitrary manifest."""
    man = {
        "format_version": format_version,
        "created_at": "2026-01-01T00:00:00+00:00",
        "hostname": "test",
        "platform": "test",
        "scope": "all",
        "entry_count": len(entries),
        "entries": entries,
    }
    with pyzipper.AESZipFile(
        path, "w", compression=pyzipper.ZIP_DEFLATED, encryption=pyzipper.WZ_AES
    ) as zf:
        zf.setpassword(password.encode())
        zf.setencryption(pyzipper.WZ_AES, nbits=256)
        zf.writestr(config.ARCHIVE_MANIFEST, json.dumps(man).encode())
        for arc, content in members.items():
            zf.writestr(arc, content)


def test_import_rejects_path_traversal(tmp_path: Path) -> None:
    zip_path = tmp_path / "evil.zip"
    _make_archive(
        zip_path,
        "pw",
        members={"projects/good.txt": b"ok", "projects/evil.txt": b"bad"},
        entries=[
            {"arcname": "projects/good.txt", "scope": "projects", "size": 2, "sha256": None},
            # Attempts to escape the target root.
            {"arcname": "projects/../../evil.txt", "scope": "projects", "size": 3, "sha256": None},
        ],
    )

    root = tmp_path / "target"
    result = importer.run_import(
        zip_path, "pw", root, home_claude=tmp_path / "home", backup_root=tmp_path / "bk"
    )

    # The safe file is restored; the traversal entry is silently dropped.
    assert (root / "good.txt").read_bytes() == b"ok"
    assert not (tmp_path / "evil.txt").exists()
    assert not (tmp_path.parent / "evil.txt").exists()
    restored = {i.arcname for i in result.items}
    assert "projects/../../evil.txt" not in restored


def test_extract_aborts_on_decompression_bomb(tmp_path: Path) -> None:
    zip_path = tmp_path / "bomb.zip"
    # A highly compressible payload that decompresses well past a tiny budget.
    _make_archive(
        zip_path,
        "pw",
        members={"projects/big.bin": b"\x00" * (1024 * 1024)},
        entries=[
            {"arcname": "projects/big.bin", "scope": "projects", "size": 1, "sha256": None}
        ],
    )

    with pytest.raises(archive.ArchiveTooLarge):
        archive.extract_all(zip_path, tmp_path / "out", "pw", max_total_bytes=4096)


@pytest.mark.skipif(
    not _SYMLINKS_OK, reason="symlink creation not permitted on this platform/account"
)
def test_symlinked_file_is_not_exported(tmp_path: Path) -> None:
    from claude_code_sync import scanner

    root = tmp_path / "GitHub"
    project = root / "proj"
    project.mkdir(parents=True)
    secret = tmp_path / "outside_secret.txt"
    secret.write_text("TOP SECRET\n", encoding="utf-8")
    # A CLAUDE.md that is actually a symlink pointing outside the scanned tree.
    (project / "CLAUDE.md").symlink_to(secret)

    arcs = {e.arcname for e in scanner.scan_projects(root)}
    assert "projects/proj/CLAUDE.md" not in arcs


def test_checksum_mismatch_restores_nothing(tmp_path: Path) -> None:
    """All checksums are verified before any file is written, so one corrupted
    member must not leave a half-restored tree behind."""
    import hashlib

    good = b"good content"
    zip_path = tmp_path / "tampered.zip"
    _make_archive(
        zip_path,
        "pw",
        members={"projects/p/good.md": good, "projects/p/bad.md": b"tampered"},
        entries=[
            {
                "arcname": "projects/p/good.md",
                "scope": "projects",
                "size": len(good),
                "sha256": hashlib.sha256(good).hexdigest(),
            },
            {
                "arcname": "projects/p/bad.md",
                "scope": "projects",
                "size": 8,
                "sha256": "deadbeef" * 8,  # wrong on purpose
            },
        ],
    )

    root = tmp_path / "target"
    with pytest.raises(importer.IntegrityError):
        importer.run_import(
            zip_path, "pw", root,
            home_claude=tmp_path / "home", backup_root=tmp_path / "bk",
        )
    assert not (root / "p" / "good.md").exists()


def test_create_failure_leaves_no_partial_archive(tmp_path: Path) -> None:
    """An export that fails mid-write must not leave a truncated ZIP (or its
    temporary .part file) behind, or retention could keep a corrupt archive."""
    from claude_code_sync.scanner import Entry

    missing = Entry(tmp_path / "vanished.txt", "projects/p/vanished.txt", "projects")
    out = tmp_path / "out.zip"
    with pytest.raises(OSError):
        archive.create([missing], out, "pw", "projects")
    assert not out.exists()
    assert list(tmp_path.glob("*.part")) == []


@pytest.mark.parametrize(
    "name",
    [
        "../escape.txt",
        "a/../../escape.txt",
        "/abs.txt",
        "..\\win-escape.txt",
        "a/..\\..\\win-escape.txt",
        "",
        ".",
    ],
)
def test_safe_extract_path_rejects_escapes(tmp_path: Path, name: str) -> None:
    """Unit-test the second traversal layer (ZIP member names, not arcnames)."""
    assert archive._safe_extract_path(tmp_path, tmp_path.resolve(), name) is None


def test_extract_skips_hostile_member_names(tmp_path: Path) -> None:
    """A ZIP whose *member names* (not manifest arcnames) try to escape the
    extraction directory must write nothing outside it."""
    zip_path = tmp_path / "evil-members.zip"
    _make_archive(
        zip_path,
        "pw",
        members={
            "../member-escape.txt": b"bad",
            "/member-abs.txt": b"bad",
            "..\\member-win.txt": b"bad",
            "projects/safe.txt": b"ok",
        },
        entries=[],
    )

    dest = tmp_path / "out"
    archive.extract_all(zip_path, dest, "pw")

    extracted = {p.relative_to(dest).as_posix() for p in dest.rglob("*") if p.is_file()}
    assert extracted == {"projects/safe.txt", config.ARCHIVE_MANIFEST}
    assert not (tmp_path / "member-escape.txt").exists()


def test_unsupported_format_version_is_rejected(tmp_path: Path) -> None:
    zip_path = tmp_path / "future.zip"
    _make_archive(zip_path, "pw", members={}, entries=[], format_version=999)
    with pytest.raises(ValueError, match="format version"):
        archive.read_manifest(zip_path, "pw")


def test_member_missing_from_archive_restores_nothing(tmp_path: Path) -> None:
    """A manifest entry without a matching ZIP member must fail loudly instead
    of being silently counted as restored."""
    good = b"good content"
    import hashlib

    zip_path = tmp_path / "padded.zip"
    _make_archive(
        zip_path,
        "pw",
        members={"projects/p/good.md": good},  # ghost.md deliberately absent
        entries=[
            {
                "arcname": "projects/p/good.md",
                "scope": "projects",
                "size": len(good),
                "sha256": hashlib.sha256(good).hexdigest(),
            },
            {"arcname": "projects/p/ghost.md", "scope": "projects", "size": 5, "sha256": None},
        ],
    )

    root = tmp_path / "target"
    backup_root = tmp_path / "bk"
    with pytest.raises(importer.IntegrityError):
        importer.run_import(
            zip_path, "pw", root, home_claude=tmp_path / "home", backup_root=backup_root
        )
    assert not (root / "p" / "good.md").exists()
    # The backup dir is created lazily, so a failed import leaves none behind.
    assert not backup_root.exists()


@pytest.mark.skipif(
    not _SYMLINKS_OK, reason="symlink creation not permitted on this platform/account"
)
def test_symlinked_directories_are_not_scanned(tmp_path: Path) -> None:
    """os.walk(followlinks=False) still traverses a symlinked *base*, so the
    scanner must reject symlinked project dirs, .claude/ dirs and global
    include dirs itself."""
    from claude_code_sync import scanner

    outside = tmp_path / "outside"
    (outside / ".claude").mkdir(parents=True)
    (outside / "CLAUDE.md").write_text("outside memory\n", encoding="utf-8")
    (outside / ".claude" / "settings.json").write_text("{}", encoding="utf-8")

    root = tmp_path / "GitHub"
    root.mkdir()
    (root / "linked-proj").symlink_to(outside, target_is_directory=True)
    real_proj = root / "real-proj"
    real_proj.mkdir()
    (real_proj / ".claude").symlink_to(outside / ".claude", target_is_directory=True)

    arcs = {e.arcname for e in scanner.scan_projects(root)}
    assert not any("linked-proj" in a for a in arcs)
    assert not any("real-proj/.claude" in a for a in arcs)

    home_claude = tmp_path / "home-claude"
    home_claude.mkdir()
    skills_src = tmp_path / "skills-src"
    skills_src.mkdir()
    (skills_src / "skill.md").write_text("outside skill\n", encoding="utf-8")
    (home_claude / "skills").symlink_to(skills_src, target_is_directory=True)

    global_arcs = {e.arcname for e in scanner.scan_global(home_claude)}
    assert "global/skills/skill.md" not in global_arcs


@pytest.mark.skipif(
    not _SYMLINKS_OK, reason="symlink creation not permitted on this platform/account"
)
def test_symlinked_global_top_level_file_is_collected(tmp_path: Path) -> None:
    """The dotfile-manager exception: allow-listed global top-level files are
    collected even when symlinked, while files deeper in include dirs are not."""
    from claude_code_sync import scanner

    home_claude = tmp_path / "home-claude"
    (home_claude / "skills").mkdir(parents=True)
    dotfiles = tmp_path / "dotfiles"
    dotfiles.mkdir()
    (dotfiles / "settings.json").write_text("{}", encoding="utf-8")
    (dotfiles / "deep.md").write_text("outside\n", encoding="utf-8")
    (home_claude / "settings.json").symlink_to(dotfiles / "settings.json")
    (home_claude / "skills" / "deep.md").symlink_to(dotfiles / "deep.md")

    arcs = {e.arcname for e in scanner.scan_global(home_claude)}
    assert "global/settings.json" in arcs
    assert "global/skills/deep.md" not in arcs


@pytest.mark.skipif(
    not _SYMLINKS_OK, reason="symlink creation not permitted on this platform/account"
)
def test_follow_symlinks_toggle_collects_symlinked_files(tmp_path: Path) -> None:
    import dataclasses

    from claude_code_sync import scanner
    from claude_code_sync.config import ScanConfig

    root = tmp_path / "GitHub"
    project = root / "proj"
    project.mkdir(parents=True)
    outside = tmp_path / "outside.md"
    outside.write_text("linked memory\n", encoding="utf-8")
    (project / "CLAUDE.md").symlink_to(outside)

    cfg = dataclasses.replace(ScanConfig.default(), follow_symlinks=True)
    arcs = {e.arcname for e in scanner.scan_projects(root, cfg)}
    assert "projects/proj/CLAUDE.md" in arcs


def test_import_detects_checksum_mismatch(tmp_path: Path) -> None:
    zip_path = tmp_path / "tampered.zip"
    _make_archive(
        zip_path,
        "pw",
        members={"projects/p/CLAUDE.md": b"real content"},
        entries=[
            {
                "arcname": "projects/p/CLAUDE.md",
                "scope": "projects",
                "size": 12,
                "sha256": "deadbeef" * 8,  # wrong on purpose
            }
        ],
    )

    with pytest.raises(importer.IntegrityError):
        importer.run_import(
            zip_path, "pw", tmp_path / "target",
            home_claude=tmp_path / "home", backup_root=tmp_path / "bk",
        )
