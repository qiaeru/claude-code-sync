# PyInstaller spec: build a standalone binary with `pyinstaller claude-code-sync.spec`.
# Produces a single-file executable named `claude-code-sync` that bundles the web UI.
from pathlib import Path

# Bundle every web UI asset (HTML/CSS/JS/SVG/fonts), preserving structure so that
# server.WEBUI_DIR (claude_code_sync/webui) resolves inside the unpacked bundle.
# Anchored on SPECPATH (injected by PyInstaller), not the cwd: invoked from
# outside the repo root, a relative path would silently bundle zero assets.
_root = Path(SPECPATH)
_webui = _root / "claude_code_sync" / "webui"
_ASSET_SUFFIXES = {".html", ".css", ".js", ".svg", ".woff2", ".md"}
datas = [
    (str(p), str(p.parent.relative_to(_root)))
    for p in _webui.rglob("*")
    if p.is_file() and p.suffix in _ASSET_SUFFIXES
]

a = Analysis(
    ["claude_code_sync/__main__.py"],
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=["tkinter"],
    hookspath=[],
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)
pyz = PYZ(a.pure, a.zipped_data)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name="claude-code-sync",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
