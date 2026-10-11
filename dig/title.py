"""The main menu's title: "ONE WAY" above a big DOWN carved from ore-studded stone, with a skeleton
leaning on the N. The stone is drawn once and cached; the ore glints and the skeleton sways each frame."""
import math
import random

import pygame

from .enemies import Enemy
from .iso import origin_at
from .sprites import DRAWERS
from .util import shade

SMALL_LINE = "ONE WAY"
SMALL_COLOR, SMALL_SHADOW = (255, 205, 70), (20, 14, 26)
STONE = (124, 122, 132)
RIM, GLOW = (30, 24, 28), (255, 200, 80)
ORE = [(255, 212, 60), (255, 212, 60), (225, 40, 70), (110, 235, 245)]   # gold (twice as common), ruby, diamond
DOWN_SIZE, SMALL_SIZE, SPACING = 210, 46, 10
SKELETON_SCALE = 3.0
ORE_COUNT = 18   # gems set into the stone


def _font(size):
    f = pygame.font.Font(None, size)
    f.set_bold(True)
    return f


def _tint(mask, color, alpha=255):
    m = mask.copy()
    m.fill((*color, alpha), special_flags=pygame.BLEND_RGBA_MULT)
    return m


def _grow(mask, color, r):
    """The mask thickened by `r` px in `color`: rims, shadows and glows."""
    t = _tint(mask, color)
    out = pygame.Surface((mask.get_width() + 2 * r, mask.get_height() + 2 * r), pygame.SRCALPHA)
    for dx in range(-r, r + 1):
        for dy in range(-r, r + 1):
            if dx * dx + dy * dy <= r * r:
                out.blit(t, (r + dx, r + dy))
    return out


def _bevel(mask, color, alpha, shift):
    """The letters' rim on one side: the mask minus itself moved by `shift`."""
    edge = _tint(mask, color, alpha)
    edge.blit(_tint(mask, (0, 0, 0), 255), shift, special_flags=pygame.BLEND_RGBA_SUB)
    return edge


def _stone(size, seed):
    """Speckled stone, lighter at the top, with a few dark cracks."""
    w, h = size
    rng = random.Random(seed)
    surf = pygame.Surface(size, pygame.SRCALPHA)
    for y in range(h):
        surf.fill((*shade(STONE, 1.18 - 0.45 * y / h), 255), (0, y, w, 1))
    for _ in range(w * h // 90):
        pygame.draw.circle(surf, shade(STONE, rng.uniform(0.6, 1.25)), (rng.randrange(w), rng.randrange(h)),
                           rng.randint(1, 4))
    for _ in range(6):
        x, y = rng.uniform(0, w), rng.uniform(0, h * 0.4)
        pts = [(x, y)]
        for _ in range(rng.randint(3, 6)):
            x += rng.uniform(-18, 18)
            y += rng.uniform(12, 30)
            pts.append((x, y))
        pygame.draw.lines(surf, shade(STONE, 0.35), False, pts, 2)
    return surf


class Title:
    """Built once for a screen width; `draw` puts it on screen with the live touches (glints, the skeleton)."""

    def __init__(self, width, seed=3):
        mask = _font(DOWN_SIZE).render("DOWN", True, (255, 255, 255))
        pad = 24
        self.down_size = mask.get_size()
        self.surf = pygame.Surface((mask.get_width() + 2 * pad, mask.get_height() + 2 * pad), pygame.SRCALPHA)
        glow = _grow(mask, GLOW, 18)
        glow.set_alpha(60)
        self.surf.blit(glow, (pad - 18, pad - 18))
        shadow = _grow(mask, (8, 6, 10), 6)
        shadow.set_alpha(180)
        self.surf.blit(shadow, (pad + 2, pad + 4))
        self.surf.blit(_grow(mask, RIM, 6), (pad - 6, pad - 6))
        stone = _stone(mask.get_size(), seed)
        stone.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
        self.surf.blit(stone, (pad, pad))
        self.surf.blit(_bevel(mask, (255, 255, 255), 80, (3, 4)), (pad, pad))   # light on the upper-left edges...
        self.surf.blit(_bevel(mask, (0, 0, 0), 120, (-3, -4)), (pad, pad))      # ...shade on the lower-right
        rng = random.Random(9)
        self.ore = []   # (x, y, colour) relative to the word, for the glints
        for _ in range(400):
            px, py = rng.randrange(mask.get_width()), rng.randrange(mask.get_height())
            if mask.get_at((px, py))[3] > 200 and len(self.ore) < ORE_COUNT:
                c = rng.choice(ORE)
                self.ore.append((px, py, c))
                gx, gy = pad + px, pad + py   # a little diamond-shaped gem
                pts = [(gx, gy - 6), (gx + 5, gy), (gx, gy + 6), (gx - 5, gy)]
                pygame.draw.polygon(self.surf, c, pts)
                pygame.draw.polygon(self.surf, shade(c, 0.55), pts, 1)
        self.pad = pad
        self.n_right = sum(_font(DOWN_SIZE).size(c)[0] for c in "DOWN")   # (the N's right edge, from the word's left)
        self.skeleton = Enemy("skeleton", 5, (0, 0), 0)
        self.skeleton.state, self.skeleton.x, self.skeleton.y, self.skeleton.draw_z = "standing", 0.0, 0.0, 0.0
        self.skeleton.facing, self.skeleton.show_hp = -1, False

    def draw(self, surf, center_x, top, t):
        """Draw the title with its top at `top`. Returns the bottom of the drawn title."""
        f = _font(SMALL_SIZE)
        widths = [f.size(c)[0] for c in SMALL_LINE]
        x = center_x - (sum(widths) + SPACING * (len(SMALL_LINE) - 1)) // 2
        for c, wd in zip(SMALL_LINE, widths):   # the spaced-out small line
            surf.blit(f.render(c, True, SMALL_SHADOW), (x + 2, top + 3))
            surf.blit(f.render(c, True, SMALL_COLOR), (x, top))
            x += wd + SPACING
        word_x = center_x - self.down_size[0] // 2
        word_y = top + SMALL_SIZE - 6
        surf.blit(self.surf, (word_x - self.pad, word_y - self.pad))
        for k, (px, py, c) in enumerate(self.ore):   # a few ore glints at a time, in turn
            glint = math.sin(t * 2.2 + k * 2.39)
            if glint > 0.85:
                r = int(3 + (glint - 0.85) * 40)
                gx, gy = word_x + px, word_y + py
                pygame.draw.line(surf, (255, 255, 255), (gx - r, gy), (gx + r, gy), 1)
                pygame.draw.line(surf, (255, 255, 255), (gx, gy - r), (gx, gy + r), 1)
        self._draw_skeleton(surf, (word_x + self.n_right + 50, word_y + self.down_size[1] - 4), t)
        return word_y + self.down_size[1]

    def _draw_skeleton(self, surf, feet, t):
        """The game's own skeleton sprite, big, leaning on the N and swaying a little."""
        self.skeleton.anim_t = t * 0.35
        canvas = pygame.Surface((140, 200), pygame.SRCALPHA)
        with origin_at((70, 170)):
            DRAWERS["skeleton"](canvas, self.skeleton, 0, t, False)
        big = pygame.transform.scale(canvas, (int(140 * SKELETON_SCALE), int(200 * SKELETON_SCALE)))
        surf.blit(big, (feet[0] - 70 * SKELETON_SCALE, feet[1] - 170 * SKELETON_SCALE))
