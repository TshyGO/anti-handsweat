"""Resolve local tools without relying on Finder's inherited PATH."""
from __future__ import annotations
import os
from pathlib import Path
import shutil
import sys


def discover_exiftool(preferred: str = '', root: Path | None = None) -> str:
    """Respect an explicit choice; otherwise search the package and standard locations.

    This function only finds a path. Executable validation takes place on invocation.
    A missing explicitly chosen path must not silently fall back to another version.
    """
    if preferred.strip():
        return str(Path(preferred.strip()).expanduser())
    candidates: list[Path] = []
    if root is not None:
        candidates += [root / 'tools' / 'exiftool', root / 'tools' / 'exiftool.exe']
    found = shutil.which('exiftool')
    if found:
        candidates.append(Path(found))
    if sys.platform == 'darwin':
        candidates += [Path('/usr/local/bin/exiftool'), Path('/opt/homebrew/bin/exiftool')]
    for path in candidates:
        if path.is_file() and (sys.platform == 'win32' or os.access(path, os.X_OK)):
            return str(path)
    return ''
