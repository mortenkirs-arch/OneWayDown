"""Drawing the isometric dig site, and mapping the mouse back onto blocks."""
import math
import random
import time

import pygame

from .blocks import BLOCKS
from .config import BAD, GOOD, GRID, W
from .iso import cube_faces, draw_cube, iso, point_in_poly
from .util import shade

_slab_fade = None


def _get_slab_fade():
    global _slab_fade
    if _slab_fade is None:
        _slab_fade = pygame.Surface((W, 160), pygame.SRCALPHA)
        for i in range(160):
            _slab_fade.fill((10, 8, 16, int(255 * i / 160)), (0, i, W, 1))
    return _slab_fade


def pick_block(world, pos):
    """Front-most block (and which face) under a screen point - top, left or right side."""
    z = 2 + world.rise
    for cell in sorted(world.current, key=lambda c: c[0] + c[1], reverse=True):
        for face, poly in cube_faces(cell[0], cell[1], z).items():
            if point_in_poly(pos, poly):
                return cell, face
    return None


def draw_board(surf, world, fonts, hover=None):
    w = world
    r = w.rise
    # Earth slab under the board
    bottom = -3 + r
    top0 = 0 + r
    left_face = [iso(0, GRID, top0), iso(GRID, GRID, top0), iso(GRID, GRID, bottom), iso(0, GRID, bottom)]
    right_face = [iso(GRID, 0, top0), iso(GRID, GRID, top0), iso(GRID, GRID, bottom), iso(GRID, 0, bottom)]
    earth = (74, 56, 46) if w.depth < 4 else (70, 68, 78)
    pygame.draw.polygon(surf, shade(earth, 0.7), left_face)
    pygame.draw.polygon(surf, shade(earth, 0.5), right_face)
    for i in range(1, 3):
        z = top0 - i
        pygame.draw.line(surf, shade(earth, 0.4), iso(0, GRID, z), iso(GRID, GRID, z), 2)
        pygame.draw.line(surf, shade(earth, 0.33), iso(GRID, 0, z), iso(GRID, GRID, z), 2)
    surf.blit(_get_slab_fade(), (0, iso(GRID, GRID, bottom)[1] - 150))

    # Drawables sorted back-to-front: blocks of both layers + miners
    items = []
    for (x, y), b in w.next.items():
        items.append((x + y, 0, "block", (x, y, 1 + r, b, 1)))
    for (x, y), b in w.current.items():
        items.append((x + y, 1, "block", (x, y, 2 + r, b, 0)))
    for m in w.miners:
        items.append((m.x + m.y - 0.5, 2, "miner", m))
    items.sort(key=lambda t: (t[0], t[1]))

    for _, _, kind, data in items:
        if kind == "block":
            x, y, z, b, layer = data
            spec = BLOCKS[b.kind]
            color = spec["color"]
            if layer == 1:
                color = shade(color, 0.7)
            faces = draw_cube(surf, x, y, z, color, spec.get("fleck"),
                              seed=hash((x, y, w.depth + layer)))
            if layer == 0:
                draw_damage(surf, b, x, y, z)
                if hover and hover[0] == (x, y):
                    for name, poly in faces.items():
                        pygame.draw.polygon(surf, (255, 255, 255), poly, 3 if name == hover[1] else 1)
        else:
            draw_miner(surf, data, r)

    for rx, ry, age, max_r, color in w.rings:
        t = age / 0.4
        rad = max(2, int(max_r * t))
        pygame.draw.ellipse(surf, color, (rx - rad, ry - rad / 2, rad * 2, rad), max(1, int(4 * (1 - t))))
    for p in w.particles:
        pygame.draw.rect(surf, p.color, (int(p.x), int(p.y), p.size, p.size))
    for f in w.floaters:
        img = fonts[f.size].render(f.text, True, f.color)
        img.set_alpha(int(255 * min(1, f.life / f.max_life * 2)))
        surf.blit(img, img.get_rect(center=(f.x, f.y)))


def draw_damage(surf, b, x, y, z):
    frac = 1 - b.hp / b.max_hp
    if frac <= 0:
        return
    rng = random.Random(hash((x, y)))
    cracks = int(frac * 6) + 1
    for _ in range(cracks):
        u, v = rng.uniform(0.25, 0.75), rng.uniform(0.25, 0.75)
        p0 = iso(x + u, y + v, z)
        pts = [p0]
        for _ in range(3):
            u += rng.uniform(-0.18, 0.18)
            v += rng.uniform(-0.18, 0.18)
            pts.append(iso(x + max(0.05, min(0.95, u)), y + max(0.05, min(0.95, v)), z))
        pygame.draw.lines(surf, (30, 24, 28), False, pts, 2)
    # health bar
    cx, cy = iso(x + 0.5, y + 0.5, z)
    bar = pygame.Rect(0, 0, 40, 6)
    bar.center = (cx, cy - 24)
    pygame.draw.rect(surf, (20, 16, 24), bar.inflate(2, 2))
    pygame.draw.rect(surf, GOOD if frac < 0.6 else BAD, (bar.x, bar.y, int(bar.w * (1 - frac)), bar.h))


def draw_miner(surf, m, rise):
    fx, fy = iso(m.x, m.y, m.draw_z + rise)
    fx, fy = int(fx), int(fy)
    pygame.draw.ellipse(surf, (16, 12, 20), (fx - 11, fy - 4, 22, 8))
    bob = abs(math.sin(time.time() * 10)) * 2 if m.anim == 0 else 0
    body = pygame.Rect(fx - 7, fy - 26 - bob, 14, 18)
    pygame.draw.rect(surf, m.hue, body, border_radius=4)
    pygame.draw.rect(surf, (60, 50, 40), (fx - 7, fy - 10 - bob, 14, 8), border_radius=2)
    head = (fx, int(fy - 32 - bob))
    pygame.draw.circle(surf, (238, 196, 160), head, 7)
    pygame.draw.ellipse(surf, (240, 200, 40), (head[0] - 9, head[1] - 10, 18, 9))
    pygame.draw.circle(surf, (255, 250, 200), (head[0] + 5 * m.facing, head[1] - 6), 2)
    # pickaxe swing
    ang = (-0.5 + m.anim * 2.5) * m.facing
    hx, hy = fx + 7 * m.facing, fy - 20 - bob
    ex, ey = hx + math.sin(ang) * 18, hy - math.cos(ang) * 18
    pygame.draw.line(surf, (120, 82, 44), (hx, hy), (ex, ey), 3)
    perp = (math.cos(ang) * 8, math.sin(ang) * 8)
    pygame.draw.line(surf, (190, 190, 200), (ex - perp[0], ey - perp[1]), (ex + perp[0], ey + perp[1]), 3)
