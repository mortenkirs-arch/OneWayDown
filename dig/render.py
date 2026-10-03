"""Drawing the isometric dig site, and mapping the mouse back onto blocks."""
import math
import random
import time

import pygame

from .blocks import BLOCKS
from .config import GRID, TILE_H, TILE_W, W
from .dynamite import EXPLOSION_SECS
from .effects import CRIT_BURST_SECS, QUAKE_RADIUS, QUAKE_SPEED
from .iso import cube_faces, draw_cube, iso, point_in_poly
from .sprites import draw_bomb, draw_enemy, draw_miner
from .ui import COIN, COIN_EDGE, COIN_SHINE, gold_label
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
        items.append((x + y, 1, "block", (x, y, 2 + r + quake_lift(w, x + 0.5, y + 0.5), b, 0)))
    miner_key = {}
    for m in w.miners:
        miner_key[id(m)] = m.x + m.y - 0.5
        items.append((miner_key[id(m)], 2, "miner", m))
    for e in w.enemies:
        if e.state == "attacking" and e.victim and e.spec["grab"] in ("head", "neck", "orbit", "engulf"):
            items.append((miner_key[id(e.victim)], 3, "enemy", e))   # clinging on: drawn over its victim
        elif (e.state == "transforming" or (e.flying and e.state != "attacking")
              or (e.state == "emerging" and e.spec["entrance"] in ("drop", "swoop"))):
            items.append((math.inf, 4, "enemy", e))                  # in the air: above everything
        else:
            items.append((e.x + e.y - 0.5, 2, "enemy", e))
    for b in w.bombs:   # on its block once landed; above everything while flying in
        items.append((b.cell[0] + b.cell[1] + 0.5, 2, "bomb", b) if b.landed else (math.inf, 5, "bomb", b))
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
        elif kind == "miner":   # rides the quake heave with the block underfoot
            draw_miner(surf, fonts, data, r + quake_lift(w, data.x, data.y), t, w.lv("diamond"))
        elif kind == "bomb":
            draw_bomb(surf, data, w, t)
        else:
            draw_enemy(surf, data, r, t, hovered=data is hover_enemy)

    draw_blast_zones(surf, w, t)
    draw_quake_waves(surf, w)
    draw_crit_bursts(surf, w)
    for rx, ry, age, max_r, color in w.rings:
        q = age / 0.4
        rad = max(2, int(max_r * q))
        pygame.draw.ellipse(surf, color, (rx - rad, ry - rad / 2, rad * 2, rad), max(1, int(4 * (1 - q))))
    draw_explosions(surf, w)
    for p in w.particles:
        pygame.draw.rect(surf, p.color, (int(p.x), int(p.y), p.size, p.size))
    draw_smoke(surf, w)
    if w.flash > 0:   # white flash the instant dynamite goes off
        flash = pygame.Surface(surf.get_size(), pygame.SRCALPHA)
        flash.fill((255, 245, 225, int(150 * w.flash / 0.12)))
        surf.blit(flash, (0, 0))
    for f in w.floaters:
        if f.coin:
            img = gold_label(fonts, f.text, f.size, f.color)
        else:
            img = fonts[f.size].render(f.text, True, f.color)
        img.set_alpha(int(255 * min(1, f.life / f.max_life * 2)))
        surf.blit(img, img.get_rect(center=(f.x, f.y)))


