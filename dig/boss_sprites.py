"""Boss sprites of their own (not a scaled-up minion): the Broodmother, Fanged Behemoth, Bone Tyrant, Slime King,
Vampire Lord and Archlich. (The Zombie King still borrows the zombie's.)

Each is drawn facing right at about twice a regular monster's size, around its feet, onto the boss canvas
(see sprites._draw_boss), which mirrors it when the boss faces left, flashes it when hit and scales it by the
boss's `scale`. Their crowns are part of the sprite. Imported by sprites.py once its own helpers exist.
"""
import math
import random

import pygame

from .config import BAD
from .enemies import DIVE_SECS, THROW_ANIM_SECS, THROW_RELEASE
from .iso import iso
from .sprites import (BAT_EDGE, BONE_COL, BONE_SHADE, SLIME_ANGRY, SLIME_DARK, SLIME_GREEN, SPIDER_BODY, VAMP_CAPE,
                      VAMP_HAIR, VAMP_LINING, VAMP_SKIN, VAMP_SUIT, _ease_out, _lerp, draw_bone)
from .util import shade

SHADOW = (16, 12, 20)
GOLD, GOLD_DARK = (255, 205, 60), (150, 100, 20)
RUBY, SAPPHIRE = (220, 40, 60), (80, 200, 255)
EYE = (240, 50, 50)
SILK, SILK_DARK = (225, 222, 205), (170, 165, 150)
# How high above its feet each boss's body sits (canvas px, before scaling): what you click, and where effects
# land. And how deep each one starts in the ground when it climbs out of it.
ANCHOR = {"broodmother": 32, "greatbat": 44, "bonetyrant": 80, "slimeking": 34, "vampirelord": 40, "lich": 50}
RISE_DEPTH = {"bonetyrant": 136, "slimeking": 72, "vampirelord": 72}
DROP_TOP = {"broodmother": 64}   # where the silk thread meets the Broodmother as she lowers herself in
BAR_HEIGHT = {"broodmother": 76, "bonetyrant": 136, "slimeking": 82, "vampirelord": 82, "lich": 112}   # (health bar)


def _feet(e, rise):
    fx, fy = iso(e.x, e.y, e.draw_z + rise)
    return int(fx), int(fy)


def _charge(e):
    """0..1 through a slam wind-up (0 when not winding up)."""
    return 1 - e.windup / e.windup_total if e.windup > 0 else 0.0


def _walking(e):
    return e.state == "hunting" and e.windup <= 0


