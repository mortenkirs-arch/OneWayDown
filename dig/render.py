"""Drawing the isometric dig site, and mapping the mouse back onto blocks."""
import math
import random
import time

import pygame

from .biomes import biome_at, block_color
from .blocks import BLOCKS
from .config import GRID, TILE_H, TILE_W, W
from .dynamite import EXPLOSION_SECS
from .enemies import (BONE_THROW_SECS, BOSS_SLAM_RADIUS, BRO_SURFACE_RADIUS, CURSE_RADIUS, CURSE_SECS, RALLY_RADIUS,
                      SHADE_RADIUS, VOID_INHALE_RADIUS, VOID_INHALE_SECS)
from .effects import CRIT_BURST_SECS, QUAKE_SPEED
from .icons import draw_icon
from .iso import cube_faces, draw_cube, iso, point_in_poly
from .sprites import draw_bone, draw_bomb, draw_enemy, draw_ghost, draw_miner, enemy_anchor
from .world_layout import (BALLISTA_POS, BOILER_POS, BOLT_SECS, CHEST_FX_SECS, ROCK_SECS, SPIKE_FX_SECS,
                           STEAM_SECS, WHETSTONE_POS)
from .ui import COIN, COIN_EDGE, COIN_SHINE, gold_label
from .upgrades import PHANTOM_WINDUP
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
    hover_boiler = pick_boiler(w, pygame.mouse.get_pos())
    r = w.rise
    # Earth slab under the board: the layers below the two shown block by block, each in its own biome's earth
    bottom = -3 + r
    top0 = 0 + r
    for i in range(3):
        depth = w.depth + 2 + i
        earth = (74, 56, 46) if depth < 4 else biome_at(depth)["earth"]   # (brown while the topsoil is dirt)
        hi, lo = top0 - i, top0 - i - 1
        pygame.draw.polygon(surf, shade(earth, 0.7), [iso(0, GRID, hi), iso(GRID, GRID, hi), iso(GRID, GRID, lo),
                                                      iso(0, GRID, lo)])
        pygame.draw.polygon(surf, shade(earth, 0.5), [iso(GRID, 0, hi), iso(GRID, GRID, hi), iso(GRID, GRID, lo),
                                                      iso(GRID, 0, lo)])
        if i:   # the seam between this layer and the one above
            pygame.draw.line(surf, shade(earth, 0.4), iso(0, GRID, hi), iso(GRID, GRID, hi), 2)
            pygame.draw.line(surf, shade(earth, 0.33), iso(GRID, 0, hi), iso(GRID, GRID, hi), 2)
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
    for g in w.ghosts:   # (Graveyard Shift)
        items.append((g.x + g.y - 0.5, 2, "ghost", g))
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
    if w.lv("boiler"):
        items.append((BOILER_POS[0] + BOILER_POS[1] - 0.4, 2, "boiler", None))
    items.sort(key=lambda t: (t[0], t[1]))

    for _, _, kind, data in items:
        if kind == "block":
            x, y, z, b, layer = data
            spec = BLOCKS[b.kind]
            color = block_color(b.kind, w.depth + layer)
            if layer == 1:
                color = shade(color, 0.7)
            faces = draw_cube(surf, x, y, z, color, spec.get("fleck"),
                              seed=hash((x, y, w.depth + layer)))
            # biome details and bones on both layers (the one below dimmer), seeded by the block's own layer
            dim = NEXT_DIM if layer else 1.0
            deco = biome_at(w.depth + layer)["deco"]
            if deco:
                draw_block_deco(surf, deco, faces, x, y, w.depth + layer, t, dim)
            if b.bones:
                draw_bones(surf, faces, x, y, w.depth + layer, dim)
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
        elif kind == "ghost":
            draw_ghost(surf, fonts, data, r + quake_lift(w, data.x, data.y), t, w.lv("diamond"))
        elif kind == "bomb":
            draw_bomb(surf, data, w, t)
        elif kind == "whetstone":
            busy = any(m.task == "sharpening" for m in w.miners)
            draw_whetstone(surf, _anchor(w, WHETSTONE_POS), t, busy)
        elif kind == "ballista":
            draw_ballista(surf, _anchor(w, BALLISTA_POS), w.ballista_aim, w.ballista_timer, t)
        elif kind == "boiler":
            draw_boiler(surf, _anchor(w, BOILER_POS), w.boiler, t, hover_boiler)
        else:
            draw_enemy(surf, data, r, t, hovered=data is hover_enemy)

    draw_blast_zones(surf, w, t)
    draw_webs(surf, w)
    draw_slam_zones(surf, w, t)
    draw_phantom(surf, w, t)
    draw_steam(surf, w, t)
    draw_boss_auras(surf, w, t)
    draw_shade_auras(surf, w, t)
    draw_bro_mound(surf, w, t)
    draw_curses(surf, w, t)
    draw_void_inhale(surf, w, t)
    draw_stuns(surf, w, t)
    draw_bone_throws(surf, w, t)
    draw_quake_waves(surf, w)
    draw_crit_bursts(surf, w)
    draw_spike_traps(surf, w)
    draw_bolts(surf, w, t)
    draw_rocks(surf, w, t)
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


LAVA_SHARE = 0.6   # magma blocks with lava showing (other biomes' details: about a third)
SIDE_SHARE = 0.5   # chance each side face of a decorated block shows some of it too
NEXT_DIM = 0.7     # the layer below is drawn this much darker (its details too; lava glows through a bit more)


def face_point(face):
    """(u, v) across a face -> screen: u along its first edge, v along its last. For the sides, that's along the
    top edge and down the face."""
    o = face[0]
    ax, ay = face[1][0] - o[0], face[1][1] - o[1]
    bx, by = face[3][0] - o[0], face[3][1] - o[1]
    return lambda u, v: (o[0] + ax * u + bx * v, o[1] + ay * u + by * v)


