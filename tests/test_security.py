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
    path: Path, password: str, members: dict[str, bytes], entries: list[dict]
) -> None:
    """Write a hand-crafted encrypted archive with an arbitrary manifest."""
    man = {
        "format_version": config.ARCHIVE_VERSION,
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
