"""Global constants: window, board geometry, persistence and colours."""
import os
import sys

import pygame

# The window is the largest of these that fits the desktop. Text stays the same size; the board
# scales up with the window so there's more room around the (fixed-size) characters.
# Override with e.g. ONE_WAY_DOWN_RES=1280x720.
RESOLUTIONS = [(1600, 900), (1440, 810), (1280, 720)]
BASE_W = 1280                 # the layout was designed at 1280x720


def _pick_resolution():
    if sys.platform == "emscripten":   # (in a browser: the page scales it to fit)
        return 1280, 720
    forced = os.environ.get("ONE_WAY_DOWN_RES") or os.environ.get("THE_ONLY_WAY_IS_DOWN_RES")   # (its old name too)
    if forced:
        w, h = forced.lower().split("x")
        return int(w), int(h)
    try:
        pygame.display.init()
        sizes = pygame.display.get_desktop_sizes()
    except pygame.error:
        sizes = []
    if not sizes or sizes[0][0] <= 0:
        return RESOLUTIONS[0]
    dw, dh = sizes[0]
    for w, h in RESOLUTIONS:
        if w <= dw - 40 and h <= dh - 80:   # leave room for the title bar and taskbar
            return w, h
    return RESOLUTIONS[-1]


W, H = _pick_resolution()
SCALE = W / BASE_W
FPS = 60

GRID = 10                                       # board is GRID x GRID cells
TILE_W = 2 * round(36 * SCALE)                  # isometric diamond size (72 x 36 at 1280 wide)
TILE_H = TILE_W // 2
BLOCK_H = round(34 * SCALE)                     # pixel height of one block
BOARD_ORIGIN = (W // 2, round(200 * SCALE))     # screen position of the board's back corner at z=0
GOLD_HUD_COIN = (52, 44)      # where the HUD's gold coin sits; earned coins fly here

FROZEN = getattr(sys, "frozen", False)   # a packaged build (PyInstaller: see tools/build_release.py), not the source
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RESOURCE_ROOT = getattr(sys, "_MEIPASS", PROJECT_ROOT)   # where assets/ is (packaged: where PyInstaller put it)


def _data_dir():
    """Where saves and settings live: from source, the project folder (as ever); packaged, the player's own folder
    (%APPDATA%/OneWayDown and the like), so the game's folder can be read-only and updates never touch them."""
    if not FROZEN:
        return PROJECT_ROOT
    if sys.platform == "win32":
        base = os.environ.get("APPDATA") or os.path.expanduser("~")
    elif sys.platform == "darwin":
        base = os.path.expanduser("~/Library/Application Support")
    else:
        base = os.environ.get("XDG_DATA_HOME") or os.path.expanduser("~/.local/share")
    path = os.path.join(base, "OneWayDown")
    os.makedirs(path, exist_ok=True)
    return path


DATA_DIR = _data_dir()
SAVE_PATH = os.path.join(DATA_DIR, "savegame.json")
SAVE_SLOTS = [SAVE_PATH] + [os.path.join(DATA_DIR, f"savegame_{n}.json") for n in (2, 3)]   # (Load Game)
AUTOSAVE_SECS = 10
MUSIC_DIR = os.path.join(RESOURCE_ROOT, "assets", "music")   # (regenerate with: uv run tools/make_music.py)
AUDIO_EXT = ".ogg" if sys.platform == "emscripten" else ".wav"   # (browsers want Ogg: tools/build_web.py converts)

PANEL = (38, 32, 52)
PANEL_EDGE = (78, 66, 104)
TEXT = (236, 230, 245)
MUTED = (150, 140, 170)
GOLD = (255, 205, 70)
GOOD = (110, 210, 120)
BAD = (220, 90, 90)