def draw_lava(surf, face, rng, t, side=False, dim=1.0):
    """Lava in one face of a block, placed anywhere on it. On the top: a crack wandering across, a crack forking
    out from a point, a small bubbling pool, or a scatter of short cracks. On a side: a seam running down from
    the top edge, a short drip, or a glowing pocket in the rock."""
    on = face_point(face)
    glow = 0.7 + 0.3 * math.sin(t * (2 + rng.random() * 2))
    heat = max(dim, 0.85)
    hot = shade((255, int(110 + 70 * glow), 40), heat)
    crust, bright = shade((120, 30, 10), dim), shade((255, 230, 150), heat)

    def crack(u, v, a, steps, step, width=2):
        pts = [(u, v)]
        for _ in range(steps):
            a += rng.uniform(-0.7, 0.7)
            u = min(0.92, max(0.08, u + math.cos(a) * step))
            v = min(0.92, max(0.08, v + math.sin(a) * step))
            pts.append((u, v))
        pts = [on(*q) for q in pts]
        pygame.draw.lines(surf, crust, False, [(px, py + 1) for px, py in pts], width + 2)
        pygame.draw.lines(surf, hot, False, pts, width)
        return pts

    def pool(u, v, r):
        ring = [on(u + math.cos(k / 8 * math.tau) * r * rng.uniform(0.75, 1.2),
                   v + math.sin(k / 8 * math.tau) * r * rng.uniform(0.75, 1.2)) for k in range(8)]
        pygame.draw.polygon(surf, crust, ring)
        cx, cy = sum(p[0] for p in ring) / 8, sum(p[1] for p in ring) / 8
        pygame.draw.polygon(surf, hot, [(cx + (px - cx) * 0.7, cy + (py - cy) * 0.7) for px, py in ring])
        return cx, cy

    if side:
        shape = rng.choice(("seam", "seam", "drip", "pocket"))
        down = math.pi / 2   # (straight down the face, in (u, v))
        if shape == "seam":     # from the top edge down through the rock, maybe splitting
            u = rng.uniform(0.2, 0.8)
            crack(u, 0.05, down + rng.uniform(-0.5, 0.5), rng.randint(3, 6), rng.uniform(0.12, 0.17))
            if rng.random() < 0.4:
                crack(u, rng.uniform(0.3, 0.5), down + rng.choice((-1, 1)) * 0.8, 2, 0.12, 1)
        elif shape == "drip":   # a short crack with lava dribbling out of the bottom
            px, py = crack(rng.uniform(0.2, 0.8), 0.05, down, rng.randint(1, 2), 0.14)[-1]
            drop = (t * 0.6 + rng.random()) % 1
            pygame.draw.circle(surf, hot, (int(px), int(py + 2 + drop * 8)), 2)
        else:                   # a pocket of lava glowing in the rock
            pool(rng.uniform(0.3, 0.7), rng.uniform(0.35, 0.7), rng.uniform(0.09, 0.13))
        return
    shape = rng.choice(("wander", "wander", "fork", "pool", "scatter"))
    if shape == "wander":   # from near one edge across to somewhere else, maybe with a branch
        u, v = rng.choice([(0.1, rng.uniform(0.2, 0.8)), (rng.uniform(0.2, 0.8), 0.1)])
        a = math.atan2(0.5 - v, 0.5 - u) + rng.uniform(-0.6, 0.6)
        crack(u, v, a, rng.randint(4, 7), rng.uniform(0.09, 0.14))
        if rng.random() < 0.5:
            crack(rng.uniform(0.3, 0.7), rng.uniform(0.3, 0.7), rng.uniform(0, math.tau), 2, 0.1, 1)
    elif shape == "fork":   # cracks spreading out from one hot spot
        u, v = rng.uniform(0.3, 0.7), rng.uniform(0.3, 0.7)
        base = rng.uniform(0, math.tau)
        for k in range(rng.randint(2, 4)):
            a = base + k * math.tau / 3 + rng.uniform(-0.4, 0.4)
            crack(u, v, a, rng.randint(2, 3), rng.uniform(0.08, 0.13))
        pygame.draw.circle(surf, bright, [int(c) for c in on(u, v)], 2)
    elif shape == "pool":   # a little pool of lava with a dark crust, bubbling
        u, v = rng.uniform(0.3, 0.7), rng.uniform(0.3, 0.7)
        cx, cy = pool(u, v, rng.uniform(0.1, 0.17))
        bubble = (t * 1.5 + rng.random()) % 1   # a bubble swelling and popping
        pygame.draw.circle(surf, bright, (int(cx + rng.uniform(-2, 2)), int(cy)), int(1 + 2 * bubble))
        if rng.random() < 0.6:   # a crack leaking out of it
            crack(u, v, rng.uniform(0, math.tau), 2, 0.12, 1)
    else:                   # a scatter of short, thin cracks
        for _ in range(rng.randint(2, 4)):
            crack(rng.uniform(0.15, 0.85), rng.uniform(0.15, 0.85), rng.uniform(0, math.tau), rng.randint(1, 2),
                  rng.uniform(0.07, 0.11), 1)


