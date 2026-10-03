"""Drawing the isometric dig site, and mapping the mouse back onto blocks."""
import random
import time

import pygame

from .blocks import BLOCKS
from .config import GRID, W
from .iso import cube_faces, draw_cube, iso, point_in_poly
from .sprites import draw_enemy, draw_miner
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


def draw_board(surf, world, fonts, hover=None, hover_enemy=None):
    w = world
    t = time.time()
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
    miner_key = {}
    for m in w.miners:
        miner_key[id(m)] = m.x + m.y - 0.5
        items.append((miner_key[id(m)], 2, "miner", m))
    for e in w.enemies:
        if e.kind == "spider" and e.state == "attacking" and e.victim:
            items.append((miner_key[id(e.victim)], 3, "enemy", e))   # drawn on top of its victim
        else:
            items.append((e.x + e.y - 0.5, 2, "enemy", e))
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
        elif kind == "miner":
            draw_miner(surf, fonts, data, r, t)
        else:
            draw_enemy(surf, data, r, t, hovered=data is hover_enemy)

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
