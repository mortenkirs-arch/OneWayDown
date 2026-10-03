"""Drawing the isometric dig site, and mapping the mouse back onto blocks."""
import math
import random
import time

import pygame

from .blocks import BLOCKS
from .config import GRID, TILE_H, TILE_W, W
from .dynamite import EXPLOSION_SECS
from .enemies import BOSS_SLAM_RADIUS, CURSE_RADIUS, CURSE_SECS, RALLY_RADIUS
from .effects import CRIT_BURST_SECS, QUAKE_RADIUS, QUAKE_SPEED
from .iso import cube_faces, draw_cube, iso, point_in_poly
from .sprites import draw_bomb, draw_enemy, draw_miner, enemy_anchor
from .world_layout import BALLISTA_POS, BOLT_SECS, CHEST_FX_SECS, SPIKE_FX_SECS, WHETSTONE_POS
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
    if w.lv("whetstone"):
        items.append((WHETSTONE_POS[0] + WHETSTONE_POS[1] - 0.4, 2, "whetstone", None))
    if w.lv("ballista"):
        items.append((BALLISTA_POS[0] + BALLISTA_POS[1] - 0.4, 2, "ballista", None))
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
                if b.artifact:
                    draw_artifact_glint(surf, faces, t, x, y)
                if w.golden and w.golden[0] == (x, y):
                    draw_golden_block(surf, faces, w.golden[1], t)
                if hover and hover[0] == (x, y):
                    for name, poly in faces.items():
                        pygame.draw.polygon(surf, (255, 255, 255), poly, 3 if name == hover[1] else 1)
        elif kind == "miner":   # rides the quake heave with the block underfoot
            draw_miner(surf, fonts, data, r + quake_lift(w, data.x, data.y), t, w.lv("diamond"),
                       spirit=w.lv("spiritlantern") > 0)
        elif kind == "bomb":
            draw_bomb(surf, data, w, t)
        elif kind == "whetstone":
            busy = any(m.task == "sharpening" for m in w.miners)
            draw_whetstone(surf, _anchor(w, WHETSTONE_POS), t, busy)
        elif kind == "ballista":
            draw_ballista(surf, _anchor(w, BALLISTA_POS), w.ballista_aim, w.ballista_timer, t)
        else:
            draw_enemy(surf, data, r, t, hovered=data is hover_enemy)

    draw_blast_zones(surf, w, t)
    draw_webs(surf, w)
    draw_slam_zones(surf, w, t)
    draw_boss_auras(surf, w, t)
    draw_curses(surf, w, t)
    draw_quake_waves(surf, w)
    draw_crit_bursts(surf, w)
    draw_spike_traps(surf, w)
    draw_bolts(surf, w, t)
    draw_chests(surf, w)
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


def _anchor(world, pos):
    """Screen position of the ground at a fixed grid spot (whetstone, ballista)."""
    x, y = pos
    return iso(x, y, world.column_height(*world.cell_of(x, y)) + world.rise)


def draw_golden_block(surf, faces, left, t):
    """A block turned to gold: shimmering top, gold outline, sparkles; blinks as time runs out."""
    if left < 1.5 and int(t * 10) % 2:   # about to fade: blink
        return
    top = faces["top"]
    xs, ys = [p[0] for p in top], [p[1] for p in top]
    box = pygame.Rect(min(xs) - 2, min(ys) - 2, max(xs) - min(xs) + 4, max(ys) - min(ys) + 4)
    layer = pygame.Surface(box.size, pygame.SRCALPHA)
    local = [(px - box.x, py - box.y) for px, py in top]
    shimmer = 0.6 + 0.4 * math.sin(t * 8)
    pygame.draw.polygon(layer, (255, 210, 60, int(170 * shimmer)), local)
    surf.blit(layer, box)
    for name in ("top", "left", "right"):
        pygame.draw.polygon(surf, (255, 225, 90), faces[name], 2)
    rng = random.Random(int(t * 6))
    for _ in range(4):   # twinkles
        sx, sy = rng.uniform(box.left + 6, box.right - 6), rng.uniform(box.top, box.bottom + 10)
        pygame.draw.line(surf, (255, 255, 230), (sx - 3, sy), (sx + 3, sy), 1)
        pygame.draw.line(surf, (255, 255, 230), (sx, sy - 3), (sx, sy + 3), 1)