def _shadow(s, fx, fy, w):
    pygame.draw.ellipse(s, SHADOW, (fx - w // 2, fy - 5, w, 10))


def _crown(s, x, y, w=14, h=8, tilt=0.0, gem=RUBY):
    """A gold crown, its base centred on (x, y), tipped by `tilt` radians."""
    hw = w // 2
    pts = [(-hw, 0), (-hw, -h), (-hw // 2, -h // 2), (0, -h - 2), (hw // 2, -h // 2), (hw, -h), (hw, 0)]
    c, sn = math.cos(tilt), math.sin(tilt)
    pts = [(x + px * c - py * sn, y + px * sn + py * c) for px, py in pts]
    pygame.draw.polygon(s, GOLD, pts)
    pygame.draw.polygon(s, GOLD_DARK, pts, 1)
    pygame.draw.circle(s, gem, (int(x + 3 * sn), int(y - 3 * c)), 1)


def _hovered(s, fx, fy, w):
    pygame.draw.ellipse(s, BAD, (fx - w // 2, fy - w // 6, w, w // 3), 2)


def _drawer(fn):
    """Give a boss drawer the regular signature, fading it in with `alpha` (materialising)."""
    def draw(surf, e, rise, t, hovered, dy=0, alpha=1.0, pos=None):
        if alpha >= 1:
            fn(surf, e, rise, t, hovered, dy, pos)
            return
        layer = pygame.Surface(surf.get_size(), pygame.SRCALPHA)
        fn(layer, e, rise, t, hovered, dy, pos)
        layer.set_alpha(int(255 * alpha))
        surf.blit(layer, (0, 0))
    return draw


# ----- Broodmother: a swollen, egg-laden abdomen and a crown of eyes ---------------------------------------------
BROOD_DARK, BROOD_LEG, BROOD_SHINE = shade(SPIDER_BODY, 0.55), (40, 32, 50), (120, 104, 140)


def _leg(s, pts, w=3, col=BROOD_LEG):
    pygame.draw.lines(s, shade(col, 0.6), False, pts, w + 2)
    pygame.draw.lines(s, col, False, pts, w)
    for p in pts[1:-1]:   # knobbly joints
        pygame.draw.circle(s, col, (int(p[0]), int(p[1])), w // 2 + 1)


@_drawer
def draw_broodmother(s, e, rise, t, hovered, dy, pos):
    fx, ground = _feet(e, rise)
    fy = ground + dy
    c = _charge(e)
    if hovered:
        _hovered(s, fx, ground, 110)
    if e.state != "emerging":
        _shadow(s, fx, ground, 104)
    fx += math.sin(t * 40) * 1.5 * c - 8   # (her bulk sits behind her head: centre the whole of her)
    pace = e.anim_t * (16 if _walking(e) else 4)
    for i in range(4):   # eight legs, scuttling in alternate pairs
        for side in (-1, 1):
            step = math.sin(pace + i * 1.7 + (side > 0) * math.pi) * (3 if _walking(e) else 1)
            cx, cy = fx + 16, fy - 20
            knee = (cx + side * (21 + i * 5) + step, cy - 26 + i * 4 - abs(step) * 0.6 - 4 * c)
            foot = (cx + side * (25 + i * 9) + step * 1.4, fy - i)
            _leg(s, [(cx + side * (2 + i * 2), cy), knee, foot])
    swell = 1 + 0.06 * c + 0.02 * math.sin(e.anim_t * 3)
    ab = pygame.Rect(0, 0, int(62 * swell), int(50 * swell))
    ab.center = (fx - 21, fy - 37)
    pygame.draw.ellipse(s, SPIDER_BODY, ab)
    pygame.draw.ellipse(s, BROOD_DARK, ab, 2)
    pygame.draw.ellipse(s, BROOD_SHINE, (ab.x + 10, ab.y + 6, 18, 8))
    hx, hy = ab.centerx + 4, ab.centery + 2   # red hourglass
    pygame.draw.polygon(s, (200, 30, 40), [(hx - 6, hy - 9), (hx + 6, hy - 9), (hx, hy), (hx + 6, hy + 9),
                                            (hx - 6, hy + 9), (hx, hy)])
    stir = 0.5 + 0.5 * math.sin(e.anim_t * 5)
    for k, (ex, ey, r) in enumerate(((-23, -5, 5), (-17, -17, 4), (-9, 15, 5), (1, -21, 4), (9, -11, 3),
                                     (-23, 9, 4), (15, 7, 4), (-5, -3, 3), (13, 19, 3))):   # pale eggs bulging
        ex, ey = int(ab.centerx + ex * swell), int(ab.centery + ey * swell)
        pygame.draw.circle(s, SILK, (ex, ey), r)
        pygame.draw.circle(s, SILK_DARK, (ex, ey), r, 1)
        inner = _lerp((150, 190, 110), (240, 110, 70), c) if k % 3 else _lerp((150, 190, 110), (90, 60, 120), stir)
        pygame.draw.circle(s, inner, (ex, ey), max(1, r - 3))
    rear = int(6 * c)   # winding up, she rears her head and fangs
    pygame.draw.ellipse(s, SPIDER_BODY, (fx + 4, fy - 30 - rear // 2, 26, 20))   # cephalothorax
    pygame.draw.ellipse(s, BROOD_DARK, (fx + 4, fy - 30 - rear // 2, 26, 20), 2)
    head = (fx + 30, fy - 24 - rear)
    pygame.draw.circle(s, SPIDER_BODY, head, 7)
    pygame.draw.circle(s, BROOD_DARK, head, 7, 1)
    gape = int(2 * c + (1 if e.state == "attacking" else 0))
    for dx in (-1 - gape, 3 + gape):   # fangs
        pygame.draw.line(s, (220, 210, 200), (head[0] + 4 + dx, head[1] + 4), (head[0] + 4 + dx, head[1] + 8), 2)
    cx, cy = head[0] - 1, head[1] - 6   # crown of eyes: gold points each tipped with a glowing eye
    pts = [(cx - 8, cy + 2), (cx - 9, cy - 5), (cx - 4, cy - 1), (cx, cy - 8), (cx + 4, cy - 1), (cx + 9, cy - 5),
           (cx + 8, cy + 2)]
    pygame.draw.polygon(s, GOLD, pts)
    pygame.draw.polygon(s, GOLD_DARK, pts, 1)
    blink = int(e.anim_t * 1.3) % 7 == 0
    for px, py in ((cx - 9, cy - 6), (cx, cy - 9), (cx + 9, cy - 6)):
        pygame.draw.circle(s, (120, 20, 20), (px, py), 3)
        if not blink:
            pygame.draw.circle(s, _lerp(EYE, (255, 200, 80), c), (px, py), 2)
    for ex, ey in ((0, 0), (3, 1), (2, -3)):
        pygame.draw.circle(s, EYE, (head[0] + 3 + ex, head[1] - 1 + ey), 1)


# ----- Fanged Behemoth: a shaggy giant bat with torn wings ---------------------------------------------------------
FANG = (245, 240, 230)
FUR, FUR_DARK, MANE, WING, WING_BONE = (88, 62, 70), (52, 36, 46), (150, 120, 112), (96, 60, 92), (190, 170, 160)


def _wing(s, root, side, span, lift, droop=0):
    """A bat wing: arm up to a wrist, finger bones fanning out, a torn membrane scalloped between the tips."""
    rx, ry = root
    wrist = (rx + side * span * 0.42, ry - lift)
    tips = []
    for i in range(4):
        f = i / 3
        ang = math.radians(-35 + 95 * f)   # first finger points up and out, last one down and back in
        length = span * (0.62 - 0.18 * f)
        tips.append((wrist[0] + side * math.cos(ang) * length, wrist[1] + math.sin(ang) * length + droop * f))
    body_low = (rx + side * 2, ry + span * 0.22)
    pts = [root, wrist, tips[0]]
    for a, b in zip(tips, tips[1:]):   # scallops between fingertips, curving in toward the wrist
        mid = ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2)
        pts.append((mid[0] + (wrist[0] - mid[0]) * 0.28, mid[1] + (wrist[1] - mid[1]) * 0.28))
        pts.append(b)
    pts.append(((tips[-1][0] + body_low[0]) / 2, (tips[-1][1] + body_low[1]) / 2 - 3))
    pts.append(body_low)
    pygame.draw.polygon(s, WING, pts)
    pygame.draw.polygon(s, BAT_EDGE, pts, 1)
    for a, b, k in ((tips[0], tips[1], 0.55), (tips[1], tips[2], 0.4), (tips[2], tips[3], 0.6)):   # rips
        hx = wrist[0] + ((a[0] + b[0]) / 2 - wrist[0]) * k
        hy = wrist[1] + ((a[1] + b[1]) / 2 - wrist[1]) * k
        pygame.draw.ellipse(s, (0, 0, 0, 0), (hx - 2, hy - 1, 4, 3))
        pygame.draw.ellipse(s, BAT_EDGE, (hx - 3, hy - 2, 6, 5), 1)
    pygame.draw.line(s, WING_BONE, root, wrist, 2)   # arm
    for tip in tips:
        pygame.draw.line(s, WING_BONE, wrist, tip, 1)
    pygame.draw.polygon(s, WING_BONE, [(wrist[0], wrist[1] - 1), (wrist[0] + side * 3, wrist[1] - 5),
                                       (wrist[0] + side, wrist[1] + 1)])   # thumb claw


def _ear(s, base, tip, back):
    pygame.draw.polygon(s, FUR, [base, tip, back])
    pygame.draw.polygon(s, FUR_DARK, [base, tip, back], 1)
    ix = ((base[0] * 2 + tip[0] * 2 + back[0]) / 5, (base[1] * 2 + tip[1] * 2 + back[1]) / 5)
    pygame.draw.polygon(s, (190, 110, 120), [((base[0] + back[0]) / 2, (base[1] + back[1]) / 2 + 1),
                                             ((ix[0] + tip[0]) / 2, (ix[1] + tip[1]) / 2), ix])


def behemoth_height(e):
    """How high above its spot the Behemoth hovers: lower and lower as it dives onto a marked spot."""
    h = ANCHOR["greatbat"] - math.sin(e.anim_t * 3) * 3
    if e.slam_at and 0 < e.windup <= DIVE_SECS:
        h *= 0.25 + 0.75 * e.windup / DIVE_SECS
    return h


def anchor_height(e):
    """Canvas px from the boss's feet up to the middle of its body."""
    return behemoth_height(e) if e.kind == "greatbat" else ANCHOR[e.kind]


def bar_height(e):
    """Canvas px from the boss's feet up to where its health bar sits."""
    return behemoth_height(e) + 50 if e.kind == "greatbat" else BAR_HEIGHT[e.kind]


@_drawer
def draw_behemoth(s, e, rise, t, hovered, dy, pos):
    fx, fy = _feet(e, rise)
    c = _charge(e)
    if pos:   # swooping in from the dark
        cx, cy = int(pos[0]), int(pos[1])
    else:
        cx, cy = fx, int(fy - behemoth_height(e) + dy)
        lift = (fy - cy) / ANCHOR["greatbat"]
        _shadow(s, fx, fy, int(30 + 16 / max(0.5, lift)))
    if hovered:
        _hovered(s, cx, cy + 22, 70)
    flap = math.sin(e.anim_t * (10 if e.state == "emerging" else 6))
    diving = bool(e.slam_at) and 0 < e.windup <= DIVE_SECS
    lift = 30 if diving else 18 + 8 * flap * (1 - c) + 14 * c   # (wings swept up while it winds up to dive)
    for side in (-1, 1):
        _wing(s, (cx + side * 9, cy - 6), side, 60 - (14 if diving else 0), lift, droop=6 - 10 * c)
    for d in (-1, 1):   # clawed feet
        px = cx + d * 7
        pygame.draw.line(s, FUR_DARK, (px, cy + 15), (px + d, cy + 21), 2)
        for k in (-2, 0, 2):
            pygame.draw.line(s, (220, 215, 200), (px + d + k, cy + 21), (px + d + k * 1.3, cy + 24), 1)
    pygame.draw.ellipse(s, FUR_DARK, (cx - 15, cy - 14, 30, 34))   # body
    pygame.draw.ellipse(s, FUR, (cx - 13, cy - 13, 26, 31))
    pygame.draw.ellipse(s, (130, 100, 100), (cx - 7, cy - 2, 14, 17))   # paler belly
    for k in range(11):   # shaggy pale mane round the shoulders, hanging in tufts
        px = cx - 16 + k * 3.2
        py = cy - 12 + abs(k - 5) * 0.8
        pygame.draw.polygon(s, shade(MANE, 0.6), [(px - 3, py - 4), (px + 3, py - 4), (px + 1, py + 7 + (k % 2) * 3)])
        pygame.draw.polygon(s, MANE, [(px - 2, py - 4), (px + 2, py - 4), (px + 1, py + 5 + (k % 2) * 3)])
    hx, hy = cx + 2, cy - 17
    for d in (-1, 1):   # enormous ears
        _ear(s, (hx + d * 3, hy - 6), (hx + d * 13, hy - 30), (hx + d * 12, hy - 3))
    pygame.draw.circle(s, FUR_DARK, (hx, hy), 11)
    pygame.draw.circle(s, FUR, (hx, hy), 10)
    pygame.draw.ellipse(s, (70, 44, 54), (hx - 4, hy - 1, 9, 6))   # snout
    pygame.draw.circle(s, (30, 18, 24), (hx - 1, hy + 1), 1)
    pygame.draw.circle(s, (30, 18, 24), (hx + 2, hy + 1), 1)
    for d in (-1, 1):
        pygame.draw.circle(s, (30, 10, 16), (hx + d * 5, hy - 4), 3)
        pygame.draw.circle(s, _lerp(EYE, (255, 220, 120), c), (hx + d * 5, hy - 4), 2)
    gape = 4 + int(4 * c)   # the maw opens wide as it dives
    pygame.draw.rect(s, (60, 10, 20), (hx - 6, hy + 5, 13, gape))
    for d in (-4, 4):   # big fangs
        pygame.draw.polygon(s, FANG, [(hx + d - 2, hy + 5), (hx + d + 2, hy + 5), (hx + d, hy + 12)])
    _crown(s, hx, hy - 9, 14, 7)


# ----- Bone Tyrant: a four-armed, ram-skulled skeleton warlord --------------------------------------------------
SOCKET = (40, 30, 34)


def _bone(s, a, b, w=3):
    """A bone from a to b: shaded outline, pale core, knuckled ends."""
    pygame.draw.line(s, BONE_SHADE, a, b, w + 2)
    pygame.draw.line(s, BONE_COL, a, b, w)
    for p in (a, b):
        pygame.draw.circle(s, BONE_SHADE, (int(p[0]), int(p[1])), w // 2 + 2)
        pygame.draw.circle(s, BONE_COL, (int(p[0]), int(p[1])), w // 2 + 1)


def _arm(s, shoulder, hand, side, bend):
    """Upper arm and forearm, the elbow pushed out to the side by `bend`."""
    elbow = ((shoulder[0] + hand[0]) / 2 + side * bend, (shoulder[1] + hand[1]) / 2 + abs(bend) * 0.3)
    _bone(s, shoulder, elbow, 3)
    _bone(s, elbow, hand, 2)


@_drawer
def draw_bone_tyrant(s, e, rise, t, hovered, dy, pos):
    fx, ground = _feet(e, rise)
    fy = ground + dy
    c = _charge(e)
    if hovered:
        _hovered(s, fx, ground, 70)
    if e.state != "emerging":
        pygame.draw.ellipse(s, SHADOW, (fx - 30, ground - 5, 60, 10))
    pace = e.anim_t * 5
    step = math.sin(pace) * 5 if _walking(e) else 0
    bob = abs(math.sin(pace)) * 2 if _walking(e) else 0
    crouch = 4 * c   # bracing for the slam
    top = fy - bob + crouch
    for side in (-1, 1):   # long legs, wide stance
        st = step * side
        hip, foot = (fx + side * 6, top - 46), (fx + side * 14 + st, fy - 2)
        knee = (fx + side * (12 + crouch) + st * 0.5, top - 24)
        _bone(s, hip, knee, 4)
        _bone(s, knee, foot, 3)
        pygame.draw.line(s, BONE_COL, foot, (foot[0] + 6, foot[1]), 3)
    pygame.draw.ellipse(s, BONE_SHADE, (fx - 11, top - 52, 22, 10))   # pelvis
    pygame.draw.ellipse(s, BONE_COL, (fx - 10, top - 52, 20, 8))
    sway = math.sin(pace * 0.5) * 2
    cloth = [(fx - 12, top - 48), (fx + 12, top - 48), (fx + 9 - sway, top - 30), (fx + 5, top - 34),
             (fx + 2 - sway, top - 26), (fx - 2, top - 33), (fx - 6 - sway, top - 28), (fx - 10, top - 34)]
    pygame.draw.polygon(s, (130, 30, 40), cloth)   # tattered loincloth
    pygame.draw.polygon(s, (70, 14, 24), cloth, 1)
    pygame.draw.line(s, GOLD, (fx - 12, top - 47), (fx + 12, top - 47), 2)
    pygame.draw.line(s, BONE_SHADE, (fx, top - 50), (fx, top - 98), 4)   # spine
    pygame.draw.line(s, BONE_COL, (fx, top - 50), (fx, top - 98), 2)
    for k in range(5):   # ribs
        ry = top - 92 + k * 6
        w = 26 - k * 2
        pygame.draw.arc(s, BONE_SHADE, (fx - w // 2, ry - 3, w, 10), math.pi * 1.05, math.pi * 1.95, 3)
        pygame.draw.arc(s, BONE_COL, (fx - w // 2, ry - 3, w, 10), math.pi * 1.05, math.pi * 1.95, 2)
    throw = 1 - e.throw_anim / THROW_ANIM_SECS if e.throw_anim > 0 else None
    swing = math.sin(pace) * 3 if _walking(e) else math.sin(e.anim_t * 2) * 1.5
    # four arms: the upper pair brandish bones overhead, the lower pair hold them out; all go up for a slam
    for side in (-1, 1):
        for upper in (True, False):
            sy = top - (96 if upper else 80)
            sh = (fx + side * 13, sy)
            pygame.draw.line(s, BONE_COL, (fx, sy), sh, 3)   # collar bones
            pygame.draw.circle(s, BONE_SHADE, sh, 4)
            pygame.draw.circle(s, BONE_COL, sh, 3)
            if upper and side == 1 and throw is not None:   # this one hurls the bones
                if throw < THROW_RELEASE:   # swung back over the head...
                    k = _ease_out(throw / THROW_RELEASE)
                    hand = (fx + 34 - 44 * k, sy - 28 - 8 * k)
                else:                       # ...then whipped forward
                    k = (throw - THROW_RELEASE) / (1 - THROW_RELEASE)
                    hand = (fx + 10 + 34 * k, sy - 36 + 30 * k)
                _arm(s, sh, hand, side, 6)
                if throw < THROW_RELEASE:
                    draw_bone(s, hand[0], hand[1] - 2, -1.2 - throw * 3, 8, 3)
                pygame.draw.circle(s, BONE_COL, (int(hand[0]), int(hand[1])), 3)
                continue
            if upper:
                rest = (fx + side * 34, sy - 28 + swing * side)
                raised = (fx + side * 22, sy - 44)
            else:
                rest = (fx + side * 44, sy + swing * side)
                raised = (fx + side * 32, sy - 40)
            hand = (rest[0] + (raised[0] - rest[0]) * c, rest[1] + (raised[1] - rest[1]) * c)
            _arm(s, sh, hand, side, 10 if upper else 12)
            if upper or c > 0.5:   # the bone it holds: upright overhead...
                a, b = (hand[0] - side * 4, hand[1] - 10), (hand[0] + side * 4, hand[1] + 10)
            else:                  # ...or levelled forward
                a, b = (hand[0] - side * 2, hand[1] + 6), (hand[0] + side * 10, hand[1] - 8)
            _bone(s, a, b, 3)
            pygame.draw.circle(s, BONE_COL, (int(hand[0]), int(hand[1])), 3)
    hx, hy = fx + 2, top - 110   # ram skull with curling horns
    for side in (-1, 1):
        pygame.draw.circle(s, (60, 48, 36), (hx + side * 10, hy + 1), 10, 2)
        pygame.draw.circle(s, (110, 92, 70), (hx + side * 10, hy + 1), 9, 3)
        pygame.draw.circle(s, (150, 128, 96), (hx + side * 10, hy + 1), 6, 3)
    face = [(hx - 8, hy - 8), (hx + 8, hy - 8), (hx + 6, hy + 8), (hx + 2, hy + 14), (hx - 2, hy + 14), (hx - 6, hy + 8)]
    pygame.draw.polygon(s, BONE_SHADE, face)
    pygame.draw.polygon(s, BONE_COL, [(hx - 7, hy - 7), (hx + 7, hy - 7), (hx + 5, hy + 8), (hx + 1, hy + 13),
                                      (hx - 1, hy + 13), (hx - 5, hy + 8)])
    glare = _lerp((255, 90, 40), (255, 230, 120), c)
    for ex in (-1, 1):
        pygame.draw.circle(s, SOCKET, (hx + ex * 4, hy - 1), 3)
        pygame.draw.circle(s, glare, (hx + ex * 4, hy - 1), 1 + int(c > 0.5))
    pygame.draw.line(s, SOCKET, (hx - 1, hy + 7), (hx + 1, hy + 7), 2)
    _crown(s, hx, hy - 8, 16, 9)


# ----- Slime King: a vast see-through blob full of everything it has swallowed -----------------------------------
GULLET_W, GULLET_H = 100, 66


def _gullet_body(col):
    """The blob at its resting size, loot and all (stretched to wobble)."""
    body = pygame.Surface((GULLET_W + 4, GULLET_H + 4), pygame.SRCALPHA)
    r = pygame.Rect(2, 2, GULLET_W, GULLET_H)
    pygame.draw.ellipse(body, (*col, 150), r)
    pygame.draw.ellipse(body, (*shade(col, 0.8), 120), r.inflate(-16, -14).move(0, 6))   # deeper middle
    hat = (30, 34)   # a swallowed hard hat...
    pygame.draw.ellipse(body, (240, 200, 40, 200), (hat[0] - 10, hat[1] - 8, 20, 14))
    pygame.draw.rect(body, (240, 200, 40, 200), (hat[0] - 13, hat[1] + 2, 26, 3))
    pygame.draw.line(body, (120, 90, 50, 210), (56, 62), (78, 46), 3)             # ...a pickaxe...
    pygame.draw.arc(body, (190, 190, 200, 220), (66, 38, 22, 16), 0.3, 2.9, 3)
    for cx, cy in ((48, 58), (55, 61), (42, 62), (62, 56)):                        # ...gold...
        pygame.draw.circle(body, (255, 210, 70, 220), (cx, cy), 3)
        pygame.draw.circle(body, (170, 120, 30, 220), (cx, cy), 3, 1)
    pygame.draw.line(body, (*BONE_COL, 200), (20, 52), (34, 58), 3)               # ...and a bone
    for bx, by in ((20, 52), (34, 58)):
        pygame.draw.circle(body, (*BONE_COL, 200), (bx, by), 3)
    for bx, by, br in ((84, 48, 3), (16, 30, 2), (70, 58, 2), (44, 20, 2)):       # bubbles
        pygame.draw.circle(body, (220, 255, 210, 140), (bx, by), br)
    pygame.draw.ellipse(body, (255, 255, 255, 110),
                        (r.x + r.w * 0.18, r.y + r.h * 0.1, r.w * 0.28, r.h * 0.18))   # shine
    pygame.draw.ellipse(body, (*SLIME_DARK, 255), r, 2)
    return body


@_drawer
def draw_slime_king(s, e, rise, t, hovered, dy, pos):
    fx, ground = _feet(e, rise)
    fy = ground + dy
    c = _charge(e)
    hop = max(0.0, math.sin(e.anim_t * 4)) * 0.6 if _walking(e) else 0.0
    if hovered:
        _hovered(s, fx, ground, 116)
    if e.state != "emerging":
        _shadow(s, fx, ground, int(104 * (1 - 0.2 * hop)))
    wob = math.sin(e.anim_t * 7) * 0.04
    w = int(GULLET_W * (1 + wob - 0.12 * hop + 0.22 * c))
    h = int(GULLET_H * (1 - wob + 0.15 * hop + 0.12 * c))
    lift = int(hop * 8)
    col = _lerp(SLIME_GREEN, SLIME_ANGRY, c * 0.8)
    body = pygame.transform.scale(_gullet_body(col), (w + 4, h + 4))
    top = fy - lift - h - 1
    s.blit(body, (fx - w // 2 - 2, top - 2))
    k = h / GULLET_H
    _crown(s, fx - 4 * w // GULLET_W, top + int(8 * k), 26, 11, tilt=-0.25 - wob * 2, gem=SAPPHIRE)   # sinking in
    pygame.draw.arc(s, SLIME_DARK, (fx - 22, top + int(3 * k), 36, 12), math.pi * 1.1, math.pi * 1.9, 2)   # goo lip
    ey = top + int(17 * k)
    for ex in (12, 28):   # big lazy eyes...
        x = fx + ex * w // GULLET_W
        pygame.draw.circle(s, (250, 250, 240), (x, ey), 5)
        pygame.draw.circle(s, (20, 20, 24), (x + 2, ey), 3)
        if c > 0.2:       # ...narrowed in anger as it winds up
            pygame.draw.line(s, SLIME_DARK, (x - 5, ey - 6 + (ex == 28) * 2), (x + 5, ey - 4 - (ex == 28) * 2), 2)
    gx = fx + 6 * w // GULLET_W
    if c > 0.2:   # a roaring mouth, or a wide grin
        pygame.draw.ellipse(s, SLIME_DARK, (gx + 6, ey + 6, 18, 6 + int(6 * c)))
    else:
        pygame.draw.arc(s, SLIME_DARK, (gx, ey + 1, 30, 12), math.pi * 1.1, math.pi * 1.9, 2)
    for dx in (-38, -14, 30):   # drips at the base
        pygame.draw.ellipse(s, col, (fx + dx * w // GULLET_W, fy - 4, 8, 6))


# ----- Vampire Lord: the Count, his cape spread like bat wings ---------------------------------------------------
RIM = (74, 56, 90)   # a lighter edge so his near-black cape reads against the dark cave
FANG_WHITE, VAMP_EYE = (255, 255, 255), (255, 40, 40)


@_drawer
def draw_count(s, e, rise, t, hovered, dy, pos):
    fx, ground = _feet(e, rise)
    fy = ground + dy
    c = _charge(e)
    biting = e.mode == "bite" and e.victim is not None
    if hovered:
        _hovered(s, fx, ground, 70)
    if e.state != "emerging":
        _shadow(s, fx, ground, 58)
    walk = _walking(e) and not biting
    step = math.sin(e.anim_t * 5) * 3 if walk else 0
    top = fy - 62
    # the cape spreads wider and higher as he winds up; feeding, he folds it round his victim
    spread, lean = (0.55, 12) if biting else (1 + 0.12 * c, 0)

    def cape(side, x, y):
        flutter = math.sin(e.anim_t * 4 + x * 0.15) * 1.5 * x / 52
        return fx + lean * x / 52 + side * x * spread, top + y - 12 * c * x / 52 + flutter + (14 if biting else 0) * x / 52

    for side in (-1, 1):
        outer = [cape(side, 6, 14), cape(side, 52, 6), cape(side, 48, 30), cape(side, 44, 44), cape(side, 34, 38),
                 cape(side, 28, 54), cape(side, 18, 48), (fx + side * 12, fy - 2), (fx + side * 4, fy - 2)]
        pygame.draw.polygon(s, VAMP_CAPE, outer)
        pygame.draw.polygon(s, RIM, outer, 1)
        inner = [cape(side, 8, 17), cape(side, 46, 10), cape(side, 44, 28), cape(side, 40, 40), cape(side, 33, 35),
                 cape(side, 27, 50), cape(side, 18, 45), (fx + side * 11, fy - 5)]
        pygame.draw.polygon(s, VAMP_LINING, inner)
        for rib in (0.35, 0.65):   # wing-like ribs in the lining
            pygame.draw.line(s, shade(VAMP_LINING, 0.6), cape(side, 8, 17), cape(side, 46 - 30 * rib, 10 + 40 * rib), 1)
        tip = cape(side, 52, 6)   # arms along the cape's top edge, bony fingers holding it up at the tips
        pygame.draw.line(s, VAMP_SUIT, cape(side, 6, 16), tip, 3)
        pygame.draw.line(s, RIM, cape(side, 6, 14), (tip[0], tip[1] - 2), 1)
        pygame.draw.circle(s, VAMP_SKIN, (int(tip[0]), int(tip[1])), 2)
        for k in range(3):
            b = math.atan2(-2, side * 3) + (k - 1) * 0.45
            pygame.draw.line(s, VAMP_SKIN, tip, (tip[0] + math.cos(b) * 4, tip[1] + math.sin(b) * 4), 1)
    for d, st in ((-3, step), (3, -step)):   # legs
        pygame.draw.line(s, VAMP_HAIR, (fx + d, fy - 14), (fx + d + st, fy - 1), 3)
    body = pygame.Rect(fx - 7, top + 14, 14, 36)
    pygame.draw.rect(s, VAMP_SUIT, body, border_radius=3)
    pygame.draw.rect(s, RIM, body, 1, border_radius=3)
    pygame.draw.polygon(s, (235, 235, 240), [(fx - 4, top + 14), (fx + 4, top + 14), (fx, top + 26)])   # shirt front
    pygame.draw.rect(s, VAMP_LINING, (fx - 2, top + 15, 4, 2))
    pygame.draw.circle(s, GOLD, (fx, top + 22), 2)   # medallion
    pygame.draw.line(s, GOLD_DARK, (fx - 4, top + 15), (fx, top + 20), 1)
    pygame.draw.line(s, GOLD_DARK, (fx + 4, top + 15), (fx, top + 20), 1)
    hx, hy = (fx + 8, top + 12) if biting else (fx, top + 5)   # stooping to the neck to feed
    for side in (-1, 1):   # towering collar behind the head
        pygame.draw.polygon(s, VAMP_CAPE, [(hx + side * 4, hy + 10), (hx + side * 15, hy - 13), (hx + side * 11, hy + 10)])
        pygame.draw.polygon(s, RIM, [(hx + side * 4, hy + 10), (hx + side * 15, hy - 13), (hx + side * 11, hy + 10)], 1)
        pygame.draw.polygon(s, VAMP_LINING, [(hx + side * 6, hy + 9), (hx + side * 14, hy - 9), (hx + side * 10, hy + 9)])
    pygame.draw.ellipse(s, shade(VAMP_SKIN, 0.75), (hx - 6, hy - 8, 12, 17))   # gaunt long face
    pygame.draw.ellipse(s, VAMP_SKIN, (hx - 5, hy - 8, 11, 16))
    pygame.draw.polygon(s, VAMP_HAIR, [(hx - 6, hy - 1), (hx - 6, hy - 6), (hx, hy - 9), (hx + 6, hy - 6), (hx + 6, hy - 1),
                                       (hx + 3, hy - 5), (hx, hy - 2), (hx - 3, hy - 5)])   # widow's peak
    eye = _lerp(VAMP_EYE, (255, 200, 120), c)
    for ex in (-2, 3):
        pygame.draw.line(s, eye, (hx + ex - 1, hy + 1), (hx + ex + 1, hy + 1), 1)
    pygame.draw.line(s, shade(VAMP_SKIN, 0.6), (hx - 4, hy + 4), (hx - 3, hy + 6), 1)   # sunken cheeks
    for d in (-1, 2):
        pygame.draw.polygon(s, FANG_WHITE, [(hx + d, hy + 5), (hx + d + 1, hy + 5), (hx + d + 0.5, hy + 8 + c * 2)])
    if biting:   # blood running from the fangs
        drip = int(e.anim_t * 8) % 5
        pygame.draw.line(s, (170, 20, 35), (hx + 1, hy + 8), (hx + 1, hy + 10 + drip), 1)
    _crown(s, hx, hy - 7, 12, 5)


# ----- Archlich: a robed skeleton sorcerer with a staff and his phylactery -----------------------------------------
PURPLE, BLUE = (205, 160, 255), (150, 210, 255)
ROBE, ROBE_DARK = (62, 42, 96), (30, 20, 50)
LICH_LIFT = 10   # he floats this far off the ground


def _glow(s, pos, r, color, alpha=90, over=False):
    """A soft halo. Over empty canvas it is max-blended (a plain alpha blit onto transparent pixels would
    darken it towards black); `over` an opaque body it is blended normally."""
    r = max(2, int(r))
    g = pygame.Surface((r * 2 + 2, r * 2 + 2), pygame.SRCALPHA)
    for k in range(5):   # faint at the rim, stronger towards the middle
        pygame.draw.circle(g, (*color, int(alpha * (0.15 + k * 0.12))), (r + 1, r + 1), max(1, int(r * (1 - k * 0.18))))
    s.blit(g, (pos[0] - r - 1, pos[1] - r - 1), special_flags=0 if over else pygame.BLEND_RGBA_MAX)


def _bone_hand(s, x, y, d=1):
    x, y = int(x), int(y)
    pygame.draw.circle(s, BONE_SHADE, (x, y), 4)
    pygame.draw.circle(s, BONE_COL, (x, y), 3)
    for k in range(4):
        a = -1.2 + k * 0.45
        tip = (x + d * math.cos(a) * 8, y + math.sin(a) * 8)
        pygame.draw.line(s, BONE_COL, (x, y), tip, 1)
        pygame.draw.circle(s, BONE_COL, (int(tip[0]), int(tip[1])), 1)


def _lich_skull(s, x, y, r, eye):
    pygame.draw.circle(s, BONE_SHADE, (x, y), r + 1)
    pygame.draw.circle(s, BONE_COL, (x, y), r)
    jw = int(r * 1.1)
    pygame.draw.rect(s, BONE_SHADE, (x - jw // 2 + 1, y + r - 3, jw, r // 2 + 2))
    pygame.draw.rect(s, BONE_COL, (x - jw // 2 + 1, y + r - 3, jw - 1, r // 2 + 1))
    for k in range(1, jw // 2):   # teeth
        pygame.draw.line(s, BONE_SHADE, (x - jw // 2 + 1 + k * 2, y + r - 2), (x - jw // 2 + 1 + k * 2, y + r))
    for d in (-1, 1):
        c = (x + d * 3 + 1, y)
        pygame.draw.circle(s, (34, 24, 40), c, 3)
        _glow(s, c, 4, eye, 110, over=True)
        pygame.draw.circle(s, eye, c, 1)
    pygame.draw.polygon(s, (34, 24, 40), [(x + 1, y + 3), (x - 1, y + 5), (x + 3, y + 5)])


@_drawer
def draw_archlich(s, e, rise, t, hovered, dy, pos):
    fx, fy = _feet(e, rise)
    c = _charge(e)
    if hovered:
        _hovered(s, fx, fy, 64)
    _shadow(s, fx, fy, 46)
    by = int(fy - LICH_LIFT + math.sin(e.anim_t * 2) * 2.5 + dy)
    pulse = 0.5 + 0.5 * math.sin(t * 5)
    sx = fx + 26   # staff (behind the robe), its gem flaring as he gathers a spell
    pygame.draw.line(s, (60, 40, 30), (sx, by + 4), (sx - 2, by - 104), 4)
    pygame.draw.line(s, (110, 80, 55), (sx, by + 4), (sx - 2, by - 104), 2)
    gem = (sx - 2, by - 108)
    for a in (-0.9, 0, 0.9):   # prongs clutching the gem
        pygame.draw.line(s, (90, 65, 45), (sx - 2, by - 100), (gem[0] + math.sin(a) * 7, gem[1] - 4), 2)
    _glow(s, gem, 14 + 3 * pulse + 10 * c, PURPLE, 110 + 60 * c)
    pygame.draw.polygon(s, PURPLE, [(gem[0], gem[1] - 7), (gem[0] + 5, gem[1]), (gem[0], gem[1] + 6), (gem[0] - 5, gem[1])])
    pygame.draw.polygon(s, (255, 240, 255), [(gem[0], gem[1] - 4), (gem[0] + 2, gem[1]), (gem[0], gem[1] + 2),
                                             (gem[0] - 2, gem[1])])
    rng = random.Random(3)   # robe, its ragged hem stirring
    hem = []
    for i in range(13):
        x = fx - 24 + 46 * i / 12
        hem.append((x, by - 6 + ((8 * rng.uniform(0.6, 1.0) + math.sin(e.anim_t * 4 + i) * 1.5) if i % 2 else 0)))
    robe = [(fx - 13, by - 64), (fx + 13, by - 64), (fx + 22, by - 6)] + hem[::-1][1:-1] + [(fx - 24, by - 6)]
    pygame.draw.polygon(s, ROBE, robe)
    pygame.draw.polygon(s, ROBE_DARK, robe, 2)
    pygame.draw.polygon(s, shade(ROBE, 0.7), [(fx - 2, by - 60), (fx + 4, by - 60), (fx + 8, by - 4), (fx - 6, by - 4)])
    pygame.draw.line(s, PURPLE, (fx + 1, by - 60), (fx + 1, by - 4), 1)   # trim down the front
    for d in (-1, 1):   # high collar
        pygame.draw.polygon(s, ROBE_DARK, [(fx + d * 4, by - 62), (fx + d * 18, by - 80), (fx + d * 14, by - 60)])
        pygame.draw.line(s, PURPLE, (fx + d * 6, by - 62), (fx + d * 17, by - 78), 1)
    pygame.draw.lines(s, GOLD_DARK, False, [(fx - 8, by - 62), (fx, by - 46), (fx + 8, by - 62)], 1)   # phylactery
    p = (fx, by - 42)
    _glow(s, p, 8 + 2 * pulse, BLUE, 120, over=True)
    diamond = [(p[0], p[1] - 5), (p[0] + 4, p[1]), (p[0], p[1] + 5), (p[0] - 4, p[1])]
    pygame.draw.polygon(s, BLUE, diamond)
    pygame.draw.polygon(s, (60, 90, 140), diamond, 1)
    pygame.draw.circle(s, (255, 255, 255), (p[0] - 1, p[1] - 1), 1)
    sleeve = [(fx + 8, by - 60), (fx + 24, by - 50), (fx + 22, by - 42), (fx + 6, by - 50)]   # hand on the staff
    pygame.draw.polygon(s, ROBE, sleeve)
    pygame.draw.polygon(s, ROBE_DARK, sleeve, 1)
    _bone_hand(s, sx - 1, by - 50, 1)
    hand = (fx - 20 - 6 * c, by - 40 - 34 * c)   # the casting hand rises as the spell builds
    sleeve = [(fx - 8, by - 60), (hand[0] - 2, hand[1] - 4), (hand[0] + 4, hand[1]), (fx - 6, by - 50)]
    pygame.draw.polygon(s, ROBE, sleeve)
    pygame.draw.polygon(s, ROBE_DARK, sleeve, 1)
    _glow(s, (hand[0] - 2, hand[1] + 2), 8 + 2 * pulse + 10 * c, PURPLE, 90 + 80 * c)
    _bone_hand(s, hand[0], hand[1], -1)
    _lich_skull(s, fx + 2, by - 72, 9, _lerp(BLUE, (255, 255, 255), c))
    _crown(s, fx + 2, by - 79, 20, 10, gem=PURPLE)


DRAWERS = {"broodmother": draw_broodmother, "greatbat": draw_behemoth, "bonetyrant": draw_bone_tyrant,
           "slimeking": draw_slime_king, "vampirelord": draw_count, "lich": draw_archlich}


# ----- the deep: The Burrow Brothers, The Mountain, The Void Maw ------------------------------------------------------------
def _poly(s, col, pts, edge, w=2):
    pygame.draw.polygon(s, col, pts)
    pygame.draw.polygon(s, edge, pts, w)


BRO_LOOKS = [   # Dig, then Delve: fur, its shadow, belly, and what they wear on their heads
    dict(fur=(130, 92, 62), dark=(82, 56, 36), belly=(176, 138, 104), hat="hardhat"),
    dict(fur=(98, 102, 120), dark=(58, 60, 76), belly=(150, 152, 168), hat="goggles"),
]


@_drawer
def draw_burrow_bros(s, e, rise, t, hovered, dy, pos):
    """One of The Burrow Brothers, whichever is above ground: a hulking mole-man with shovel claws and a crown.
    Dig wears a hard hat with its lamp lit; Delve, brass goggles. Fresh up out of the ground, he heaves himself
    out of the hole; winding up, the claws go up."""
    fx, ground = _feet(e, rise)
    look = BRO_LOOKS[getattr(e, "up", 0)]
    fur, dark, belly = look["fur"], look["dark"], look["belly"]
    c = _charge(e)
    if hovered:
        _hovered(s, fx, ground, 110)
    if e.state != "emerging":
        _shadow(s, fx, ground, 96)
    rising = min(1.0, getattr(e, "surface_t", 9.0) / 0.5)   # (just burst up: still climbing out of the hole)
    top = ground + dy + int((1 - _ease_out(rising)) * 80)
    clip = s.get_clip()
    s.set_clip(pygame.Rect(0, 0, s.get_width(), ground + 2))   # (below ground: hidden)
    step = math.sin(e.anim_t * 4) * 3 if _walking(e) else 0
    for d, st in ((-1, step), (1, -step)):   # stubby legs
        pygame.draw.ellipse(s, dark, (fx + d * 16 - 9, top - 14 - max(0, st), 18, 14))
    body = pygame.Rect(fx - 30, top - 74, 60, 66)
    pygame.draw.ellipse(s, dark, body.inflate(4, 4))
    pygame.draw.ellipse(s, fur, body)
    pygame.draw.ellipse(s, belly, (fx - 17, top - 60, 34, 46))
    for k in range(5):   # shaggy fur along the flanks
        pygame.draw.line(s, dark, (fx - 28 + k * 2, top - 60 + k * 8), (fx - 32 + k * 2, top - 54 + k * 8), 2)
        pygame.draw.line(s, dark, (fx + 28 - k * 2, top - 60 + k * 8), (fx + 32 - k * 2, top - 54 + k * 8), 2)
    head = (fx + 6, top - 80)
    pygame.draw.circle(s, dark, head, 21)
    pygame.draw.circle(s, fur, head, 19)
    snout = pygame.Rect(head[0] + 6, head[1] - 2, 22, 14)   # long snout, pink nose
    pygame.draw.ellipse(s, belly, snout)
    pygame.draw.ellipse(s, dark, snout, 1)
    pygame.draw.circle(s, (240, 140, 150), (snout.right - 2, snout.centery - 1), 5)
    for d in (0, 5):   # buck teeth
        pygame.draw.rect(s, (245, 240, 225), (snout.x + 6 + d, snout.bottom - 2, 4, 6))
    for d in (-1, 1):   # whiskers
        pygame.draw.line(s, dark, (snout.right - 6, snout.centery + d * 2), (snout.right + 8, snout.centery + d * 6), 1)
    if look["hat"] == "goggles":   # Delve: brass goggles over little eyes
        pygame.draw.line(s, (90, 70, 40), (head[0] - 19, head[1] - 6), (head[0] + 12, head[1] - 6), 4)
        for gx in (head[0] - 4, head[0] + 8):
            pygame.draw.circle(s, (200, 160, 70), (gx, head[1] - 6), 6)
            pygame.draw.circle(s, (150, 220, 230), (gx, head[1] - 6), 4)
            pygame.draw.circle(s, (255, 255, 255), (gx - 1, head[1] - 8), 1)
        _crown(s, head[0] - 2, head[1] - 16, 20, 10)
    else:   # Dig: a battered hard hat with its lamp lit, the crown jammed on top
        for gx in (head[0] - 2, head[0] + 8):
            pygame.draw.circle(s, (20, 14, 16), (gx, head[1] - 4), 2)
        hat = pygame.Rect(head[0] - 20, head[1] - 22, 40, 18)
        pygame.draw.ellipse(s, (240, 200, 40), hat)
        pygame.draw.rect(s, (240, 200, 40), (head[0] - 24, head[1] - 9, 48, 5), border_radius=2)
        pygame.draw.ellipse(s, (170, 130, 20), hat, 1)
        _glow(s, (head[0] + 14, head[1] - 14), 8, (255, 240, 170), 140, over=True)
        pygame.draw.circle(s, (255, 250, 210), (head[0] + 14, head[1] - 14), 3)
        _crown(s, head[0] - 2, head[1] - 20, 20, 10)
    lift = 46 * c   # the great shovel claws: out in front, raised overhead for a slam
    swing = math.sin(e.anim_t * 4) * 3 if _walking(e) else 0
    for d in (-1, 1):
        paw = (fx + d * 26 + 14, top - 34 - lift + swing * d)
        pygame.draw.line(s, dark, (fx + d * 20, top - 52), paw, 9)
        pygame.draw.ellipse(s, belly, (paw[0] - 9, paw[1] - 7, 18, 14))
        for k in range(4):
            tip = (paw[0] + 12, paw[1] - 7 + k * 5)
            pygame.draw.line(s, (235, 228, 210), (paw[0] + 5, paw[1] - 5 + k * 4), tip, 3)
    s.set_clip(clip)
    if rising < 1:   # the hole he's climbing out of, earth thrown up round it
        pygame.draw.ellipse(s, (40, 26, 18), (fx - 34, ground - 8, 68, 16))
        for k in range(7):
            a = k / 7 * math.pi
            pygame.draw.circle(s, (120, 88, 58), (int(fx + math.cos(a) * 38), int(ground - 4 + math.sin(a) * 3)), 5)


ANCHOR.update({"burrowbros": 50, "mountain": 80, "voidmaw": 70})
RISE_DEPTH.update({"burrowbros": 90, "mountain": 150})
BAR_HEIGHT.update({"burrowbros": 116, "mountain": 152, "voidmaw": 140})


MOUNTAIN_PLATES = 4   # (knocked off in this order: left shoulder, right shoulder, chest, brow)
STONE, STONE_DARK, STONE_HI = (120, 118, 132), (66, 64, 78), (160, 158, 172)
PLATE, PLATE_DARK, MOSS = (98, 96, 112), (52, 50, 64), (96, 140, 80)


def _boulder(s, rect, col=STONE, dark=STONE_DARK):
    r = pygame.Rect(rect)
    pygame.draw.ellipse(s, col, r)
    pygame.draw.ellipse(s, dark, r, 2)
    pygame.draw.arc(s, STONE_HI, r.inflate(-r.w // 3, -r.h // 3).move(-r.w // 8, -r.h // 8), 1.6, 2.8, 2)


def _plate(s, pts):
    _poly(s, PLATE, pts, PLATE_DARK, 2)
    cx = sum(p[0] for p in pts) / len(pts)
    cy = sum(p[1] for p in pts) / len(pts)
    for dx, dy in ((-4, -3), (4, 3)):
        pygame.draw.circle(s, STONE_HI, (int(cx + dx), int(cy + dy)), 1)


def _scar(s, pts, t):
    """Where a plate was knocked off: bare stone, cracked and glowing."""
    pulse = 0.6 + 0.4 * math.sin(t * 5)
    cx = sum(p[0] for p in pts) / len(pts)
    cy = sum(p[1] for p in pts) / len(pts)
    glow = (255, int(140 + 60 * pulse), 70)
    pygame.draw.lines(s, glow, False, [(cx - 8, cy - 5), (cx - 1, cy + 1), (cx - 5, cy + 7)], 2)
    pygame.draw.lines(s, glow, False, [(cx + 6, cy - 6), (cx + 2, cy), (cx + 8, cy + 5)], 2)


@_drawer
def draw_mountain(s, e, rise, t, hovered, dy, pos):
    """The Mountain: a towering golem of stacked boulders in stone plates. Each plate knocked off leaves a glowing
    scar; the arms rise for a stomp."""
    fx, ground = _feet(e, rise)
    fy = ground + dy
    c = _charge(e)
    plates = getattr(e, "plates", MOUNTAIN_PLATES)
    gone = MOUNTAIN_PLATES - plates
    if hovered:
        _hovered(s, fx, ground, 130)
    if e.state != "emerging":
        _shadow(s, fx, ground, 120)
    step = math.sin(e.anim_t * 3) * 3 if _walking(e) else 0
    for d, st in ((-1, step), (1, -step)):   # tree-trunk legs of stacked stone
        _boulder(s, (fx + d * 22 - 12, fy - 26 - max(0, st), 24, 26))
        _boulder(s, (fx + d * 20 - 14, fy - 46 - max(0, st) * 0.5, 28, 24))
    sway = math.sin(e.anim_t * 3) * 2 if _walking(e) else 0
    top = fy - int(4 * c)   # it rears up for a stomp
    _boulder(s, (fx - 36, top - 106, 72, 64))   # the great torso
    for d in (-1, 1):   # arms: boulder upon boulder, raised overhead as it winds up
        lift = 40 * c
        _boulder(s, (fx + d * 48 - 15, top - 100 - lift * 0.3, 30, 28))
        _boulder(s, (fx + d * 54 - 12, top - 76 - lift * 0.9 + sway * d, 24, 24))
        _boulder(s, (fx + d * 56 - 14, top - 54 - lift * 1.6 + sway * d, 28, 26))
    shoulders = {-1: [(fx - 36, top - 108), (fx - 60, top - 102), (fx - 62, top - 86), (fx - 38, top - 84)],
                 1: [(fx + 36, top - 108), (fx + 60, top - 102), (fx + 62, top - 86), (fx + 38, top - 84)]}
    chest = [(fx - 24, top - 98), (fx + 24, top - 98), (fx + 20, top - 62), (fx, top - 54), (fx - 20, top - 62)]
    for k, pts in enumerate((shoulders[-1], shoulders[1], chest)):
        if gone > k:
            _scar(s, pts, t)
        else:
            _plate(s, pts)
    head = pygame.Rect(fx - 17, top - 132, 34, 30)
    _boulder(s, head)
    brow = [(fx - 17, top - 126), (fx + 17, top - 126), (fx + 14, top - 116), (fx - 14, top - 116)]
    if gone > 3:
        _scar(s, brow, t)
    else:
        _plate(s, brow)
    eye = (255, 170, 80) if plates == 0 else _lerp((120, 230, 255), (255, 120, 90), c)
    for d in (-7, 7):   # glowing eye slits
        pygame.draw.rect(s, (20, 18, 30), (fx + d - 5, top - 114, 10, 5))
        _glow(s, (fx + d, top - 112), 4, eye, 120, over=True)
        pygame.draw.line(s, eye, (fx + d - 3, top - 112), (fx + d + 3, top - 112), 2)
    for x, y, w in ((fx - 34, top - 104, 14), (fx + 6, top - 58, 10)):   # moss
        pygame.draw.line(s, MOSS, (x, y), (x + w, y), 3)
    for x, y, h in ((fx + 54, top - 104, 12), (fx - 52, top - 106, 10), (fx - 20, fy - 46, 9)):   # crystals
        _poly(s, (150, 120, 255), [(x, y - h), (x + 3, y - h // 3), (x, y), (x - 3, y - h // 3)], (75, 60, 128), 1)
    cr = [(fx - 18, top - 128), (fx - 16, top - 142), (fx - 9, top - 134), (fx - 2, top - 148), (fx + 5, top - 134),
          (fx + 12, top - 144), (fx + 18, top - 128)]   # a crown of jagged rock, studded with crystal
    _poly(s, (150, 140, 120), cr, (80, 72, 60), 2)
    for x, y, col in ((fx - 2, top - 136, SAPPHIRE), (fx - 12, top - 132, (150, 120, 255)),
                      (fx + 10, top - 133, (80, 220, 120))):
        pygame.draw.circle(s, col, (x, y), 2)


VOID, VOID_RIM, VIOLET = (14, 10, 28), (78, 58, 120), (175, 120, 255)
# The Void Maw's eyes: (x, y from its feet in canvas px, radius). One opens at a time: the weak point.
VOID_EYES = [(-36, -92, 6), (-12, -108, 5), (20, -104, 8), (42, -86, 5), (-48, -64, 5), (50, -52, 5),
             (-4, -82, 5), (30, -76, 5)]


def void_eye_screen(e, rise):
    """Screen position and radius of the Void Maw's open eye, or None while they're all shut."""
    if getattr(e, "eye", None) is None:
        return None
    fx, fy = _feet(e, rise)
    ex, ey, r = VOID_EYES[e.eye]
    k = e.draw_scale or 1
    return fx + ex * k, fy + ey * k, r * k


@_drawer
def draw_void_maw(s, e, rise, t, hovered, dy, pos):
    """The Void Maw: a mass of darkness rising out of its pool, tendrils lashing; one pale eye open at a time,
    and a vast toothed maw that gapes as it winds up."""
    fx, fy = _feet(e, rise)
    fy += dy
    c = _charge(e)
    if hovered:
        _hovered(s, fx, fy, 150)
    _shadow(s, fx, fy, 146)
    pool = pygame.Surface((160, 30), pygame.SRCALPHA)
    pygame.draw.ellipse(pool, (6, 4, 14, 210), (0, 4, 160, 22))
    pygame.draw.ellipse(pool, (*VIOLET, 70), (0, 4, 160, 22), 2)
    s.blit(pool, (fx - 80, fy - 16))
    for k, (bx, tip, ctrl) in enumerate(((-58, (-74, -46), (-72, -14)), (-40, (-62, -84), (-30, -40)),
                                         (46, (70, -62), (66, -18)), (60, (76, -24), (78, -8)))):
        wave = math.sin(e.anim_t * 2 + k * 1.7) * 6
        pts = [(fx + bx, fy - 6), (fx + ctrl[0] + wave * 0.5, fy + ctrl[1]),
               (fx + tip[0] + wave, fy + tip[1] - wave * 0.4)]
        pygame.draw.lines(s, VOID_RIM, False, pts, 7)
        pygame.draw.lines(s, VOID, False, pts, 5)
        pygame.draw.circle(s, VOID_RIM, (int(pts[-1][0]), int(pts[-1][1])), 3)
    heave = 0   # (the eyes are aimed at, so the mass doesn't bob)
    mass = [(fx - 56, fy - 8), (fx - 62, fy - 56), (fx - 48, fy - 96), (fx - 22, fy - 122), (fx + 10, fy - 128),
            (fx + 40, fy - 112), (fx + 58, fy - 78), (fx + 60, fy - 30), (fx + 52, fy - 8)]
    _poly(s, VOID, mass, VOID_RIM, 3)
    sheen = pygame.Surface(s.get_size(), pygame.SRCALPHA)
    pygame.draw.ellipse(sheen, (60, 30, 110, 90), (fx - 40, fy - 116, 70, 60))
    s.blit(sheen, (0, 0))
    gape = 44 + int(20 * c)   # the maw gapes as it winds up
    maw = pygame.Rect(fx - 40, fy - 44 - gape // 2, 84, gape)
    pygame.draw.ellipse(s, (40, 6, 24), maw)
    pygame.draw.ellipse(s, VOID_RIM, maw, 2)
    pygame.draw.ellipse(s, (8, 2, 10), maw.inflate(-30, -18))
    pygame.draw.ellipse(s, (120, 70, 190), maw.inflate(-56, -int(gape * 0.7)), 1)
    for k in range(9):   # teeth round the rim
        a = math.pi + (k + 0.5) / 9 * math.pi
        x, y = maw.centerx + math.cos(a) * 40, maw.centery + math.sin(a) * gape / 2.2
        _poly(s, (225, 220, 240), [(x - 3, y), (x + 3, y), (x, y + 8)], (120, 110, 150), 1)
        a2 = (k + 0.5) / 9 * math.pi
        x2, y2 = maw.centerx + math.cos(a2) * 40, maw.centery + math.sin(a2) * gape / 2.2
        _poly(s, (225, 220, 240), [(x2 - 3, y2), (x2 + 3, y2), (x2, y2 - 8)], (120, 110, 150), 1)
    open_eye = getattr(e, "eye", None)
    for i, (ex, ey, r) in enumerate(VOID_EYES):
        x, y = fx + ex, fy + ey + heave
        if i == open_eye:   # wide open, glowing: the one place a blow lands properly
            _glow(s, (x, y), r + 8, (220, 230, 255), 140, over=True)
            pygame.draw.ellipse(s, (235, 240, 255), (x - r, y - r * 0.7, r * 2, r * 1.4))
            pygame.draw.ellipse(s, VIOLET, (x - r * 0.45, y - r * 0.55, r * 0.9, r * 1.1))
            pygame.draw.ellipse(s, (20, 10, 40), (x - 1, y - r * 0.4, 2, r * 0.8))
        else:   # half-lidded
            pygame.draw.ellipse(s, (200, 205, 230), (x - r, y - r * 0.5, r * 2, r))
            pygame.draw.circle(s, (40, 20, 70), (int(x), int(y)), max(1, r // 2))
            pygame.draw.rect(s, VOID, (x - r - 1, y - r, r * 2 + 2, r * 0.9))
            pygame.draw.line(s, VOID_RIM, (x - r, y - r * 0.15), (x + r, y - r * 0.15), 1)
    tx, ty = fx - 6, fy - 124   # a crown of black spikes lit violet from within
    spikes = [(-22, 2), (-18, -16), (-11, -2), (-5, -24), (1, -3), (8, -20), (14, -2), (20, -12), (24, 4)]
    _poly(s, (30, 22, 46), [(tx + dx, ty + dy) for dx, dy in spikes], VIOLET, 2)
    for dx, dy in ((-5, -18), (8, -14), (-18, -10)):
        _glow(s, (tx + dx, ty + dy), 5, VIOLET, 160)
    pygame.draw.circle(s, (230, 200, 255), (int(tx + 1), int(ty - 6)), 2)


NO_FLIP = {"voidmaw"}   # (its eyes are aimed at: it stays put, facing the same way)
DRAWERS.update({"burrowbros": draw_burrow_bros, "mountain": draw_mountain, "voidmaw": draw_void_maw})
