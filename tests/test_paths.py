"""Every asset path in the config must exist, with the exact same case.

Windows ignores case in file names, so "Font.TTF" finds "font.ttf" there,
but Linux (CI) and the browser build don't: the game would work on your
PC and crash on the web. This test catches it on any system.
"""

from pathlib import Path

import pytest

from config import PATHS


def asset_paths():
    for name, value in vars(PATHS).items():
        if name.startswith("_") or not isinstance(value, (str, Path)):
            continue
        path = Path(value)
        if path.suffix:   # files only; folders are checked through their files
            yield name, path


@pytest.mark.parametrize("name, path", list(asset_paths()), ids=lambda v: str(v))
def test_asset_exists_with_exact_case(name, path):
    assert path.exists(), f"{name}: {path} not found"
    # Compare against the real names on disk, part by part
    current = Path(path.anchor) if path.is_absolute() else Path(".")
    for part in path.parts[len(path.parts) - len(path.relative_to(current).parts):]:
        names = {p.name for p in current.iterdir()}
        assert part in names, f"{name}: '{part}' has different case on disk in {current}"
        current = current / part