def draw_flying_coins(surf, coins):
    """Coins in mid-air (earned coins heading for the counter, or spent ones heading for an upgrade)."""
    for c in coins:
        if c.t < 0:
            continue
        x, y = c.pos()
        squash = abs(math.cos(c.t * 14))          # spinning: the coin flips edge-on and back
        r = c.size
        rect = pygame.Rect(0, 0, max(2, int(2 * r * squash)), 2 * r)
        rect.center = (int(x), int(y))
        pygame.draw.ellipse(surf, COIN_EDGE, rect.move(0, 1))
        pygame.draw.ellipse(surf, COIN, rect)
        if squash > 0.5:
            pygame.draw.circle(surf, COIN_SHINE, (rect.centerx - 1, rect.centery - 2), max(1, r // 3))


def quake_lift(world, x, y):
    """How far (in blocks) a Seismic Strikes wave is heaving the ground at grid point (x, y) right now.
    The wave front rolls outward; ground it passes pops up and settles, strongest near the epicentre."""
    lift = 0.0
    for qx, qy, age, _ in world.quakes:
        d = math.hypot(x - qx, y - qy)
        if d > QUAKE_RADIUS:
            continue
        behind = age * QUAKE_SPEED - d          # how far the front has travelled past this point
        if 0 <= behind < 1.2:
            strength = (1 - d / QUAKE_RADIUS) ** 0.7
            lift += math.sin(behind / 1.2 * math.pi) * 0.3 * strength
    return lift


def draw_quake_waves(surf, world):
    """Dusty rings spreading across the board from each Seismic Strikes crit."""
    if not world.quakes:
        return
    overlay = pygame.Surface(surf.get_size(), pygame.SRCALPHA)
    for qx, qy, age, _ in world.quakes:
        cx, cy = iso(qx, qy, 2 + world.rise)
        for lag, width in ((0.0, 5), (0.45, 3)):   # leading ring and a fainter one behind it
            rad = age * QUAKE_SPEED - lag
            if not 0 < rad <= QUAKE_RADIUS:
                continue
            fade = 1 - rad / QUAKE_RADIUS
            rect = pygame.Rect(0, 0, rad * TILE_W * 1.42, rad * TILE_H * 1.42)   # a circle on the iso ground
            rect.center = (cx, cy)
            pygame.draw.ellipse(overlay, (215, 180, 130, int(200 * fade)), rect, width)
    surf.blit(overlay, (0, 0))


def draw_crit_bursts(surf, world):
    """Star-shaped flash where a critical strike lands."""
    for x, y, age in world.crit_bursts:
        p = age / CRIT_BURST_SECS
        outer, inner = 10 + 34 * p, 4 + 9 * p
        size = int(outer * 2 + 4)
        star = pygame.Surface((size, size), pygame.SRCALPHA)
        c = size / 2
        pts = []
        for i in range(16):
            r = outer if i % 2 == 0 else inner
            a = i / 16 * math.tau + p * 0.6
            pts.append((c + math.cos(a) * r, c + math.sin(a) * r * 0.75))
        pygame.draw.polygon(star, (255, 170, 70, int(220 * (1 - p))), pts)
        pygame.draw.circle(star, (255, 255, 235, int(255 * (1 - p))), (c, c), max(2, int(inner * 1.2)))
        surf.blit(star, (x - c, y - c))


def draw_blast_zones(surf, world, t):
    """Pulsing red danger area under every lit bundle of dynamite; pulses faster as the fuse shortens."""
    lit = [b for b in world.bombs if b.landed]
    if not lit:
        return
    overlay = pygame.Surface(surf.get_size(), pygame.SRCALPHA)
    for b in lit:
        urgency = 1 - b.fuse_left()
        pulse = 0.5 + 0.5 * math.sin(t * (7 + 22 * urgency))
        fill = (255, 50, 30, int(35 + 70 * pulse * (0.4 + 0.6 * urgency)))
        edge = (255, 120, 70, int(140 + 100 * pulse))
        cx, cy = b.cell
        for dx in range(-b.radius, b.radius + 1):
            for dy in range(-b.radius, b.radius + 1):
                x, y = cx + dx, cy + dy
                if 0 <= x < GRID and 0 <= y < GRID:
                    top = cube_faces(x, y, world.column_height(x, y) + world.rise)["top"]
                    pygame.draw.polygon(overlay, fill, top)
                    pygame.draw.polygon(overlay, edge, top, 1)
    surf.blit(overlay, (0, 0))


def draw_explosions(surf, world):
    """Fireball: white-hot core that blooms out into orange and red, then fades."""
    for x, y, age, size in world.explosions:
        p = age / EXPLOSION_SECS
        grow = 1 - (1 - p) ** 2
        fade = 1 - p
        rad = size * (0.35 + 0.9 * grow)
        dim = int(rad * 2.6)
        ball = pygame.Surface((dim, dim), pygame.SRCALPHA)
        c = dim // 2
        for scale, color, alpha in ((1.15, (170, 50, 30), 90), (1.0, (255, 120, 40), 180),
                                    (0.8, (255, 200, 80), 220), (0.55, (255, 245, 210), 255)):
            pygame.draw.circle(ball, (*color, int(alpha * fade)), (c, c), int(rad * scale))
        if p < 0.15:   # blinding core for the first instant
            pygame.draw.circle(ball, (255, 255, 255, int(255 * (1 - p / 0.15))), (c, c), int(rad * 0.75))
        surf.blit(ball, (x - c, y - c * 0.85))


def draw_smoke(surf, world):
    for s in world.smoke:
        r = max(1, int(s.r))
        puff = pygame.Surface((r * 2, r * 2), pygame.SRCALPHA)
        alpha = int(150 * s.life / s.max_life)
        pygame.draw.circle(puff, (s.shade, s.shade - 6, s.shade - 10, alpha), (r, r), r)
        surf.blit(puff, (s.x - r, s.y - r))


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