def draw_side_deco(surf, deco, face, rng, t, dim):
    """A biome's detail showing in a block's side face: lava, crystals, a carved rune or faint lights."""
    on = face_point(face)
    if deco == "lava":
        draw_lava(surf, face, rng, t, side=True, dim=dim)
    elif deco == "crystals":   # a few gems set into the rock
        for _ in range(rng.randint(1, 3)):
            px, py = on(rng.uniform(0.2, 0.8), rng.uniform(0.25, 0.8))
            r = rng.uniform(2.5, 4.5)
            col = shade(rng.choice([(170, 140, 255), (130, 210, 255), (220, 160, 255)]), dim)
            gem = [(px, py - r * 1.4), (px + r, py), (px, py + r * 1.4), (px - r, py)]
            pygame.draw.polygon(surf, col, gem)
            pygame.draw.polygon(surf, shade(col, 0.6), gem, 1)
            pygame.draw.line(surf, shade((255, 255, 255), dim), (px - r * 0.3, py - r * 0.6), (px, py - r * 1.2), 1)
    elif deco == "glyphs":     # a rune cut into the stone (upright here)
        dark = shade((118, 96, 64), dim)
        u, v = rng.uniform(0.3, 0.7), rng.uniform(0.35, 0.65)
        kind = rng.randint(0, 2)
        if kind == 0:   # a diamond with a stroke through it
            pts = [on(u, v - 0.18), on(u + 0.13, v), on(u, v + 0.18), on(u - 0.13, v)]
            pygame.draw.polygon(surf, dark, pts, 2)
            pygame.draw.line(surf, dark, on(u - 0.06, v - 0.1), on(u + 0.06, v + 0.1), 2)
        elif kind == 1:   # a pillar with a crossbar
            pygame.draw.line(surf, dark, on(u, v - 0.2), on(u, v + 0.2), 2)
            pygame.draw.line(surf, dark, on(u - 0.1, v - 0.08), on(u + 0.1, v - 0.08), 2)
        else:   # a zig-zag
            pygame.draw.lines(surf, dark, False, [on(u - 0.15, v + 0.1), on(u - 0.05, v - 0.1), on(u + 0.05, v + 0.1),
                                                  on(u + 0.15, v - 0.1)], 2)
    elif deco == "glow":       # faint cold lights in the dark rock
        pulse = 0.5 + 0.5 * math.sin(t * 2 + rng.random() * 6)
        for _ in range(2):
            px, py = on(rng.uniform(0.15, 0.85), rng.uniform(0.2, 0.85))
            col = shade((int(60 + 80 * pulse), int(110 + 90 * pulse), 255), dim)
            pygame.draw.circle(surf, col, (int(px), int(py)), 2)


def draw_block_deco(surf, deco, faces, x, y, depth, t, dim=1.0):
    """Biome detail on a block (on about a third of them - more for lava - and the same ones each frame): in
    its top, and on some of them down its sides too. `depth` is the block's own layer, so the layer below
    already shows the detail it will have once it's the one being dug."""
    rng = random.Random(hash((x, y, depth, 7)))
    if rng.random() > (LAVA_SHARE if deco == "lava" else 0.38):
        return
    sides = [rng.random() < SIDE_SHARE for _ in range(2)]   # (drawn first: the same rolls every frame)
    for face, show in zip(("left", "right"), sides):
        if show:
            draw_side_deco(surf, deco, faces[face], random.Random(hash((x, y, depth, face))), t + x * 0.7, dim)
    top = faces["top"]
    cx = sum(p[0] for p in top) / 4
    cy = sum(p[1] for p in top) / 4
    if deco == "crystals":   # a cluster of shards poking up out of the top
        for _ in range(rng.randint(2, 3)):
            bx, by = cx + rng.uniform(-12, 12), cy + rng.uniform(-4, 5)
            h, wd = rng.uniform(9, 17), rng.uniform(3, 5)
            lean = rng.uniform(-4, 4)
            col = shade(rng.choice([(170, 140, 255), (130, 210, 255), (220, 160, 255)]), dim)
            shard = [(bx - wd, by), (bx + lean, by - h), (bx + wd, by)]
            pygame.draw.polygon(surf, col, shard)
            pygame.draw.line(surf, shade((255, 255, 255), dim), (bx + lean * 0.4, by - h * 0.6), (bx + lean, by - h),
                             1)
            pygame.draw.polygon(surf, shade(col, 0.6), shard, 1)
    elif deco == "lava":     # glowing cracks, forks and little pools of lava in the top
        draw_lava(surf, top, rng, t + x * 1.3 + y, dim=dim)
    elif deco == "glyphs":   # a rune carved into the top (squashed to lie flat in the iso view)
        dark = shade((118, 96, 64), dim)
        kind = rng.randint(0, 2)
        if kind == 0:
            pygame.draw.polygon(surf, dark, [(cx, cy - 6), (cx + 11, cy), (cx, cy + 6), (cx - 11, cy)], 2)
            pygame.draw.line(surf, dark, (cx - 5, cy - 3), (cx + 5, cy + 3), 2)
        elif kind == 1:
            pygame.draw.ellipse(surf, dark, (cx - 9, cy - 4.5, 18, 9), 2)
            pygame.draw.line(surf, dark, (cx, cy - 4), (cx, cy + 4), 2)
        else:
            pygame.draw.lines(surf, dark, False, [(cx - 10, cy + 3), (cx - 3, cy - 4), (cx + 3, cy + 3),
                                                  (cx + 10, cy - 4)], 2)
    elif deco == "glow":     # faint cold lights in the dark rock
        pulse = 0.5 + 0.5 * math.sin(t * 2 + x + y * 1.7)
        for _ in range(2):
            gx, gy = cx + rng.uniform(-14, 14), cy + rng.uniform(-5, 5)
            col = shade((int(60 + 80 * pulse), int(110 + 90 * pulse), 255), dim)
            pygame.draw.circle(surf, col, (int(gx), int(gy)), 2)


BONE, BONE_EDGE = (234, 226, 202), (140, 130, 108)
BONE_SIDE_SHARE = 0.7   # bone blocks with a fossil showing in one of their sides as well


