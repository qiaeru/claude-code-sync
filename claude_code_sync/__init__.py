"""A small tool that syncs your Claude Code configuration across machines, offline and encrypted.

The package is split into UI-agnostic core modules (:mod:`scanner`,
:mod:`archive`, :mod:`importer`, :mod:`manifest`, :mod:`config`) and a thin local
web layer (:mod:`server`, :mod:`api`). The core can be reused from tests or a
future CLI without starting the web server.
"""

__version__ = "1.0.0"
