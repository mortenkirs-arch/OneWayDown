"""The game's window and taskbar icon: a pickaxe over a gold arrow pointing down (the only way is down).

Drawn at ICON_DRAW px with pygame shapes, then smooth-scaled to the size asked for, so it stays crisp small.
(Options it was picked from: mockups/icons/make_icon_options.py.)
"""
import math
import sys

import pygame

ICON_DRAW = 256
NIGHT, NIGHT_EDGE = (28, 22, 40), (70, 58, 96)
GOLD, GOLD_DARK = (255, 205, 70), (170, 115, 25)
HANDLE, HANDLE_DARK, STEEL, STEEL_DARK = (150, 100, 55), (95, 60, 30), (205, 210, 220), (120, 125, 140)
APP_ID = "OnlyWayIsDown.Game"   # (Windows: groups the game's window under its own icon, not Python's)


def _pickaxe(s, cx, cy, size, ang):
    """A pickaxe centred on (cx, cy), its handle along `ang`, the curved head across the top."""
    dx, dy = math.cos(ang), math.sin(ang)
    a, b = (cx - dx * size * 0.55, cy - dy * size * 0.55), (cx + dx * size * 0.45, cy + dy * size * 0.45)
    pygame.draw.line(s, HANDLE_DARK, a, b, int(size * 0.13))
    pygame.draw.line(s, HANDLE, a, b, int(size * 0.08))
    nx, ny = -dy, dx
    head = []
    for i in range(-10, 11):
        k = i / 10
        bend = (1 - k * k) * size * 0.12
        head.append((b[0] + nx * k * size * 0.48 + dx * bend, b[1] + ny * k * size * 0.48 + dy * bend))
    pygame.draw.lines(s, STEEL_DARK, False, head, int(size * 0.16))
    pygame.draw.lines(s, STEEL, False, head, int(size * 0.1))


def make_icon(size=64):
    s = ICON_DRAW
    img = pygame.Surface((s, s), pygame.SRCALPHA)
    pygame.draw.rect(img, NIGHT, (8, 8, s - 16, s - 16), border_radius=48)
    pygame.draw.rect(img, NIGHT_EDGE, (8, 8, s - 16, s - 16), 10, border_radius=48)
    cx, top, w, h = s / 2, 40, 150, 180   # the arrow pointing down
    shaft = w * 0.38
    arrow = [(cx - shaft / 2, top), (cx + shaft / 2, top), (cx + shaft / 2, top + h * 0.5), (cx + w / 2, top + h * 0.5),
             (cx, top + h), (cx - w / 2, top + h * 0.5), (cx - shaft / 2, top + h * 0.5)]
    pygame.draw.polygon(img, GOLD, arrow)
    pygame.draw.polygon(img, GOLD_DARK, arrow, 8)
    _pickaxe(img, s / 2 - 14, s / 2 + 14, 150, -math.pi / 4)
    return pygame.transform.smoothscale(img, (size, size))


def set_app_icon():
    """Give the window (title bar and taskbar) the game's icon. Call before the window is opened."""
    if sys.platform == "win32":   # its own app id, so the taskbar shows our icon rather than python.exe's
        try:
            import ctypes
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(APP_ID)
        except (AttributeError, OSError):
            pass
    pygame.display.set_icon(make_icon(64))
