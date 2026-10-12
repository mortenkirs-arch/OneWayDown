"""Reusable UI widgets and text helpers."""
import math

import pygame

import os

from .config import MUTED, PANEL, PANEL_EDGE, RESOURCE_ROOT, TEXT
from .util import shade


COIN, COIN_EDGE, COIN_SHINE = (255, 205, 70), (185, 130, 35), (255, 242, 180)


def draw_coin(surf, center, r):
    """A little gold coin: thick edge, raised inner ring and a glint."""
    x, y = int(center[0]), int(center[1])
    r = max(3, int(r))
    pygame.draw.circle(surf, COIN_EDGE, (x, y + max(1, r // 5)), r)          # coin thickness
    pygame.draw.circle(surf, COIN, (x, y), r)
    pygame.draw.circle(surf, COIN_EDGE, (x, y), max(2, int(r * 0.66)), max(1, r // 6))
    pygame.draw.circle(surf, COIN_SHINE, (x - int(r * 0.35), y - int(r * 0.35)), max(1, r // 4))


def gold_label(fonts, text, size, color):
    """A coin followed by `text`, as one surface (so it can fade like other text)."""
    img = fonts[size].render(text, True, color)
    r = max(3, int(size * 0.3))
    gap = max(3, size // 7)
    w, h = 2 * r + gap + img.get_width(), max(img.get_height(), 2 * r + 3)
    label = pygame.Surface((w, h), pygame.SRCALPHA)
    draw_coin(label, (r, h // 2 - 1), r)
    label.blit(img, img.get_rect(midleft=(2 * r + gap, h // 2)))
    return label


def draw_gold(surf, fonts, text, size, color, pos, anchor="topleft"):
    """Draw a gold amount with its coin icon; returns the bounding rect."""
    label = gold_label(fonts, text, size, color)
    rect = label.get_rect(**{anchor: pos})
    surf.blit(label, rect)
    return rect


def draw_pointer(surf, tip, direction, t, color=COIN):
    """A bouncing arrow whose point sits at `tip`, pointing "up", "down", "left" or "right"."""
    dx, dy = {"up": (0, -1), "down": (0, 1), "left": (-1, 0), "right": (1, 0)}[direction]
    bounce = abs(math.sin(t * 6)) * 8
    tx, ty = tip[0] - dx * bounce, tip[1] - dy * bounce
    px, py = -dy, dx                                    # perpendicular
    head = [(tx, ty), (tx - dx * 16 + px * 11, ty - dy * 16 + py * 11),
            (tx - dx * 16 - px * 11, ty - dy * 16 - py * 11)]
    shaft = [(tx - dx * 14 + px * 4, ty - dy * 14 + py * 4), (tx - dx * 34 + px * 4, ty - dy * 34 + py * 4),
             (tx - dx * 34 - px * 4, ty - dy * 34 - py * 4), (tx - dx * 14 - px * 4, ty - dy * 14 - py * 4)]
    for poly in (shaft, head):
        pygame.draw.polygon(surf, (40, 30, 10), [(x + 2, y + 2) for x, y in poly])   # drop shadow
        pygame.draw.polygon(surf, color, poly)


def draw_callout(surf, fonts, lines, pos, anchor="center", size=24):
    """A gold-bordered hint box. `lines` is a list of (text, colour)."""
    imgs = [fonts[size].render(text, True, color) for text, color in lines]
    w = max(i.get_width() for i in imgs) + 28
    h = sum(i.get_height() for i in imgs) + 18
    box = pygame.Rect(0, 0, w, h)
    setattr(box, anchor, pos)
    pygame.draw.rect(surf, PANEL, box, border_radius=10)
    pygame.draw.rect(surf, COIN, box, 2, border_radius=10)
    y = box.y + 9
    for img in imgs:
        surf.blit(img, img.get_rect(midtop=(box.centerx, y)))
        y += img.get_height()
    return box


def draw_glow(surf, rect, t, color=COIN):
    """Pulsing outline drawing the eye to a button or tab."""
    grow = 3 + int(3 * (0.5 + 0.5 * math.sin(t * 6)))
    pygame.draw.rect(surf, color, rect.inflate(grow * 2, grow * 2), 3, border_radius=12)


class Button:
    def __init__(self, rect, text, action, size=30, color=(86, 70, 130)):
        self.rect = pygame.Rect(rect)
        self.text, self.action, self.size, self.color = text, action, size, color
        self.enabled = True
        self.gold = None   # optional price shown as "<text>  (coin) <gold>"
        self.nudge = 0     # px the label sits right of centre (room for an icon drawn on the button's left)

    def draw(self, surf, fonts, mouse):
        """A chunky bevelled button: a dark rim, a lit upper face over a shadowed lower one, a highlight along the
        top edge, a drop shadow beneath - and the label (in the display font) stamped in with a shadow of its own."""
        hover = self.enabled and self.rect.collidepoint(mouse)
        base = self.color if self.enabled else (60, 56, 70)
        if hover:
            base = shade(base, 1.2)
        r = self.rect
        pygame.draw.rect(surf, (10, 8, 14), r.move(0, 5).inflate(2, 2), border_radius=11)   # drop shadow
        pygame.draw.rect(surf, shade(base, 0.35), r.inflate(4, 4), border_radius=12)         # dark rim
        pygame.draw.rect(surf, shade(base, 0.72), r, border_radius=10)                        # the lower face...
        top = pygame.Rect(r.x, r.y, r.w, int(r.h * 0.55))
        pygame.draw.rect(surf, base, top, border_top_left_radius=10, border_top_right_radius=10)   # ...the upper
        pygame.draw.line(surf, shade(base, 1.45), (r.x + 8, r.y + 2), (r.right - 9, r.y + 2), 2)   # (its highlight)
        pygame.draw.rect(surf, shade(base, 1.25), r, 1, border_radius=10)
        color = TEXT if self.enabled else MUTED
        font = fonts.display(self.size)
        label = font.render(self.text, True, color)
        under = font.render(self.text, True, shade(base, 0.3))
        if self.gold is None:
            cx = r.centerx + self.nudge
            surf.blit(under, under.get_rect(center=(cx, r.centery + 2)))
            surf.blit(label, label.get_rect(center=(cx, r.centery)))
            return
        price = gold_label(fonts, self.gold, self.size, color)
        gap = self.size // 2
        x = self.rect.centerx - (label.get_width() + gap + price.get_width()) // 2
        surf.blit(under, under.get_rect(midleft=(x, self.rect.centery + 2)))
        surf.blit(label, label.get_rect(midleft=(x, self.rect.centery)))
        surf.blit(price, price.get_rect(midleft=(x + label.get_width() + gap, self.rect.centery)))

    def handle(self, event):
        if (self.enabled and event.type == pygame.MOUSEBUTTONDOWN and event.button == 1
                and self.rect.collidepoint(event.pos)):
            self.action()
            return True
        return False


FONTS_DIR = os.path.join(RESOURCE_ROOT, "assets", "fonts")   # (both under the SIL Open Font License: see there)
DISPLAY_FONT = os.path.join(FONTS_DIR, "LilitaOne-Regular.ttf")
DISPLAY_FROM = 32      # text this big (titles, headings, big pop-ups) - and every button - is in the display font...
DISPLAY_SCALE = 0.78   # ...drawn at this share of the size asked for (it runs wide: this keeps labels where they fit)
BODY_FONT = os.path.join(FONTS_DIR, "Fredoka-SemiBold.ttf")   # everything smaller: rounded, to go with it...
BODY_SCALE = 0.76      # ...and drawn at this share of the size asked for (the room the old default font took)


class Fonts(dict):
    """Lazily-created fonts keyed by pixel size: fonts[24]. Body text is Fredoka; from DISPLAY_FROM up it's the
    display font (Lilita One), as is fonts.display(size) at any size (buttons). (Either missing: the plain default.)"""

    def __init__(self):
        super().__init__()
        self.shown = {}

    def __missing__(self, size):
        f = self.display(size) if size >= DISPLAY_FROM else _load(BODY_FONT, size, BODY_SCALE)
        self[size] = f
        return f

    def display(self, size):
        f = self.shown.get(size)
        if f is None:
            f = self.shown[size] = _load(DISPLAY_FONT, size, DISPLAY_SCALE)
        return f


def _load(path, size, scale):
    """A font at `size` (drawn at `scale` of it), or the plain default if it can't be loaded."""
    try:
        return pygame.font.Font(path, max(8, round(size * scale)))
    except (OSError, FileNotFoundError):
        return pygame.font.Font(None, size)


def draw_text(surf, fonts, text, size, color, pos, anchor="topleft"):
    img = fonts[size].render(text, True, color)
    rect = img.get_rect(**{anchor: pos})
    surf.blit(img, rect)
    return rect


def draw_panel(surf, rect, radius=12):
    pygame.draw.rect(surf, PANEL, rect, border_radius=radius)
    pygame.draw.rect(surf, PANEL_EDGE, rect, 2, border_radius=radius)


def wrap_text(font, text, width):
    lines, line = [], ""
    for word in text.split():
        trial = f"{line} {word}".strip()
        if font.size(trial)[0] <= width:
            line = trial
        else:
            lines.append(line)
            line = word
    if line:
        lines.append(line)
    return lines