def draw_side_bones(surf, face, rng, dim):
    """Bones set into a block's side face, like a fossil in the rock: a bone, a skull or a few ribs."""
    on = face_point(face)
    bone_col, edge = shade(BONE, dim), shade(BONE_EDGE, dim)
    kind = rng.randint(0, 2)
    if kind == 0:     # a long bone lying at a slant
        u, v, a = rng.uniform(0.35, 0.65), rng.uniform(0.35, 0.65), rng.uniform(-0.6, 0.6)
        p0, p1 = on(u - math.cos(a) * 0.3, v - math.sin(a) * 0.3), on(u + math.cos(a) * 0.3, v + math.sin(a) * 0.3)
        pygame.draw.line(surf, edge, p0, p1, 5)
        pygame.draw.line(surf, bone_col, p0, p1, 3)
        for px, py in (p0, p1):
            for dy in (-1.8, 1.8):
                pygame.draw.circle(surf, edge, (int(px), int(py + dy)), 3)
                pygame.draw.circle(surf, bone_col, (int(px), int(py + dy)), 2)
    elif kind == 1:   # a skull looking out of the rock
        px, py = on(rng.uniform(0.3, 0.7), rng.uniform(0.35, 0.6))
        head = pygame.Rect(0, 0, 12, 11)
        head.center = (int(px), int(py))
        pygame.draw.ellipse(surf, edge, head.inflate(2, 2))
        pygame.draw.ellipse(surf, bone_col, head)
        pygame.draw.rect(surf, bone_col, (head.centerx - 3, head.bottom - 3, 6, 4))
        for ex in (-3, 2):
            pygame.draw.rect(surf, shade((60, 50, 44), dim), (head.centerx + ex - 1, head.centery - 2, 3, 3))
    else:             # the curve of a few ribs
        u, v = rng.uniform(0.3, 0.6), rng.uniform(0.3, 0.5)
        pygame.draw.line(surf, edge, on(u, v), on(u + 0.3, v), 3)
        for k in range(3):
            uu = u + 0.05 + k * 0.1
            pygame.draw.lines(surf, bone_col, False, [on(uu, v), on(uu - 0.04, v + 0.15), on(uu + 0.02, v + 0.3)], 2)


def draw_bones(surf, faces, x, y, depth, dim=1.0):
    """Old bones in a block's top face: a bone, crossed bones, a skull, a ribcage or a fish skeleton; most also
    show a fossil in a side. Laid flat in the iso view (screen y squashed by half); the same ones each frame,
    and seeded by the block's own layer so the layer below shows them before it's dug."""
    rng = random.Random(hash((x, y, depth, 3)))
    if rng.random() < BONE_SIDE_SHARE:
        draw_side_bones(surf, faces[rng.choice(("left", "right"))], random.Random(hash((x, y, depth, 5))), dim)
    top = faces["top"]
    cx = sum(p[0] for p in top) / 4 + rng.uniform(-6, 6)
    cy = sum(p[1] for p in top) / 4 + rng.uniform(-2, 2)
    a = rng.uniform(0, math.pi)
    bone_col, bone_edge = shade(BONE, dim), shade(BONE_EDGE, dim)

    def pt(u, v):   # a point u along / v across the bone's direction, flattened onto the ground
        return (cx + u * math.cos(a) - v * math.sin(a), cy + (u * math.sin(a) + v * math.cos(a)) * 0.5)

    def bone(u0, v0, u1, v1, knob=2.2):
        p0, p1 = pt(u0, v0), pt(u1, v1)
        pygame.draw.line(surf, bone_edge, p0, p1, 5)
        pygame.draw.line(surf, bone_col, p0, p1, 3)
        for p in (p0, p1):   # the knobbly ends
            for side in (-1, 1):
                k = (p[0] - math.sin(a) * side * 1.8, p[1] + math.cos(a) * side * 0.9)
                pygame.draw.circle(surf, bone_edge, (int(k[0]), int(k[1])), int(knob) + 1)
                pygame.draw.circle(surf, bone_col, (int(k[0]), int(k[1])), int(knob))

    kind = rng.randint(0, 4)
    if kind == 0:     # a single long bone
        bone(-10, 0, 10, 0)
    elif kind == 1:   # crossed bones
        bone(-9, -6, 9, 6)
        bone(-9, 6, 9, -6)
    elif kind == 2:   # a little skull
        head = pygame.Rect(0, 0, 16, 10)
        head.center = (int(cx), int(cy))
        pygame.draw.ellipse(surf, bone_edge, head.inflate(2, 2))
        pygame.draw.ellipse(surf, bone_col, head)
        pygame.draw.rect(surf, bone_col, (head.centerx - 4, head.bottom - 3, 8, 4))
        for ex in (-3, 3):
            pygame.draw.ellipse(surf, shade((60, 50, 44), dim), (head.centerx + ex - 2, head.centery - 2, 4, 3))
    elif kind == 3:   # a ribcage
        pygame.draw.line(surf, bone_edge, pt(-10, 0), pt(10, 0), 4)
        pygame.draw.line(surf, bone_col, pt(-10, 0), pt(10, 0), 2)
        for u in (-6, -1, 4):
            for side in (-1, 1):
                pygame.draw.lines(surf, bone_col, False, [pt(u, 0), pt(u + 1, side * 5), pt(u + 3, side * 7)], 2)
    else:             # a fish skeleton
        pygame.draw.line(surf, bone_col, pt(-9, 0), pt(7, 0), 2)
        for u in (-6, -3, 0, 3):
            pygame.draw.line(surf, bone_col, pt(u, -4), pt(u, 4), 1)
        pygame.draw.polygon(surf, bone_col, [pt(7, 0), pt(12, -4), pt(12, 4)], 1)   # head
        pygame.draw.lines(surf, bone_col, False, [pt(-9, 0), pt(-13, -3), pt(-13, 3), pt(-9, 0)], 1)   # tail


