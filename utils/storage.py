"""Small JSON documents that persist between sessions.

On desktop each document is a file. In the browser (pygbag) files live in
memory and vanish when the page reloads, so documents go to the browser's
localStorage instead, under the file's name.
"""

import json

from utils.runtime import WEB


def _local_storage():
    from platform import window   # pygbag's bridge to the browser (only exists there)
    return window.localStorage


def load(path, default):
    """Read the JSON document at path; `default` if missing or corrupt."""
    try:
        if WEB:
            text = _local_storage().getItem(path.name)
            if text is None:
                return default
            return json.loads(text)
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError, TypeError):
        return default


def save(path, data):
    """Write data as a JSON document at path."""
    text = json.dumps(data, ensure_ascii=False, indent=2)
    if WEB:
        _local_storage().setItem(path.name, text)
        return
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)
