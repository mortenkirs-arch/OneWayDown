"""Global constants: window, board geometry, persistence and colours."""
import os

W, H = 1280, 720
FPS = 60

GRID = 8                      # board is GRID x GRID cells
TILE_W, TILE_H = 72, 36       # isometric diamond size
BLOCK_H = 34                  # pixel height of one block
BOARD_ORIGIN = (W // 2, 200)  # screen position of the board's back corner at z=0

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