def draw_ambient(surf, world, t):
    """The biome's drifting effect, drawn behind the board. Stateless: every mote's position comes from its
    index and the time, so nothing needs updating or saving."""
    biome = biome_at(world.depth)
    kind = biome["ambient"]
    if not kind:
        return
    w, h = surf.get_size()
    accent = biome["accent"]
    for i in range(46):
        seed = i * 7919
        x0 = (seed * 13) % w
        y0 = (seed * 31) % h
        speed = 12 + (seed % 23)
        if kind == "embers":      # rising sparks, wavering as they go
            y = (y0 - t * speed * 2.2) % h
            x = x0 + math.sin(t * 1.5 + i) * 10
            heat = 0.5 + 0.5 * math.sin(t * 6 + i)
            pygame.draw.circle(surf, (255, int(110 + 100 * heat), 40), (int(x), int(y)), 1 + i % 2)
        elif kind == "sparkles":  # twinkling points
            tw = math.sin(t * (1.5 + i % 5 * 0.4) + i)
            if tw > 0.55:
                r = 1 + int((tw - 0.55) * 7)
                pygame.draw.line(surf, accent, (x0 - r, y0), (x0 + r, y0), 1)
                pygame.draw.line(surf, accent, (x0, y0 - r), (x0, y0 + r), 1)
        elif kind == "drips":     # water drops falling through the dark
            y = (y0 + t * speed * 6) % h
            pygame.draw.line(surf, (110, 140, 190), (x0, y), (x0, y + 4), 1)
        elif kind == "dust":      # slow motes drifting sideways
            x = (x0 + t * speed * 0.8) % w
            y = y0 + math.sin(t * 0.7 + i) * 8
            pygame.draw.circle(surf, (150, 140, 110), (int(x), int(y)), 1)
        elif kind == "motes":     # cold lights bobbing in the abyss
            y = y0 + math.sin(t * 0.5 + i) * 14
            glow = 0.5 + 0.5 * math.sin(t * 1.3 + i * 2)
            pygame.draw.circle(surf, (int(40 + 60 * glow), int(70 + 90 * glow), int(150 + 105 * glow)),
                               (x0, int(y)), 1 + i % 2)


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
    Archlich: violet threads from each wisp shielding him, and the shield itself."""
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


def draw_bro_mound(surf, world, t):
    """The Burrow Brothers: the tunnelling brother's mound ploughing towards the crew - and, as he's about to burst
    up, a red ring where he'll come out."""
    boss = world.boss()
    if not boss or boss.kind != "burrowbros" or not boss.mound:
        return
    x, y = boss.mound
    cx, cy = iso(x, y, world.column_height(*world.cell_of(x, y)) + world.rise)
    churn = math.sin(t * 12) * 2
    pygame.draw.ellipse(surf, (16, 12, 20), (cx - 30, cy - 7, 60, 14))
    hump = pygame.Rect(cx - 26, cy - 18 + churn, 52, 22)
    pygame.draw.ellipse(surf, (118, 88, 60), hump)
    pygame.draw.ellipse(surf, (72, 52, 34), hump, 2)
    for k in range(5):   # clods of earth flung up
        a = (t * 2.4 + k * 0.2) % 1
        px = cx - 20 + k * 10 + math.sin(t * 3 + k) * 4
        pygame.draw.circle(surf, (96, 70, 46), (int(px), int(cy - 16 - a * 22 + a * a * 26)), 3)
    if boss.swap_timer < 2.0:   # about to burst up: warn the crew
        q = 1 - boss.swap_timer / 2.0
        ring = _ground_ellipse(world, x, y, BRO_SURFACE_RADIUS)
        overlay = pygame.Surface(surf.get_size(), pygame.SRCALPHA)
        pygame.draw.ellipse(overlay, (255, 60, 40, int(50 + 70 * q)), ring)
        pygame.draw.ellipse(overlay, (255, 150, 110, 220), ring, 3)
        surf.blit(overlay, (0, 0))


def draw_shade_auras(surf, world, t):
    """Abyssal Shades: a pool of darkness on the ground around each, where the crew's swings drag."""
    spots = [(e.x, e.y, False) for e in world.enemies if e.spec.get("aura") and e.targetable]
    spots += [(p[0], p[1], True) for p in world.void_pools]   # (and The Void Maw's hungry pools of darkness)
    if not spots:
        return
    overlay = pygame.Surface(surf.get_size(), pygame.SRCALPHA)
    for x, y, hungry in spots:
        ring = _ground_ellipse(world, x, y, SHADE_RADIUS)
        pulse = 0.5 + 0.5 * math.sin(t * 2 + x)
        pygame.draw.ellipse(overlay, (6, 4, 14, int(110 + 30 * pulse)), ring)
        if hungry:   # a violet rim that writhes: it bites (and a click drives it back)
            fast = 0.5 + 0.5 * math.sin(t * 6 + x)
            pygame.draw.ellipse(overlay, (170, 110, 255, int(120 + 100 * fast)), ring, 3)
            pygame.draw.ellipse(overlay, (120, 60, 200, 70), ring.inflate(-ring.w * 0.45, -ring.h * 0.45), 2)
        else:
            pygame.draw.ellipse(overlay, (90, 70, 140, 90), ring, 2)
    surf.blit(overlay, (0, 0))


def draw_void_inhale(surf, world, t):
    """The Void Maw inhaling: rings of darkness closing in on it, and streams dragging each pulled crew member."""
    boss = world.boss()
    if not boss or boss.kind != "voidmaw" or boss.inhale is None:
        return
    overlay = pygame.Surface(surf.get_size(), pygame.SRCALPHA)
    k = boss.inhale / VOID_INHALE_SECS
    for i in range(3):   # rings rushing inwards
        share = 1 - ((t * 1.6 + i / 3) % 1)
        ring = _ground_ellipse(world, boss.x, boss.y, VOID_INHALE_RADIUS * share)
        pygame.draw.ellipse(overlay, (150, 100, 230, int(40 + 120 * (1 - share))), ring, 3)
    pygame.draw.ellipse(overlay, (20, 10, 40, int(40 + 50 * k)), _ground_ellipse(world, boss.x, boss.y, 1.6))
    mx, my = world.entity_screen(boss, 40)
    for m in world.void_pulled(boss):
        x, y = world.entity_screen(m, 30)
        for j in range(4):   # dashes streaming from them into its mouth
            a = (t * 2.5 + j / 4) % 1
            px, py = x + (mx - x) * a, y + (my - y) * a
            pygame.draw.circle(overlay, (190, 150, 255, int(200 * (1 - a))), (int(px), int(py)), 3)
    surf.blit(overlay, (0, 0))
    from .boss_sprites import void_eye_screen
    eye = void_eye_screen(boss, world.rise)
    if eye:   # a target pulsing round the open eye: hit it now to choke the breath
        pulse = 0.5 + 0.5 * math.sin(t * 10)
        r = int(eye[2] + 8 + 6 * pulse)
        pygame.draw.circle(surf, (255, 255, 255), (int(eye[0]), int(eye[1])), r, 2)
        pygame.draw.circle(surf, (200, 160, 255), (int(eye[0]), int(eye[1])), r + 5, 1)


