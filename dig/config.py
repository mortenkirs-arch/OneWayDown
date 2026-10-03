"""Global constants: window, board geometry, persistence and colours."""
import os

import pygame

# The window is the largest of these that fits the desktop. Text stays the same size; the board
# scales up with the window so there's more room around the (fixed-size) characters.
# Override with e.g. KEEP_DIGGING_RES=1280x720.
RESOLUTIONS = [(1600, 900), (1440, 810), (1280, 720)]
BASE_W = 1280                 # the layout was designed at 1280x720


def _pick_resolution():
    forced = os.environ.get("KEEP_DIGGING_RES")
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

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SAVE_PATH = os.path.join(PROJECT_ROOT, "savegame.json")
AUTOSAVE_SECS = 10
OFFLINE_CAP_SECS = 8 * 3600

BG_TOP = (28, 22, 40)
BG_BOTTOM = (10, 8, 16)
PANEL = (38, 32, 52)
PANEL_EDGE = (78, 66, 104)
TEXT = (236, 230, 245)
MUTED = (150, 140, 170)
GOLD = (255, 205, 70)
GOOD = (110, 210, 120)
BAD = (220, 90, 90)
