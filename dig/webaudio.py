"""Sound in a browser build (pygbag): played by the browser's own mixer - window.owdAudio, the Web Audio player in
tools/web/onewaydown.tmpl - instead of pygame's. pygame mixes in Python between frames and hands the browser a buffer
at a time, so every sound waited a buffer's length to start (and a slow frame made it crackle); the browser mixes on
its own audio thread, starting each sound as it's asked for. Paths name the game's own files (the player reads them
from the page's file system). Each call quietly does nothing if there's no player (no Web Audio in this browser)."""


def _player():
    import platform   # (pygbag's: the page's JavaScript `window`)
    return platform.window.owdAudio


def available():
    try:
        return bool(_player())
    except Exception:
        return False


def _call(method, *args):
    try:
        getattr(_player(), method)(*args)
    except Exception:
        pass


def preload(path):
    """Decode `path` now, so its first play starts straight away."""
    _call("preload", path)


def play(sound_id, path, volume):
    """Play the sound effect in `path` at `volume` (0..1); `sound_id` names it for stop()."""
    _call("play", sound_id, path, volume)


def stop(sound_id, fade_ms):
    _call("stop", sound_id, fade_ms)


def music(path, volume, fade_out_ms, fade_in_ms):
    """Change track to `path` (None: silence): the old one fades out, then the new one fades in, looping for ever."""
    _call("music", path or "", volume, fade_out_ms, fade_in_ms)


def music_volume(volume):
    _call("musicVolume", volume)