def draw_curses(surf, world, t):
    """Archlich: a violet sigil over each cursed crew member, its ring running down to the burst,
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


def draw_stuns(surf, world, t):
    """Crew reeling from the Fanged Behemoth's screech: little stars circling their heads."""
    for m in world.miners:
        if m.stun > 0 and m.state != "down":
            x, y = world.entity_screen(m, 50 + m.height)
            for k in range(3):
                a = t * 6 + k * math.tau / 3
                sx, sy = x + math.cos(a) * 10, y + math.sin(a) * 4
                pygame.draw.line(surf, (255, 240, 140), (sx - 3, sy), (sx + 3, sy), 2)
                pygame.draw.line(surf, (255, 240, 140), (sx, sy - 3), (sx, sy + 3), 2)


def draw_bone_throws(surf, world, t):
    """Bones the Bone Tyrant hurls at the crew: a red mark on whoever it's coming for, a shadow racing across
    the ground, and a big bone spinning end over end on a high arc with a trail of dust behind it."""
    overlay = pygame.Surface(surf.get_size(), pygame.SRCALPHA)
    for (sx, sy), target, age, (gx, gy) in world.bone_throws:
        q = min(1.0, age / BONE_THROW_SECS)
        tx, ty = world.entity_screen(target, 30)
        fx, fy = world.entity_screen(target)
        pulse = 0.5 + 0.5 * math.sin(t * 16)
        mark = pygame.Rect(0, 0, 34 + 10 * (1 - q), 14 + 4 * (1 - q))
        mark.center = (fx, fy)
        pygame.draw.ellipse(overlay, (255, 60, 40, int(90 + 90 * pulse)), mark, 3)
        shadow = (gx + (fx - gx) * q, gy + (fy - gy) * q)   # the bone's shadow on the ground
        sw = 10 + 12 * q
        pygame.draw.ellipse(overlay, (10, 8, 12, 120), (shadow[0] - sw / 2, shadow[1] - sw / 5, sw, sw / 2.5))
        arc = lambda k: (sx + (tx - sx) * k, sy + (ty - sy) * k - math.sin(k * math.pi) * 90)
        for back in (0.06, 0.12, 0.18):   # dust trail
            if q - back > 0:
                px, py = arc(q - back)
                pygame.draw.circle(overlay, (235, 228, 205, int(110 * (1 - back * 4))), (int(px), int(py)),
                                   int(5 - back * 15))
        x, y = arc(q)
        draw_bone(surf, x, y, age * 16, 13, 5)
    surf.blit(overlay, (0, 0))


def draw_slam_zones(surf, world, t):
    """A boss winding up: the ground it is about to cave in glows red, filling in as the slam nears."""
    winding = [e for e in world.enemies if (e.boss or e.spec.get("slam")) and e.windup > 0]   # (+ slime chunks)
    if not winding:
        return
    overlay = pygame.Surface(surf.get_size(), pygame.SRCALPHA)
    for e in winding:
        gx, gy = e.slam_at or (e.x, e.y)   # (a diving boss marks where it will land, not where it is)
        cx, cy = iso(gx, gy, world.column_height(*world.cell_of(gx, gy)) + world.rise)
        radius = e.spec.get("slam_radius", BOSS_SLAM_RADIUS)
        full = pygame.Rect(0, 0, radius * TILE_W * 1.42, radius * TILE_H * 1.42)
        full.center = (cx, cy)
        q = 1 - e.windup / e.windup_total
        pulse = 0.5 + 0.5 * math.sin(t * (10 + 20 * q))
        pygame.draw.ellipse(overlay, (255, 40, 30, int(40 + 50 * pulse)), full)
        inner = full.inflate(-full.w * (1 - q), -full.h * (1 - q))
        pygame.draw.ellipse(overlay, (255, 80, 50, 120), inner)
        pygame.draw.ellipse(overlay, (255, 150, 110, 230), full, 3)
    surf.blit(overlay, (0, 0))


def draw_phantom(surf, world, t):
    """Phantom Slam charging: a ghostly purple hand hangs over its block, rising as the glow beneath it grows."""
    if not world.phantom:
        return
    cell, age = world.phantom
    q = min(1.0, age / PHANTOM_WINDUP)
    cx, cy = world.cell_screen(cell)
    overlay = pygame.Surface((180, 220), pygame.SRCALPHA)
    ox, oy = 90, 170   # the block's top sits here on the overlay
    pulse = 0.5 + 0.5 * math.sin(t * (8 + 18 * q))
    ring = pygame.Rect(0, 0, 40 + 90 * q, 20 + 45 * q)
    ring.center = (ox, oy)
    pygame.draw.ellipse(overlay, (190, 110, 255, int(40 + 60 * q * pulse)), ring)
    pygame.draw.ellipse(overlay, (225, 180, 255, int(120 + 100 * q)), ring, 2)
    hand = pygame.Surface((70, 70), pygame.SRCALPHA)
    draw_icon(hand, "hand", (35, 35), 26, (225, 190, 255))
    hand.set_alpha(int(110 + 110 * q))
    lift = 40 + 30 * q + math.sin(t * 5) * 3   # drawn back up, ready to come down
    overlay.blit(hand, hand.get_rect(center=(ox, oy - lift)))
    for k in range(3):   # wisps streaming off it
        a = t * 4 + k * 2.1
        pygame.draw.circle(overlay, (210, 170, 255, 160), (int(ox + math.sin(a) * 20), int(oy - lift + 30 + (a * 8) % 20)), 2)
    surf.blit(overlay, (cx - ox, cy - oy))


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


