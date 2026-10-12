"""Where saves and settings are kept. On the desktop: files (written whole, then swapped in, so a crash mid-save
can't leave half a file). In a browser build (pygbag, sys.platform "emscripten"): the browser's own storage
(localStorage) - its file system is wiped when the tab closes, localStorage isn't. Paths name the entry either way."""
import os
import sys
import time

WEB = sys.platform == "emscripten"
PREFIX = "onewaydown:"


def _local():
    import platform   # (pygbag's: the page's JavaScript `window`)
    return platform.window.localStorage


def _key(path):
    return PREFIX + os.path.basename(path)


def read(path):
    """The text saved at `path`, or None if there's none (or it can't be read)."""
    if WEB:
        try:
            text = _local().getItem(_key(path))
        except Exception:   # (no storage: private browsing, or blocked)
            return None
        return None if text is None else str(text)
    try:
        with open(path, encoding="utf-8") as f:
            return f.read()
    except OSError:
        return None


def write(path, text):
    """Save `text` at `path`. Quietly gives up if it can't (better a lost save than a crashed game)."""
    if WEB:
        try:
            _local().setItem(_key(path), text)
            _local().setItem(_key(path) + ":saved", str(time.time()))
        except Exception:
            pass
        return
    try:
        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)   # (e.g. saves/ for test games)
        tmp = path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            f.write(text)
        os.replace(tmp, path)
    except OSError:
        pass


def exists(path):
    if WEB:
        return read(path) is not None
    return os.path.exists(path)


def saved_at(path):
    """When `path` was last saved (seconds since the epoch; 0 if never)."""
    if WEB:
        try:
            return float(_local().getItem(_key(path) + ":saved") or 0)
        except (Exception,):
            return 0.0
    try:
        return os.path.getmtime(path)
    except OSError:
        return 0.0
