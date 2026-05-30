# Credits

Claude Code Sync is released under the [MIT License](./LICENSE). Every third-party asset and library it ships is distributed under an OSI-approved or FSF-approved open source licence. No CDN is contacted at runtime.

## Fonts

- **Inter.** Copyright © The Inter Project Authors, licensed under the [SIL Open Font License 1.1](https://openfontlicense.org/). Source: <https://github.com/rsms/inter>. Bundled (latin variable `.woff2`) for offline use.
- **Source Serif 4.** Copyright © Adobe, licensed under the [SIL Open Font License 1.1](https://openfontlicense.org/). Source: <https://github.com/adobe-fonts/source-serif>. Bundled (latin variable `.woff2`) for offline use.

These are open approximations of the look of claude.ai; Anthropic's actual fonts (Styrene, Copernicus/Tiempos) are proprietary and are not bundled.

## Icons

- **Heroicons.** Copyright © Tailwind Labs, licensed under the [MIT License](https://github.com/tailwindlabs/heroicons/blob/master/LICENSE). Source: <https://heroicons.com/>. Used as inline SVG in the web UI, plus the favicon.

## Runtime

- [pyzipper](https://github.com/danifus/pyzipper). MIT licence. AES-256 encrypted ZIP archives — the only runtime dependency.
- [tomllib](https://docs.python.org/3/library/tomllib.html) and [http.server](https://docs.python.org/3/library/http.server.html) from the Python standard library power the optional config file and the local web server.

## Development tooling

- [pytest](https://pytest.org/) and [pytest-cov](https://github.com/pytest-dev/pytest-cov). MIT licence. Tests and coverage.
- [Ruff](https://docs.astral.sh/ruff/). MIT licence. Linting and import sorting.
- [mypy](https://mypy-lang.org/). MIT licence. Static type checking.
- [PyInstaller](https://pyinstaller.org/). GPL-2.0-with-exception (the produced binaries are unencumbered). Optional standalone-binary builds.

## Acknowledgements

Inspired by [jean-claude](https://github.com/MikeVeerman/jean-claude). Thanks to the maintainers of every dependency listed above, and to everyone who reported a bug or suggested an improvement.