def pick_boiler(world, pos):
    """Whether `pos` is on the Steam Boiler."""
    if not world.lv("boiler"):
        return False
    x, y = _anchor(world, BOILER_POS)
    return abs(pos[0] - x) <= 20 and y - 44 <= pos[1] <= y + 4


def draw_boiler(surf, base, pressure, t, hovered=False):
    """The Steam Boiler: an iron drum on legs with a chimney and a pressure gauge; puffing and whistling when full."""
    x, y = int(base[0]), int(base[1])
    full = pressure >= 1.0
    pygame.draw.ellipse(surf, (16, 12, 20), (x - 17, y - 5, 34, 10))
    for d in (-9, 9):   # legs
        pygame.draw.line(surf, (60, 58, 66), (x + d, y - 6), (x + d, y - 1), 3)
    drum = pygame.Rect(x - 14, y - 36, 28, 30)
    pygame.draw.rect(surf, (96, 92, 104), drum, border_radius=8)
    pygame.draw.rect(surf, (58, 56, 66), drum, 2, border_radius=8)
    for ry in (drum.y + 9, drum.bottom - 9):   # riveted bands
        pygame.draw.line(surf, (70, 68, 78), (drum.x + 2, ry), (drum.right - 3, ry), 2)
    glow = (255, int(120 + 100 * pressure), 60)   # the firebox, brighter as the pressure builds
    pygame.draw.rect(surf, (40, 30, 30), (x - 6, drum.bottom - 9, 12, 6), border_radius=2)
    pygame.draw.rect(surf, glow, (x - 4, drum.bottom - 8, 8, 4), border_radius=1)
    pygame.draw.rect(surf, (70, 66, 76), (x + 4, drum.y - 12, 6, 13))   # chimney
    gx, gy = x - 4, drum.y + 13   # the gauge, its needle sweeping round as the pressure climbs
    pygame.draw.circle(surf, (235, 230, 215), (gx, gy), 6)
    pygame.draw.circle(surf, (58, 56, 66), (gx, gy), 6, 1)
    pygame.draw.arc(surf, (220, 60, 50), (gx - 5, gy - 5, 10, 10), -0.4, 0.6, 2)   # the red zone
    a = math.pi * (1.1 - 1.2 * pressure) + (math.sin(t * 30) * 0.08 if full else 0)
    pygame.draw.line(surf, (30, 26, 30), (gx, gy), (gx + math.cos(a) * 5, gy - math.sin(a) * 5), 2)
    if full:   # steam puffing from the chimney, and a glow to say "click me"
        for k in range(3):
            q = (t * 1.5 + k / 3) % 1
            pygame.draw.circle(surf, (230, 235, 240), (int(x + 7 + q * 6), int(drum.y - 14 - q * 18)), int(3 + q * 5), 1)
        pulse = 0.5 + 0.5 * math.sin(t * 6)
        pygame.draw.rect(surf, (230, 240, 255), drum.inflate(6 + 4 * pulse, 6 + 4 * pulse), 2, border_radius=10)
    else:   # a thin gauge bar under it shows how far along it is
        bar = pygame.Rect(x - 14, y + 4, 28, 4)
        pygame.draw.rect(surf, (20, 16, 24), bar.inflate(2, 2))
        pygame.draw.rect(surf, (210, 220, 235), (bar.x, bar.y, int(bar.w * pressure), bar.h))
    if hovered:
        pygame.draw.rect(surf, (255, 255, 255), drum.inflate(10, 10), 1, border_radius=10)


def draw_steam(surf, world, t):
    """The Steam Boiler venting: a wall of scalding steam rolling out from its corner across the whole board."""
    if world.steam is None:
        return
    q = world.steam / STEAM_SECS
    rng = random.Random(9)
    overlay = pygame.Surface(surf.get_size(), pygame.SRCALPHA)
    reach = GRID * 1.6 * min(1.0, q * 1.6)   # how far the front has rolled, in tiles
    fade = 1 - max(0.0, (q - 0.45) / 0.55)
    for _ in range(140):
        a = rng.uniform(math.pi / 2, math.pi)   # (out across the board from its right corner)
        d = rng.uniform(0, 1) ** 0.6 * reach
        gx, gy = BOILER_POS[0] + math.cos(a) * d, BOILER_POS[1] + math.sin(a) * d
        px, py = iso(gx, gy, 2.5 + world.rise)
        r = int(16 + rng.uniform(0, 24) + 12 * q)
        pygame.draw.circle(overlay, (235, 240, 248, int(rng.uniform(70, 130) * fade)), (int(px), int(py - 20 * q)), r)
    surf.blit(overlay, (0, 0))


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


def draw_rocks(surf, world, t):
    """Rocks the crew lob at a boss once they've nothing left to dig: a tumbling stone on a high arc."""
    for _, (sx, sy), boss, age in world.rocks:
        q = min(1.0, age / ROCK_SECS)
        tx, ty = enemy_anchor(boss, world.rise, t)
        x, y = sx + (tx - sx) * q, sy + (ty - sy) * q - math.sin(q * math.pi) * 40
        spin = age * 20
        pts = [(x + math.cos(spin + k * 2.1) * 4, y + math.sin(spin + k * 2.1) * 3.5) for k in range(3)]
        pygame.draw.polygon(surf, (130, 118, 108), pts)
        pygame.draw.polygon(surf, (70, 62, 58), pts, 1)


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
    """Buried Treasure: a chest rises out of the broken block and its lid flies open, a beam of light shoots
    up into the sky, sparkles drift up the beam and coins spill out."""
    for x, y, age in world.chest_fx:
        p = age / CHEST_FX_SECS
        fade = 1 - max(0.0, (p - 0.75) / 0.25)                 # everything fades out over the last quarter
        cx = int(x)
        cy = int(y - 6 - 18 * _ease(min(1.0, p / 0.12)))      # pops up out of the block
        _draw_treasure_beam(surf, cx, cy - 14, age, p, fade)
        _draw_chest(surf, cx, cy, min(1.0, max(0.0, (p - 0.1) / 0.18)), fade)
        if p > 0.2:   # coins and gems tumbling out over the rim
            rng = random.Random(int(x * 7 + y * 13))
            for k in range(9):
                q = (p - 0.2 - k * 0.02) / 0.5
                if not 0 < q < 1:
                    continue
                vx = rng.uniform(-60, 60)
                px = cx + vx * q
                py = cy - 16 - 70 * q + 120 * q * q
                col = rng.choice([(255, 210, 60), (255, 230, 120), (120, 220, 255), (240, 70, 90)])
                pygame.draw.circle(surf, _scale_col(col, fade), (int(px), int(py)), 3)