def draw_artifact_glint(surf, faces, t, x, y):
    """A block hiding an artifact: a slow violet shimmer and a star that winks on its top face."""
    top = faces["top"]
    cx = sum(p[0] for p in top) / 4
    cy = sum(p[1] for p in top) / 4
    phase = t * 2.2 + x * 1.7 + y * 0.9
    pulse = 0.5 + 0.5 * math.sin(phase)
    pygame.draw.polygon(surf, (200, 150, 255), top, 1 + int(pulse * 2))
    if math.sin(phase * 0.5) > 0.2:   # the star winks on and off
        r = 3 + 4 * pulse
        sx, sy = cx + 8 * math.sin(phase * 0.3), cy - 2
        pygame.draw.line(surf, (255, 245, 255), (sx - r, sy), (sx + r, sy), 2)
        pygame.draw.line(surf, (255, 245, 255), (sx, sy - r), (sx, sy + r), 2)
        pygame.draw.circle(surf, (230, 200, 255), (int(sx), int(sy)), 2)


def _ground_ellipse(world, x, y, radius, z=None):
    """Screen rect of a circle of `radius` tiles on the ground around grid point (x, y)."""
    z = world.column_height(*world.cell_of(x, y)) if z is None else z
    cx, cy = iso(x, y, z + world.rise)
    rect = pygame.Rect(0, 0, radius * TILE_W * 1.42, radius * TILE_H * 1.42)
    rect.center = (cx, cy)
    return rect


def draw_webs(surf, world):
    """Broodmother: sticky webs on the ground her slams hit; they fade as they wear off."""
    if not world.webs:
        return
    overlay = pygame.Surface(surf.get_size(), pygame.SRCALPHA)
    for (x, y), left in world.webs.items():
        a = int(150 * min(1.0, left / 1.5))
        z = world.column_height(x, y) + world.rise
        c = iso(x + 0.5, y + 0.5, z)
        corners = [iso(x + u, y + v, z) for u, v in ((0.1, 0.1), (0.9, 0.1), (0.9, 0.9), (0.1, 0.9))]
        mids = [iso(x + u, y + v, z) for u, v in ((0.5, 0.08), (0.92, 0.5), (0.5, 0.92), (0.08, 0.5))]
        for p in corners + mids:   # spokes
            pygame.draw.line(overlay, (235, 235, 245, a), c, p, 1)
        for k in (0.35, 0.7):      # rings
            ring = [(c[0] + (p[0] - c[0]) * k, c[1] + (p[1] - c[1]) * k)
                    for pair in zip(corners, mids) for p in pair]
            pygame.draw.polygon(overlay, (235, 235, 245, a), ring, 1)
    surf.blit(overlay, (0, 0))


def draw_boss_auras(surf, world, t):
    """Zombie King: a sickly green ring of command, and a glow under every zombie he has rallied.
    Lich: violet threads from each wisp shielding him, and the shield itself."""
    boss = world.boss()
    if not boss or boss.state == "emerging":
        return
    overlay = pygame.Surface(surf.get_size(), pygame.SRCALPHA)
    pulse = 0.5 + 0.5 * math.sin(t * 3)
    if boss.kind == "zombieking":
        pygame.draw.ellipse(overlay, (120, 200, 80, int(40 + 30 * pulse)), _ground_ellipse(world, boss.x, boss.y,
                                                                                       RALLY_RADIUS), 3)
        for e in world.enemies:
            if getattr(e, "rallied", False):
                pygame.draw.ellipse(overlay, (140, 230, 90, 150), _ground_ellipse(world, e.x, e.y, 0.45, e.draw_z), 3)
    elif boss.kind == "lich":
        bx, by = enemy_anchor(boss, world.rise, t)
        wisps = world.shield_wisps()
        for e in wisps:
            ex, ey = enemy_anchor(e, world.rise, t)
            pygame.draw.line(overlay, (190, 140, 255, int(110 + 80 * pulse)), (ex, ey), (bx, by), 2)
        if wisps:   # (centred on his body, a little above the click anchor)
            r = int(56 + 4 * pulse)
            pygame.draw.circle(overlay, (170, 120, 255, 45), (int(bx), int(by - 30)), r)
            pygame.draw.circle(overlay, (210, 170, 255, 170), (int(bx), int(by - 30)), r, 2)
    surf.blit(overlay, (0, 0))


