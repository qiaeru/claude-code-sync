# Building a standalone binary

For machines without Python, you can build a single self-contained executable with [PyInstaller](https://pyinstaller.org/). The bundled binary includes the web UI assets and (where available) tkinter for the native file pickers.

## Build

```bash
pip install -e ".[dev,build]"   # installs pyinstaller
pyinstaller claude-code-sync.spec
```

The executable is written to `dist/claude-code-sync` (`dist\claude-code-sync.exe` on Windows). Build on the OS you want to target. PyInstaller does not cross-compile.

## Run

```bash
./dist/claude-code-sync           # launches the web UI
./dist/claude-code-sync export --root . --scope all
```

## Notes

- The spec bundles `claude_code_sync/webui/**` so the UI works from the single file.
- In a frozen build the native **Browse…** dialog runs in-process (there is no separate Python interpreter to spawn). If tkinter is not bundled, typing or drag-and-dropping the path still works.
- `upx=True` in the spec compresses the binary if [UPX](https://upx.github.io/) is installed; it is optional and skipped without warning otherwise.