def _ease(q):
    return 1 - (1 - q) ** 3


def _draw_treasure_beam(surf, cx, base, age, p, fade):
    """A column of golden light from the open chest to the top of the screen."""
    grow = _ease(min(1.0, max(0.0, (p - 0.15) / 0.2)))       # shoots up as the lid opens
    if grow <= 0:
        return
    top = base - (base + 40) * grow
    beam = pygame.Surface((140, int(base - top) + 1), pygame.SRCALPHA)
    h = beam.get_height()
    pulse = 0.85 + 0.15 * math.sin(age * 9)
    for half, col, alpha in ((60, (255, 210, 90), 50), (30, (255, 230, 140), 110), (11, (255, 252, 225), 230)):
        a = int(alpha * fade * pulse)
        # wider at the top: light spreading as it rises
        pygame.draw.polygon(beam, (*col, a), [(70 - half * 0.45, h), (70 + half * 0.45, h),
                                              (70 + half, 0), (70 - half, 0)])
    surf.blit(beam, (cx - 70, top))
    rng = random.Random(cx)
    for k in range(12):   # sparkles drifting up the beam
        ky = base - ((age * 160 + k * 53) % max(1.0, base - top))
        kx = cx + math.sin(age * 4 + k) * 9 + rng.uniform(-6, 6)
        r = 1 + (k % 3)
        pygame.draw.line(surf, _scale_col((255, 255, 230), fade), (kx - r, ky), (kx + r, ky), 1)
        pygame.draw.line(surf, _scale_col((255, 255, 230), fade), (kx, ky - r), (kx, ky + r), 1)


def _draw_chest(surf, cx, cy, opened, fade):
    """A wooden treasure chest with gold bands and a lock; `opened` 0..1 swings the lid back on its hinge."""
    wood, dark, band = _scale_col((150, 92, 44), fade), _scale_col((92, 54, 26), fade), _scale_col((240, 190, 60), fade)
    w, h = 36, 20
    body = pygame.Rect(cx - w // 2, cy - h, w, h)
    if opened > 0:   # gold glowing inside, seen past the open lid
        glow = pygame.Rect(body.x + 3, body.y - 6, w - 6, 10)
        pygame.draw.ellipse(surf, _scale_col((255, 220, 90), fade), glow)
        pygame.draw.ellipse(surf, _scale_col((255, 250, 210), fade), glow.inflate(-12, -4))
    pygame.draw.rect(surf, wood, body, border_radius=3)
    for k in (1, 2):   # planks
        pygame.draw.line(surf, dark, (body.x + 2, body.y + k * h // 3), (body.right - 3, body.y + k * h // 3), 1)
    for bx in (body.x + 6, body.right - 8):   # gold bands
        pygame.draw.rect(surf, band, (bx, body.y, 3, h))
    pygame.draw.rect(surf, dark, body, 2, border_radius=3)
    lock = pygame.Rect(cx - 4, body.y + 3, 8, 9)
    pygame.draw.rect(surf, band, lock, border_radius=2)
    pygame.draw.circle(surf, dark, (cx, body.y + 7), 1)
    # the lid, seen from the front: closed it sits on the body; opening, its hinge rises to the back edge and it
    # tips back, so we see more and more of its (darker) inside, with the golden glow showing beneath it
    hinge = body.y - 7 * opened
    lid_h = 8 + 9 * opened
    lean = 4 * opened   # the far edge looks a little narrower as it tips away
    inside = opened > 0.45
    pts = [(body.x - 1, hinge), (body.right + 1, hinge), (body.right + 1 - lean, hinge - lid_h),
           (body.x - 1 + lean, hinge - lid_h)]
    pygame.draw.polygon(surf, _scale_col((110, 64, 30), fade) if inside else wood, pts)
    pygame.draw.polygon(surf, dark, pts, 2)
    for bx in (body.x + 6, body.right - 8):   # the bands carry on over the lid
        pygame.draw.line(surf, band, (bx + 1, hinge), (bx + 1 + (lean if bx < cx else -lean), hinge - lid_h), 3)


def _scale_col(color, f):
    return tuple(int(c * f) for c in color)


def quake_lift(world, x, y):
    """How far (in blocks) a Seismic Strikes wave is heaving the ground at grid point (x, y) right now.
    The wave front rolls outward; ground it passes pops up and settles, strongest near the epicentre."""
    lift = 0.0
    for qx, qy, age, _, reach in world.quakes:
        d = math.hypot(x - qx, y - qy)
        if d > reach:
            continue
        behind = age * QUAKE_SPEED - d          # how far the front has travelled past this point
        if 0 <= behind < 1.2:
            strength = (1 - d / reach) ** 0.7
            lift += math.sin(behind / 1.2 * math.pi) * 0.3 * strength
    return lift


def draw_quake_waves(surf, world):
    """Dusty rings spreading across the board from each Seismic Strikes crit."""
    if not world.quakes:
        return
    overlay = pygame.Surface(surf.get_size(), pygame.SRCALPHA)
    for qx, qy, age, _, reach in world.quakes:
        cx, cy = iso(qx, qy, 2 + world.rise)
        for lag, width in ((0.0, 5), (0.45, 3)):   # leading ring and a fainter one behind it
            rad = age * QUAKE_SPEED - lag
            if not 0 < rad <= reach:
                continue
            fade = 1 - rad / reach
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