def draw_curses(surf, world, t):
    """Lich: a violet sigil over each cursed crew member, its ring running down to the burst,
    and the area the burst will hit."""
    cursed = [m for m in world.miners if m.curse > 0 and m.state != "down"]
    if not cursed:
        return
    overlay = pygame.Surface(surf.get_size(), pygame.SRCALPHA)
    for m in cursed:
        urgency = 1 - m.curse / CURSE_SECS
        pulse = 0.5 + 0.5 * math.sin(t * (6 + 18 * urgency))
        pygame.draw.ellipse(overlay, (170, 100, 255, int(30 + 60 * pulse * urgency)),
                            _ground_ellipse(world, m.x, m.y, CURSE_RADIUS, m.draw_z))
        x, y = world.entity_screen(m, 70 + m.height)
        pygame.draw.circle(overlay, (60, 20, 90, 200), (int(x), int(y)), 13)
        pygame.draw.arc(overlay, (230, 200, 255, 255), (x - 15, y - 15, 30, 30), math.pi / 2,
                        math.pi / 2 + math.tau * (m.curse / CURSE_SECS), 3)
        for k in range(3):   # a little three-pointed sigil
            a = t * 2 + k * math.tau / 3
            pygame.draw.line(overlay, (220, 170, 255, 255), (x, y), (x + math.cos(a) * 8, y + math.sin(a) * 8), 2)
        hx, hy = world.entity_screen(m, 30)   # a pulsing ring around the miner: click here
        pygame.draw.circle(overlay, (220, 170, 255, int(120 + 120 * pulse)), (int(hx), int(hy)), 22, 2)
    surf.blit(overlay, (0, 0))


def draw_slam_zones(surf, world, t):
    """A boss winding up: the ground it is about to cave in glows red, filling in as the slam nears."""
    winding = [e for e in world.enemies if e.boss and e.windup > 0]
    if not winding:
        return
    overlay = pygame.Surface(surf.get_size(), pygame.SRCALPHA)
    for e in winding:
        cx, cy = iso(e.x, e.y, e.draw_z + world.rise)
        full = pygame.Rect(0, 0, BOSS_SLAM_RADIUS * TILE_W * 1.42, BOSS_SLAM_RADIUS * TILE_H * 1.42)
        full.center = (cx, cy)
        q = 1 - e.windup / e.windup_total
        pulse = 0.5 + 0.5 * math.sin(t * (10 + 20 * q))
        pygame.draw.ellipse(overlay, (255, 40, 30, int(40 + 50 * pulse)), full)
        inner = full.inflate(-full.w * (1 - q), -full.h * (1 - q))
        pygame.draw.ellipse(overlay, (255, 80, 50, 120), inner)
        pygame.draw.ellipse(overlay, (255, 150, 110, 230), full, 3)
    surf.blit(overlay, (0, 0))


def draw_whetstone(surf, base, t, busy):
    """A grinding wheel on a little wooden frame; spins fast while someone sharpens."""
    x, y = int(base[0]), int(base[1])
    pygame.draw.ellipse(surf, (16, 12, 20), (x - 14, y - 4, 28, 8))
    for dx in (-9, 9):   # A-frame legs
        pygame.draw.line(surf, (120, 82, 44), (x + dx, y), (x, y - 20), 3)
    pygame.draw.rect(surf, (90, 60, 34), (x - 11, y - 4, 22, 4))   # water trough
    cx, cy = x, y - 20
    pygame.draw.circle(surf, (150, 150, 160), (cx, cy), 10)
    pygame.draw.circle(surf, (100, 100, 112), (cx, cy), 10, 2)
    spin = t * (18 if busy else 2)
    for k in range(3):   # spokes show the spin
        a = spin + k * math.tau / 3
        pygame.draw.line(surf, (110, 110, 120), (cx, cy), (cx + math.cos(a) * 8, cy + math.sin(a) * 8), 2)
    pygame.draw.circle(surf, (120, 82, 44), (cx, cy), 2)
    pygame.draw.line(surf, (120, 82, 44), (cx + 10, cy), (cx + 16, cy - 6), 2)   # crank handle


def draw_ballista(surf, base, aim, timer, t):
    """A crossbow turret on a wooden stand, swivelling to face its target."""
    x, y = int(base[0]), int(base[1])
    pygame.draw.ellipse(surf, (16, 12, 20), (x - 16, y - 5, 32, 10))
    pygame.draw.rect(surf, (110, 74, 40), (x - 10, y - 10, 20, 10), border_radius=2)   # stand
    pygame.draw.line(surf, (90, 60, 34), (x, y - 10), (x, y - 18), 4)                 # post
    px, py = x, y - 18
    dx, dy = math.cos(aim), math.sin(aim) * 0.6       # flattened a little for the iso view
    norm = math.hypot(dx, dy) or 1.0
    dx, dy = dx / norm, dy / norm
    nx, ny = -dy, dx
    front, back = (px + dx * 14, py + dy * 14), (px - dx * 10, py - dy * 10)
    pygame.draw.line(surf, (130, 90, 50), back, front, 4)                              # stock
    tips = [(front[0] - dx * 4 + nx * 12, front[1] - dy * 4 + ny * 12),
            (front[0] - dx * 4 - nx * 12, front[1] - dy * 4 - ny * 12)]
    pygame.draw.lines(surf, (150, 110, 60), False, [tips[0], front, tips[1]], 3)       # bow
    draw_back = (px - dx * 3, py - dy * 3) if timer > 0.3 else front                   # string pulled back
    pygame.draw.lines(surf, (230, 230, 230), False, [tips[0], draw_back, tips[1]], 1)
    if timer > 0.3:   # a bolt loaded and ready
        pygame.draw.line(surf, (200, 200, 210), draw_back, (front[0] + dx * 6, front[1] + dy * 6), 2)


def draw_bolts(surf, world, t):
    for (sx, sy), enemy, age in world.bolts:
        q = min(1.0, age / BOLT_SECS)
        tx, ty = enemy_anchor(enemy, world.rise, t)
        x, y = sx + (tx - sx) * q, sy + (ty - sy) * q - math.sin(q * math.pi) * 20
        dx, dy = tx - sx, ty - sy
        norm = math.hypot(dx, dy) or 1.0
        tail = (x - dx / norm * 14, y - dy / norm * 14)
        pygame.draw.line(surf, (140, 100, 60), tail, (x, y), 2)
        pygame.draw.circle(surf, (210, 210, 220), (int(x), int(y)), 2)


def draw_spike_traps(surf, world):
    """Booby Traps: a ring of spikes punching up out of the ground and sinking back."""
    for cell, age in world.spike_fx:
        h = math.sin(min(1.0, age / SPIKE_FX_SECS) * math.pi) * 16
        z = world.column_height(*cell) + world.rise
        for k in range(6):
            a = k / 6 * math.tau
            bx, by = iso(cell[0] + 0.5 + math.cos(a) * 0.3, cell[1] + 0.5 + math.sin(a) * 0.3, z)
            pygame.draw.polygon(surf, (170, 170, 185), [(bx - 3, by), (bx + 3, by), (bx, by - h)])
            pygame.draw.line(surf, (230, 230, 240), (bx, by), (bx, by - h), 1)


def draw_chests(surf, world):
    """Buried Treasure: a chest pops out of the broken block, the lid flies open, light pours out."""
    for x, y, age in world.chest_fx:
        p = age / CHEST_FX_SECS
        cx, cy = int(x), int(y - 10 - 14 * min(1.0, p * 3))
        fade = 1 - max(0.0, (p - 0.6) / 0.4)
        if p > 0.15:   # rays of light
            for k in range(7):
                a = -math.pi / 2 + (k - 3) * 0.32
                ln = 26 * min(1.0, (p - 0.15) * 3)
                end = (cx + math.cos(a) * ln, cy - 6 + math.sin(a) * ln)
                pygame.draw.line(surf, _scale_col((255, 230, 120), fade), (cx, cy - 6), end, 2)
        pygame.draw.rect(surf, _scale_col((140, 90, 40), fade), (cx - 10, cy - 6, 20, 12), border_radius=2)
        pygame.draw.rect(surf, _scale_col((255, 205, 70), fade), (cx - 10, cy - 2, 20, 3))
        open_ = min(1.0, p * 4) * 1.9   # lid swings back on its hinge
        hx, hy = cx - 10, cy - 6
        lid = [(hx, hy), (hx + 20 * math.cos(open_), hy - 20 * math.sin(open_)),
               (hx + 20 * math.cos(open_) - 5 * math.sin(open_), hy - 20 * math.sin(open_) - 5 * math.cos(open_)),
               (hx - 5 * math.sin(open_), hy - 5 * math.cos(open_))]
        pygame.draw.polygon(surf, _scale_col((160, 105, 50), fade), lid)


def _scale_col(color, f):
    return tuple(int(c * f) for c in color)


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
