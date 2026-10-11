"""Character sprites: miners, gravestones and enemies, plus enemy hit-testing."""
import math
import random

import pygame

from .config import BAD, BLOCK_H, GOOD, GRID, MUTED
from .dynamite import FUSE_LEN, STICK_H, STICK_STAGGER, STICK_W, fuse_points
from .enemies import (ENEMY_TYPES, FLY_ALTITUDE, PILE_SECS, TELEGRAPH_SECS, THROW_ANIM_SECS,
                      THROW_RELEASE, TRANSFORM_SECS)
from .iso import current_origin, iso, origin_at
from .miners import CRIT_ANIM_SECS, LOOK_FIELDS
from .util import shade
from .world_layout import MITTS_CLICKS

HI_VIS = (255, 140, 30)
HELMETS = {"miner": (240, 200, 40), "foreman": (245, 245, 250), "driller": (240, 130, 40),
           "guard": (62, 68, 86), "demolitionist": (200, 50, 45), "medic": (245, 245, 250)}
MEDIC_RED = (215, 45, 50)
STEEL, DIAMOND = (190, 190, 200), (110, 235, 245)   # pick head colour, before / after Diamond Tips
CRIT_SLAM = 0.3     # share of the crit animation spent slamming down (the rest is the recoil)
CRIT_WINDUP = -1.6  # pick angle at the start of a crit: raised back behind the shoulder
ENEMY_HIT_RADIUS = {"zombie": 26, "spider": 20, "bat": 20, "vampire": 26, "wisp": 16, "ghost": 24,
                    "zombieking": 54, "broodmother": 56, "vampirelord": 54, "lich": 56, "eggsac": 18,
                    "skeleton": 24, "greatbat": 54, "bonetyrant": 66,
                    "slime": 22, "slimeling": 20, "slimechunk": 26, "slimeking": 54,
                    "mimic": 20, "golem": 30, "shade": 26, "burrower": 20,
                    "burrowbros": 56, "mountain": 66, "voidmaw": 72}
BONE_COL, BONE_SHADE = (232, 226, 205), (150, 142, 120)
BOSS_CANVAS = (180, 240)   # a boss is drawn on this canvas around its feet, then scaled up
ZOMBIE_SKIN, ZOMBIE_SHIRT = (118, 168, 92), (70, 88, 130)
SPIDER_BODY = (58, 48, 70)
SLIME_GREEN, SLIME_DARK, SLIME_ANGRY = (110, 210, 90), (46, 110, 40), (230, 100, 60)
SLIME_SIZE = {"slimeling": 8, "slimechunk": 10}   # body radius (slimes, and the Slime King before scaling: 13)
BAT_BODY, BAT_WING, BAT_EDGE = (58, 44, 70), (82, 60, 100), (36, 26, 46)
VAMP_SKIN, VAMP_SUIT, VAMP_CAPE, VAMP_LINING, VAMP_HAIR = (
    (232, 230, 240), (32, 28, 40), (22, 18, 28), (160, 22, 42), (20, 18, 24))


def _lerp(a, b, t):
    return tuple(int(x + (y - x) * t) for x, y in zip(a, b))


def _feet(e, rise):
    fx, fy = iso(e.x, e.y, e.draw_z + rise)
    return int(fx), int(fy)


def _hp_bar(surf, cx, top, frac, color, width=32):
    """Health bar in team colour: green for the crew, red for monsters."""
    bar = pygame.Rect(0, 0, width, 5)
    bar.midbottom = (cx, top)
    pygame.draw.rect(surf, (20, 16, 24), bar.inflate(2, 2))
    pygame.draw.rect(surf, color, (bar.x, bar.y, int(bar.w * max(0, frac)), bar.h))


def struggle_shake(t, phase=0.0):
    return math.sin(t * 38 + phase) * 2


# ----- miners --------------------------------------------------------------
def miner_neck(m, rise, t):
    fx, fy = _feet(m, rise)
    if m.state == "grabbed":
        fx += struggle_shake(t)
    return fx, fy - 27 - m.height


def miner_head(m, rise, t):
    fx, fy = _feet(m, rise)
    if m.state == "grabbed":
        fx += struggle_shake(t)
    return fx, fy - 32 - m.height


def _draw_hair_back(surf, m, head):
    """Hair that sits behind the head (drawn before the body and face)."""
    hx, hy = head
    f = m.facing
    if m.style == "long":
        pygame.draw.rect(surf, m.hair, (hx - 8, hy - 5, 16, 14), border_radius=4)
    elif m.style == "ponytail":
        pygame.draw.line(surf, m.hair, (hx - 5 * f, hy - 3), (hx - 10 * f, hy + 5), 4)
        pygame.draw.circle(surf, m.hair, (hx - 10 * f, hy + 6), 3)


def _draw_face(surf, m, head, grabbed):
    """Sideburns, facial hair and eyes (over the face, under the helmet)."""
    hx, hy = head
    f = m.facing
    if m.style in ("short", "long", "ponytail"):
        pygame.draw.rect(surf, m.hair, (hx - 8, hy - 4, 3, 5))
        pygame.draw.rect(surf, m.hair, (hx + 5, hy - 4, 3, 5))
    if m.facial == "beard":
        pygame.draw.ellipse(surf, m.hair, (hx - 6, hy + 1, 12, 7))
    elif m.facial == "mustache":
        pygame.draw.rect(surf, m.hair, (hx - 3 + 2 * f, hy + 2, 7, 2))
    if grabbed:   # wide panicked eyes + open mouth
        pygame.draw.circle(surf, (255, 255, 255), (hx - 3, hy), 2)
        pygame.draw.circle(surf, (255, 255, 255), (hx + 3, hy), 2)
        pygame.draw.circle(surf, (40, 20, 30), (hx, hy + 4), 2)
    else:
        pygame.draw.rect(surf, (30, 24, 28), (hx + 3 * f - 1, hy - 2, 2, 2))


def _draw_mohawk(surf, m, head):
    """A spiky fin poking up through the helmet."""
    hx, hy = head
    top = hy - 9
    pygame.draw.polygon(surf, m.hair, [(hx - 6, top), (hx - 4, top - 5), (hx - 2, top - 1), (hx, top - 7),
                                       (hx + 2, top - 1), (hx + 4, top - 5), (hx + 6, top)])


def draw_climber(surf, m, fx, fy, t, style, tau, rope_x):
    """A crew member climbing a rope out of the collapsing shaft, feet at (fx, fy), the rope at rope_x. `style`
    is how they go about it (camp.CLIMB_STYLES), `tau` seconds since they grabbed on."""
    role = getattr(m, "role", "miner")
    width = 18 if role in ("driller", "guard") else 14
    lift = m.height
    phase = tau * {"scramble": 14, "steady": 8, "struggle": 5}.get(style, 7) + m.climb["phase"]
    trousers = (60, 50, 40)
    # legs: kicking, scissoring or bracing against the rope
    if style == "hauled":
        kick = math.sin(t * 22) * 4
        legs = ((fx - 3 + kick, fy), (fx + 3 - kick, fy))
    elif style == "struggle":
        kick = math.sin(t * 6) * 5
        legs = ((fx - 4 + kick, fy + 1), (fx + 4 + kick, fy))
    elif style in ("steady", "scramble", "spin"):
        legs = ((fx - 3, fy - 4 - 5 * max(0.0, math.sin(phase))), (fx + 3, fy - 4 - 5 * max(0.0, -math.sin(phase))))
    else:
        legs = ((fx - 2, fy), (fx + 3, fy - 2))
    for d, foot in zip((-3, 3), legs):
        pygame.draw.line(surf, trousers, (fx + d, fy - 10), foot, 3)
    body = pygame.Rect(fx - width // 2, fy - 26 - lift, width, 18 + lift)
    head = (fx, int(fy - 32 - lift))
    _draw_hair_back(surf, m, head)
    pygame.draw.rect(surf, m.shirt, body, border_radius=4)
    _draw_outfit(surf, m, role, body, fx)
    pygame.draw.circle(surf, m.skin, head, 7)
    _draw_face(surf, m, head, style in ("struggle", "hauled"))
    if role in HEADGEAR:
        HEADGEAR[role](surf, m, head, t)
    else:
        pygame.draw.ellipse(surf, HELMETS.get(role, HELMETS["miner"]), (head[0] - 9, head[1] - 10, 18, 9))
        pygame.draw.circle(surf, (255, 250, 200), (head[0] + 5 * m.facing, head[1] - 6), 2)
    if m.style == "mohawk":
        _draw_mohawk(surf, m, head)
    # arms: hand over hand up the rope (or hanging on with both, or one free to wave)
    top = head[1] - 12
    if style == "hauled":
        hands = [(rope_x, top - 2), (rope_x, top + 4)]
    elif style == "waver":
        hands = [(rope_x, top), (fx + 18 * m.facing, top - 4 + math.sin(t * 14) * 5)]
    else:
        hands = [(rope_x, top - 6 * math.sin(phase)), (rope_x, top + 6 * math.sin(phase))]
    for d, hand in zip((-1, 1), hands):
        shoulder = (fx + d * (width // 2 - 2), body.y + 4)
        pygame.draw.line(surf, m.shirt, shoulder, hand, 3)
        pygame.draw.circle(surf, m.skin, (int(hand[0]), int(hand[1])), 3)


def draw_rope(surf, top, bottom):
    """A climbing rope from `top` down to `bottom`, knotted every so often."""
    pygame.draw.line(surf, (120, 88, 50), top, bottom, 4)
    pygame.draw.line(surf, (170, 130, 80), (top[0] - 1, top[1]), (bottom[0] - 1, bottom[1]), 1)
    length = math.hypot(bottom[0] - top[0], bottom[1] - top[1])
    for k in range(1, int(length // 26) + 1):
        a = k * 26 / max(1.0, length)
        pygame.draw.circle(surf, (95, 68, 40), (int(top[0] + (bottom[0] - top[0]) * a),
                                                 int(top[1] + (bottom[1] - top[1]) * a)), 3)


def pick_head_color(diamond_lv):
    """Steel turning to diamond blue as Diamond Tips levels up (fully blue at its max, 10)."""
    return _lerp(STEEL, DIAMOND, min(1.0, diamond_lv / 10))


def draw_miner(surf, fonts, m, rise, t, pick_level=0, spirit=False):
    fx, fy = _feet(m, rise)
    if m.state == "down":
        if getattr(m, "ko", False):   # one of the camp's people: knocked out, not dead
            draw_knocked_out(surf, fonts, m, fx, fy, t)
        else:
            draw_grave(surf, fonts, fx, fy, m.respawn)
        return
    grabbed = m.state == "grabbed"
    if getattr(m, "role", "") == "claygolem":   # Mitts is a shape all their own
        draw_clay_golem(surf, fonts, m, fx, fy, t, grabbed)
        return
    lift = m.height
    timer = getattr(m, "crit", 0.0)
    crit = 1 - timer / CRIT_ANIM_SECS if timer > 0 and not grabbed else None   # 0..1 through a crit
    pygame.draw.ellipse(surf, (16, 12, 20), (fx - 11, fy - 4, 22, 8))
    if grabbed:
        fx += struggle_shake(t)
        kick = math.sin(t * 22) * 4                       # legs kicking
        pygame.draw.line(surf, (60, 50, 40), (fx - 3, fy - 9), (fx - 3 + kick, fy - 1), 3)
        pygame.draw.line(surf, (60, 50, 40), (fx + 3, fy - 9), (fx + 3 - kick, fy - 1), 3)
        bob = 0
    elif crit is not None and crit > CRIT_SLAM:   # recoil: the whole miner bounces off the impact
        bob = math.sin((crit - CRIT_SLAM) / (1 - CRIT_SLAM) * math.pi) * 7
    elif getattr(m, "task", "") == "planting":    # demolitionist kneeling over a charge
        bob = -6
    else:
        bob = abs(math.sin(t * 10)) * 2 if m.anim == 0 else 0
    role = getattr(m, "role", "miner")
    foreman = role == "foreman"
    width = 18 if role in ("driller", "guard") else 14   # drillers and guards are built broad
    body = pygame.Rect(fx - width // 2, fy - 26 - bob - lift, width, 18 + lift + min(0, bob))
    head = (fx, int(fy - 32 - bob - lift))
    _draw_hair_back(surf, m, head)
    if role == "hero":   # a cape, stirring behind them
        sway = math.sin(t * 3 + m.x) * 2
        pygame.draw.polygon(surf, (180, 36, 46), [(fx - 6, body.y + 2), (fx + 6, body.y + 2),
                                                  (fx + 8 - 4 * m.facing + sway, fy - 5), (fx - 8 - 4 * m.facing + sway, fy - 5)])
    elif role == "archer":   # a quiver of arrows on their back
        qx = fx - 8 * m.facing
        pygame.draw.rect(surf, (110, 70, 40), (qx - 2, body.y - 3, 5, 15), border_radius=2)
        for k in range(3):
            pygame.draw.line(surf, (240, 240, 235), (qx - 1 + k * 2, body.y - 3), (qx - 2 + k * 2, body.y - 7), 1)
    pygame.draw.rect(surf, m.shirt, body, border_radius=4)
    _draw_outfit(surf, m, role, body, fx)
    pygame.draw.rect(surf, (60, 50, 40), (fx - width // 2, fy - 10 - max(0, bob), width, 8), border_radius=2)
    # choked purple / venom green / drained pale, depending on who has hold of them
    tint = m.attacker.spec["tint"] if grabbed and m.attacker else m.skin
    skin = _lerp(m.skin, tint, 1 - m.hp / m.max_hp) if grabbed else m.skin
    pygame.draw.circle(surf, skin, head, 7)
    _draw_face(surf, m, head, grabbed)
    if role == "driller" and not grabbed:   # safety goggles
        for d in (-3, 3):
            pygame.draw.circle(surf, (150, 200, 230), (head[0] + d + m.facing, head[1] - 1), 2)
        pygame.draw.line(surf, (60, 60, 70), (head[0] - 7, head[1] - 1), (head[0] + 7, head[1] - 1), 1)
    if role in HEADGEAR:   # the camp's people wear their own
        HEADGEAR[role](surf, m, head, t)
    else:
        pygame.draw.ellipse(surf, HELMETS.get(role, HELMETS["miner"]), (head[0] - 9, head[1] - 10, 18, 9))
    if foreman:
        pygame.draw.line(surf, HI_VIS, (head[0] - 6, head[1] - 7), (head[0] + 6, head[1] - 7), 2)
    elif role == "medic":   # a red cross on the front of the helmet
        pygame.draw.line(surf, MEDIC_RED, (head[0] - 2 * m.facing, head[1] - 9), (head[0] - 2 * m.facing, head[1] - 4), 2)
        pygame.draw.line(surf, MEDIC_RED, (head[0] - 2 * m.facing - 2, head[1] - 7),
                         (head[0] - 2 * m.facing + 2, head[1] - 7), 2)
    lamp = (head[0] + 5 * m.facing, head[1] - 6)
    if role in HEADGEAR:
        pass
    elif getattr(m, "shaded", False):   # an Abyssal Shade's darkness: the lamp gutters out
        pygame.draw.circle(surf, (70, 66, 80), lamp, 2)
    elif role == "guard":   # a proper lantern on the helmet, glowing
        pygame.draw.circle(surf, (255, 220, 120), lamp, 4)
        pygame.draw.circle(surf, (255, 255, 230), lamp, 2)
    elif spirit:   # Spirit Lantern: a cold blue light that keeps spirits from fading
        pygame.draw.circle(surf, (120, 200, 255), lamp, 4)
        pygame.draw.circle(surf, (225, 245, 255), lamp, 2)
    else:
        pygame.draw.circle(surf, (255, 250, 200), lamp, 2)
    if m.style == "mohawk":
        _draw_mohawk(surf, m, head)
    if foreman:
        _draw_clipboard(surf, m, fx, fy - bob - lift, skin, grabbed, t)
    elif role == "medic":
        _draw_medkit(surf, m, fx, fy - bob - lift, skin, grabbed, t)
    elif role == "driller":
        _draw_jackhammer(surf, m, fx, fy - max(0, bob), grabbed, t)
    elif role == "demolitionist":
        _draw_charge_stick(surf, m, fx, fy - bob - lift, skin, grabbed, t)
    elif role == "engineer":
        _draw_hammer(surf, m, fx, fy - bob - lift, grabbed, t)
    elif role == "archer":
        _draw_bow(surf, m, fx, fy - bob - lift, grabbed, t)
    elif role == "taxman":
        _draw_ledger(surf, m, fx, fy - bob - lift, grabbed, t)
    else:
        # pickaxe: normal swing, flailing wildly while grabbed, or a crit's overhead slam
        # (rests raised in front of the miner so it doesn't hide their face)
        hx, hy = fx + 7 * m.facing, fy - 20 - bob - lift
        head_col = (250, 205, 70) if role == "hero" else pick_head_color(pick_level)   # (the hero's: gold)
        if getattr(m, "forged", 0) > 0:   # rigged by the Goblin Engineer: glowing with the charge in it
            head_col = _lerp(head_col, (255, 130, 50), 0.55 + 0.25 * math.sin(t * 6 + m.x))
        if grabbed:
            ang = math.sin(t * 16) * 1.4
        elif crit is not None and crit <= CRIT_SLAM:   # slam: from behind the head down into the block
            q = crit / CRIT_SLAM
            ang = (CRIT_WINDUP + (2.4 - CRIT_WINDUP) * q) * m.facing
            for k in range(1, 4):   # motion trail along the arc
                ta = (CRIT_WINDUP + (2.4 - CRIT_WINDUP) * max(0.0, q - k * 0.12)) * m.facing
                tx, ty = hx + math.sin(ta) * 20, hy - math.cos(ta) * 20
                pygame.draw.line(surf, _lerp((255, 220, 150), (60, 50, 70), k / 4), (hx, hy), (tx, ty), 2)
        elif crit is not None:   # stuck in the block, shuddering
            ang = (2.3 + math.sin(crit * 70) * 0.12 * (1 - crit)) * m.facing
        else:
            ang = (0.35 + m.anim * 2.0) * m.facing
        ex, ey = hx + math.sin(ang) * 18, hy - math.cos(ang) * 18
        pygame.draw.line(surf, (120, 82, 44), (hx, hy), (ex, ey), 3)
        if role == "guard":   # a guard swings a shovel, not a pick
            d = (math.sin(ang), -math.cos(ang))
            p = (math.cos(ang) * 4, math.sin(ang) * 4)
            blade = [(ex - p[0], ey - p[1]), (ex + p[0], ey + p[1]),
                     (ex + p[0] + d[0] * 8, ey + p[1] + d[1] * 8), (ex - p[0] + d[0] * 8, ey - p[1] + d[1] * 8)]
            pygame.draw.polygon(surf, (150, 150, 160), blade)
            pygame.draw.polygon(surf, (90, 90, 100), blade, 1)
            tips = ()
        else:
            perp = (math.cos(ang) * 8, math.sin(ang) * 8)
            tips = ((ex - perp[0], ey - perp[1]), (ex + perp[0], ey + perp[1]))
            pygame.draw.line(surf, head_col, tips[0], tips[1], 3)
        if getattr(m, "sharp", 0) > 0 and tips:   # freshly sharpened at the Whetstone: edge gleams
            pygame.draw.line(surf, (235, 250, 255), tips[0], tips[1], 1)
            if int(t * 8 + m.x * 5) % 3 == 0:
                pygame.draw.circle(surf, (255, 255, 255), (int(tips[1][0]), int(tips[1][1])), 2)
        if pick_level >= 5:   # diamond tips glint
            for i, (gx, gy) in enumerate(tips):
                if math.sin(t * 5 + i * 2.1 + m.x * 3) > 0.75:
                    pygame.draw.circle(surf, (255, 255, 255), (int(gx), int(gy)), 2)
    if getattr(m, "coffee", 0) > 0 and not grabbed:   # Coffee Break: a steaming mug in the other hand
        mx, my = int(fx - 8 * m.facing), int(fy - 18 - bob - lift)
        pygame.draw.rect(surf, (240, 236, 228), (mx - 3, my - 3, 6, 6), border_radius=1)
        pygame.draw.rect(surf, (120, 70, 40), (mx - 2, my - 2, 4, 2))
        pygame.draw.arc(surf, (240, 236, 228), (mx - 3 - 3 * m.facing, my - 2, 4, 4), 0, math.tau, 1)
        for k in range(2):   # curls of steam
            sy = my - 5 - ((t * 14 + k * 5) % 10)
            pygame.draw.circle(surf, (225, 225, 235), (mx - 1 + k * 2 + int(math.sin(t * 6 + k) * 1.5), int(sy)), 1)
    if m.hp < m.max_hp:
        _hp_bar(surf, fx, fy - 46 - lift, m.hp / m.max_hp, GOOD, 26)
    if grabbed and int(t * 4) % 2 == 0:
        img = fonts[26].render("!!", True, BAD)
        surf.blit(img, img.get_rect(midbottom=(fx, fy - 50 - lift)))


def _draw_outfit(surf, m, role, body, fx):
    """Role clothing over the shirt."""
    if role == "foreman":   # hi-vis vest with a reflective stripe, open at the front
        vest = pygame.Rect(body.x, body.y + 1, body.w, body.h - 9)
        pygame.draw.rect(surf, HI_VIS, vest, border_radius=3)
        pygame.draw.rect(surf, (255, 245, 200), (vest.x, vest.centery, vest.w, 3))
        pygame.draw.line(surf, m.shirt, (fx, vest.y), (fx, vest.y + 6), 2)
    elif role == "driller":   # heavy work jacket, shirt collar showing
        jacket = pygame.Rect(body.x, body.y + 3, body.w, body.h - 11)
        pygame.draw.rect(surf, (125, 85, 50), jacket, border_radius=4)
        pygame.draw.line(surf, (90, 60, 35), (fx, jacket.y), (fx, jacket.bottom), 1)
        pygame.draw.rect(surf, (200, 200, 205), (jacket.x, jacket.centery + 2, jacket.w, 2))
    elif role == "guard":   # navy uniform with a gold badge and a belt
        coat = pygame.Rect(body.x, body.y, body.w, body.h - 8)
        pygame.draw.rect(surf, (52, 62, 100), coat, border_radius=4)
        pygame.draw.circle(surf, (255, 205, 70), (fx - 4 * m.facing, coat.y + 6), 2)
        pygame.draw.line(surf, (30, 30, 40), (coat.x, coat.bottom - 2), (coat.right - 1, coat.bottom - 2), 2)
    elif role == "medic":   # white coat with a red cross on the chest
        coat = pygame.Rect(body.x, body.y, body.w, body.h - 7)
        pygame.draw.rect(surf, (238, 240, 244), coat, border_radius=4)
        pygame.draw.line(surf, (190, 195, 205), (fx, coat.y + 1), (fx, coat.bottom - 1), 1)
        cx, cy = fx + 3 * m.facing, coat.y + 6
        pygame.draw.line(surf, MEDIC_RED, (cx, cy - 3), (cx, cy + 3), 2)
        pygame.draw.line(surf, MEDIC_RED, (cx - 3, cy), (cx + 3, cy), 2)
    elif role == "hero":   # a polished breastplate, gold-trimmed, and a belt
        plate = pygame.Rect(body.x + 1, body.y + 2, body.w - 2, body.h - 10)
        pygame.draw.rect(surf, (200, 205, 216), plate, border_radius=3)
        pygame.draw.rect(surf, (240, 196, 60), plate, 1, border_radius=3)
        pygame.draw.line(surf, (60, 40, 30), (body.x, body.bottom - 8), (body.right - 1, body.bottom - 8), 2)
    elif role == "engineer":   # a scorched leather apron on straps
        apron = pygame.Rect(body.x + 2, body.y + 4, body.w - 4, body.h - 6)
        pygame.draw.rect(surf, (96, 66, 42), apron, border_radius=2)
        for d in (-1, 1):
            pygame.draw.line(surf, (70, 48, 30), (fx + d * 4, body.y), (fx + d * 3, apron.y), 1)
        pygame.draw.circle(surf, (40, 30, 26), (fx - 2, apron.centery + 2), 1)
    elif role == "archer":   # a tunic belted at the waist, the quiver's strap across it
        pygame.draw.line(surf, (90, 60, 30), (body.x + 1, body.y + 2), (body.right - 2, body.bottom - 9), 2)
        pygame.draw.line(surf, (60, 40, 25), (body.x, body.bottom - 8), (body.right - 1, body.bottom - 8), 2)
    elif role == "taxman":   # a black waistcoat, gold buttons and a watch chain
        coat = pygame.Rect(body.x + 2, body.y + 2, body.w - 4, body.h - 9)
        pygame.draw.rect(surf, (34, 28, 40), coat, border_radius=2)
        for k in range(3):
            pygame.draw.circle(surf, (240, 200, 70), (fx, coat.y + 3 + k * 4), 1)
        pygame.draw.arc(surf, (240, 200, 70), (fx - 1, coat.y + 6, 6, 5), math.pi, math.tau, 1)
    elif role == "demolitionist":   # leather vest with a bandolier of dynamite
        vest = pygame.Rect(body.x, body.y + 1, body.w, body.h - 9)
        pygame.draw.rect(surf, (115, 75, 45), vest, border_radius=3)
        pygame.draw.line(surf, m.shirt, (fx, vest.y), (fx, vest.bottom), 3)
        for i in range(3):   # sticks along a strap from shoulder to hip
            sx, sy = vest.x + 2 + i * 4, vest.y + 2 + i * 3
            pygame.draw.rect(surf, (210, 40, 40), (sx, sy, 3, 5))


def _draw_jackhammer(surf, m, fx, base, grabbed, t):
    """A pneumatic drill held upright in front; rattles and sparks while drilling."""
    f = m.facing
    drilling = m.anim > 0.3 and not grabbed
    jx = fx + 9 * f + (math.sin(t * 90) * 1.2 if drilling else 0) + (struggle_shake(t) if grabbed else 0)
    top = base - 26 + (math.sin(t * 70) * 1 if drilling else 0)
    pygame.draw.line(surf, (40, 40, 48), (jx - 5, top), (jx + 5, top), 3)            # T-handle
    pygame.draw.rect(surf, (120, 122, 132), (jx - 3, top + 1, 7, 13), border_radius=2)  # motor body
    pygame.draw.rect(surf, (230, 150, 50), (jx - 3, top + 5, 7, 3))                   # warning band
    pygame.draw.line(surf, (200, 200, 210), (jx, top + 14), (jx, base - 1), 2)        # chisel bit
    if drilling and math.sin(t * 40) > 0.3:
        pygame.draw.circle(surf, (255, 230, 140), (int(jx + math.sin(t * 77) * 3), int(base - 1)), 1)


def _draw_charge_stick(surf, m, fx, top, skin, grabbed, t):
    """A demolitionist holds a stick of dynamite; kneeling, it goes down onto the block."""
    f = m.facing
    planting = getattr(m, "task", "") == "planting"
    if grabbed:
        cx, cy = fx + 8 * f + math.sin(t * 16) * 5, top - 28
    elif planting:
        cx, cy = fx + 9 * f, top - 4
    else:
        cx, cy = fx + 8 * f, top - 17
    pygame.draw.rect(surf, (210, 40, 40), (cx - 2, cy - 5, 5, 10), border_radius=2)
    pygame.draw.line(surf, (70, 58, 46), (cx, cy - 5), (cx + 2 * f, cy - 9), 1)
    if planting and int(t * 12) % 2:
        pygame.draw.circle(surf, (255, 220, 120), (int(cx + 2 * f), int(cy - 9)), 2)
    pygame.draw.circle(surf, skin, (int(cx), int(cy + 3)), 2)


def _draw_medkit(surf, m, fx, top, skin, grabbed, t):
    """The medic's first-aid bag: carried at the side, held out over a patient, swung when grabbed."""
    f = m.facing
    if grabbed:   # swinging the bag at the monster
        ang = math.sin(t * 16) * 1.3
        cx, cy = fx + 8 * f + math.sin(ang) * 10, top - 24 - math.cos(ang) * 8
    elif m.anim > 0.2:   # treating someone: bag held out, a hand in it
        cx, cy = fx + 11 * f, top - 18 + math.sin(t * 9) * 1.5
    else:
        cx, cy = fx + 8 * f, top - 12
    bag = pygame.Rect(0, 0, 11, 8)
    bag.center = (int(cx), int(cy))
    pygame.draw.arc(surf, (120, 30, 34), (bag.centerx - 3, bag.y - 4, 7, 7), 0, math.pi, 2)
    pygame.draw.rect(surf, MEDIC_RED, bag, border_radius=2)
    pygame.draw.line(surf, (255, 255, 255), (bag.centerx, bag.y + 1), (bag.centerx, bag.bottom - 2), 2)
    pygame.draw.line(surf, (255, 255, 255), (bag.centerx - 2, bag.centery), (bag.centerx + 2, bag.centery), 2)
    pygame.draw.circle(surf, skin, (int(cx - 3 * f), int(cy - 3)), 2)


def draw_ghost(surf, fonts, g, rise, t, pick_level=0):
    """Graveyard Shift: a fallen crew member back at work, pale blue and see-through, drifting a little."""
    fx, fy = _feet(g, rise)
    img = pygame.Surface((96, 104), pygame.SRCALPHA)
    ox, oy = current_origin()
    with origin_at((ox + 48 - fx, oy + 88 - fy - 4 - math.sin(t * 2 + g.x * 3) * 2)):
        draw_miner(img, fonts, g, rise, t, pick_level)
    img = pygame.transform.grayscale(img)
    img.fill((150, 195, 255), special_flags=pygame.BLEND_RGB_MULT)
    img.fill((60, 70, 90), special_flags=pygame.BLEND_RGB_ADD)
    img.set_alpha(150)
    surf.blit(img, (fx - 48, fy - 88))
    for k in range(3):   # a few motes of cold light trailing off them
        a = t * 1.5 + k * 2.1 + g.y
        pygame.draw.circle(surf, (190, 225, 255), (int(fx + math.sin(a) * 9), int(fy - 20 - (a * 9) % 30)), 1)


def _draw_clipboard(surf, m, fx, top, skin, grabbed, t):
    """The foreman's clipboard: held at the chest, a finger jabbed out when barking, waved when grabbed."""
    f = m.facing
    if grabbed:   # swatting at the monster with it
        ang = math.sin(t * 16) * 1.3
        cx, cy = fx + 7 * f + math.sin(ang) * 10, top - 26 - math.cos(ang) * 8
    else:
        cx, cy = fx + 6 * f, top - 18
    board = pygame.Rect(0, 0, 10, 12)
    board.center = (int(cx), int(cy))
    pygame.draw.rect(surf, (150, 105, 60), board, border_radius=2)
    pygame.draw.rect(surf, (245, 245, 240), board.inflate(-4, -4))
    for i in range(2):   # scribbled lines on the paper
        ly = board.y + 5 + i * 3
        pygame.draw.line(surf, (120, 120, 140), (board.x + 3, ly), (board.right - 3, ly))
    pygame.draw.rect(surf, (170, 170, 180), (board.centerx - 2, board.y - 1, 5, 3))
    if m.anim > 0.2 and not grabbed:   # pointing at whoever is being told off
        sx, sy = fx - 4 * f, top - 21
        tip = (sx - 13 * f, sy - 5)
        pygame.draw.line(surf, m.shirt, (sx, sy), tip, 3)
        pygame.draw.circle(surf, skin, tip, 2)


class _Portrait:
    """Stand-in for a miner built from a saved look (works for the living and the dead)."""

    def __init__(self, look):
        for field in LOOK_FIELDS:
            value = look[field]
            setattr(self, field, tuple(value) if isinstance(value, list) else value)
        self.role = look.get("role", "miner")
        self.x = self.y = self.draw_z = 0.0
        self.state, self.attacker, self.anim, self.facing = "working", None, 0.25, 1
        self.hp = self.max_hp = 1.0
        self.respawn = 0.0


def draw_portrait(surf, fonts, look, center, dead=False, pick_level=0):
    """A miner standing still, for the Crew page. The dead are shown faded and in greyscale."""
    img = pygame.Surface((64, 72), pygame.SRCALPHA)
    with origin_at((32, 64)):
        draw_miner(img, fonts, _Portrait(look), 0, 0.0, pick_level)
    if dead:
        img = pygame.transform.grayscale(img)
        img.set_alpha(170)
    surf.blit(img, img.get_rect(center=center))


# ----- the camp's people (Base Camp hires) ----------------------------------------------------------------------
def _hero_helmet(surf, m, head, t):
    """The Hero Miner: a gilded helmet with a red plume, its lamp lit."""
    hx, hy = head
    f = m.facing
    pygame.draw.polygon(surf, (210, 40, 46), [(hx - 1 * f, hy - 10), (hx - 7 * f, hy - 20), (hx - 12 * f, hy - 15),
                                              (hx - 5 * f, hy - 8)])
    pygame.draw.ellipse(surf, (240, 196, 60), (hx - 9, hy - 11, 18, 10))
    pygame.draw.line(surf, (190, 140, 30), (hx - 8, hy - 5), (hx + 8, hy - 5), 2)
    pygame.draw.circle(surf, (255, 250, 200), (hx + 5 * f, hy - 7), 2)


def _goblin_cap(surf, m, head, t):
    """The Goblin Engineer: big pointed ears, a leather cap and goggles pushed up on it."""
    hx, hy = head
    for d in (-1, 1):
        pygame.draw.polygon(surf, m.skin, [(hx + d * 6, hy - 3), (hx + d * 15, hy - 8), (hx + d * 6, hy + 2)])
        pygame.draw.line(surf, _lerp(m.skin, (0, 0, 0), 0.3), (hx + d * 7, hy - 2), (hx + d * 12, hy - 6), 1)
    pygame.draw.ellipse(surf, (90, 60, 40), (hx - 8, hy - 10, 16, 8))
    for d in (-3, 3):
        pygame.draw.circle(surf, (200, 160, 70), (hx + d, hy - 7), 2)
        pygame.draw.circle(surf, (150, 220, 230), (hx + d, hy - 7), 1)


def _archer_hood(surf, m, head, t):
    """The Archer: a green hood with a point at the back, and a feather."""
    hx, hy = head
    f = m.facing
    hood = (58, 100, 50)
    pygame.draw.polygon(surf, hood, [(hx - 6 * f, hy - 8), (hx - 14 * f, hy - 13), (hx - 9 * f, hy - 2)])
    pygame.draw.polygon(surf, hood, [(hx - 7 * f, hy - 4), (hx - 9 * f, hy + 7), (hx - 2 * f, hy + 5)])
    pygame.draw.ellipse(surf, hood, (hx - 9, hy - 11, 18, 10))
    pygame.draw.line(surf, (230, 70, 50), (hx + 2 * f, hy - 10), (hx + 7 * f, hy - 17), 2)


def _top_hat(surf, m, head, t):
    """The Tax Collector: a tall black hat and a monocle on a chain."""
    hx, hy = head
    f = m.facing
    pygame.draw.rect(surf, (28, 22, 30), (hx - 6, hy - 22, 12, 14))
    pygame.draw.rect(surf, (140, 30, 50), (hx - 6, hy - 12, 12, 3))
    pygame.draw.ellipse(surf, (28, 22, 30), (hx - 10, hy - 10, 20, 5))
    pygame.draw.circle(surf, (230, 230, 240), (hx + 3 * f, hy), 3, 1)
    pygame.draw.line(surf, (240, 200, 70), (hx + 3 * f, hy + 3), (hx + 1 * f, hy + 9), 1)


MITTS_HOP_PX = 70   # how high Mitts goes at the top of a leap


def draw_clay_golem(surf, fonts, m, fx, fy, t, grabbed):
    """Mitts the Clay Golem: a lumpy, lumbering body of river clay, a glowing rune on its chest, eyes like coals,
    and two huge fists - hanging at its sides, or raised overhead as it winds up a slam."""
    clay, dark, light = (186, 116, 74), (132, 80, 50), (214, 150, 104)
    if getattr(m, "fired", False):   # out of the Kiln: deep terracotta, glazed to a shine
        clay, dark, light = (168, 84, 52), (98, 44, 28), (236, 170, 120)
    if grabbed:
        fx += struggle_shake(t)
    leaping = getattr(m, "task", "") == "leaping"
    up = m.anim if leaping else 0.0
    walk = math.sin(t * 6 + m.x * 3) * 2 if getattr(m, "strolling", False) and not leaping else 0.0
    hop = getattr(m, "hop", 0.0)
    sw = 34 - 14 * hop   # (the shadow shrinks as he goes up)
    pygame.draw.ellipse(surf, (16, 12, 20), (fx - sw / 2, fy - 5 + 2 * hop, sw, 10 - 4 * hop))
    fy -= int(hop * MITTS_HOP_PX)
    for d in (-1, 1):   # stumpy legs
        pygame.draw.rect(surf, dark, (fx + d * 7 - 5, fy - 12 + (walk * d if d > 0 else -walk * d) * 0.5, 10, 12),
                         border_radius=4)
    body = pygame.Rect(fx - 15, fy - 40, 30, 30)
    pygame.draw.ellipse(surf, dark, body.inflate(4, 4))
    pygame.draw.ellipse(surf, clay, body)
    pygame.draw.ellipse(surf, light, (body.x + 5, body.y + 4, 12, 8))   # (a sheen of wet clay)
    for a, b in (((fx - 9, fy - 30), (fx - 4, fy - 22)), ((fx + 6, fy - 36), (fx + 10, fy - 28))):   # cracks
        pygame.draw.line(surf, dark, a, b, 1)
    glow = 0.5 + 0.5 * math.sin(t * 3 + m.x)
    rune = (int(120 + 100 * glow), int(200 + 40 * glow), 255)
    pygame.draw.circle(surf, rune, (fx, fy - 26), 4, 1)
    pygame.draw.line(surf, rune, (fx, fy - 31), (fx, fy - 21), 1)
    head = pygame.Rect(fx - 8, fy - 52, 16, 13)
    pygame.draw.rect(surf, dark, head.inflate(2, 2), border_radius=5)
    pygame.draw.rect(surf, clay, head, border_radius=5)
    pygame.draw.line(surf, dark, (head.x + 2, head.y + 4), (head.right - 2, head.y + 4), 2)   # a heavy brow
    for d in (-3, 3):
        pygame.draw.circle(surf, (255, 190, 90), (fx + d + m.facing, head.y + 7), 2)
    glazed = getattr(m, "glazed", False)   # (Glazed Fists: fired a second time, in deep blue)
    for d in (-1, 1):   # the fists: down at its sides, or up overhead
        shoulder = (fx + d * 14, fy - 34)
        fist = (fx + d * (19 - 9 * up), fy - 14 - (46 * up) + (math.sin(t * 16) * 4 if grabbed else 0))
        pygame.draw.line(surf, dark, shoulder, fist, 8)
        pygame.draw.circle(surf, (34, 62, 120) if glazed else dark, (int(fist[0]), int(fist[1])), 8)
        pygame.draw.circle(surf, (66, 120, 200) if glazed else clay, (int(fist[0]), int(fist[1])), 7)
        if glazed:   # (a shine on the glaze)
            pygame.draw.circle(surf, (190, 220, 255), (int(fist[0]) - 2, int(fist[1]) - 3), 2)
    if m.hp < m.max_hp:
        _hp_bar(surf, fx, fy - 58, m.hp / m.max_hp, GOOD, 30)
    if not leaping and getattr(m, "clicks", None) is not None:   # a pip per click of yours towards his next leap
        _mitts_pips(surf, fx, fy - (66 if m.hp < m.max_hp else 60), getattr(m, "clicks", 0), t, grabbed)


def _mitts_pips(surf, x, y, clicks, t, grabbed=False):
    """Mitts' click meter: MITTS_CLICKS little pips over his head, lit one per click (all of them pulsing once
    he's ready to go and just waiting to be let loose) - greyed while something has hold of him: he isn't listening."""
    full = clicks >= MITTS_CLICKS and not grabbed
    pulse = 0.5 + 0.5 * math.sin(t * 10)
    gap = 6
    for i in range(MITTS_CLICKS):
        px = int(x - (MITTS_CLICKS - 1) * gap / 2 + i * gap)
        pygame.draw.circle(surf, (24, 16, 14), (px, y), 4)   # (a dark rim: it has to read over lava and ore)
        if i < clicks:
            col = (120, 112, 106) if grabbed else (255, int(190 + 50 * pulse), 110) if full else (230, 160, 100)
            pygame.draw.circle(surf, col, (px, y), 3)
        else:
            pygame.draw.circle(surf, (90, 60, 44), (px, y), 2)


def _golem_brow(surf, m, head, t):
    """(Mitts on a rope: a clay brow and coal eyes in place of a helmet.)"""
    hx, hy = head
    pygame.draw.line(surf, (132, 80, 50), (hx - 7, hy - 4), (hx + 7, hy - 4), 3)
    for d in (-3, 3):
        pygame.draw.circle(surf, (255, 190, 90), (hx + d, hy - 1), 2)


HEADGEAR = {"claygolem": _golem_brow, "hero": _hero_helmet, "engineer": _goblin_cap, "archer": _archer_hood, "taxman": _top_hat}


def _draw_hammer(surf, m, fx, base, grabbed, t):
    """The goblin's hammer (and, hard at work rigging a pick, the little anvil set down beside them)."""
    f = m.facing
    if getattr(m, "task", "") == "forging":
        ax, ay = fx + 12 * f, base + 26 + (-3 if m.height < 0 else 0)
        pygame.draw.polygon(surf, (70, 70, 80), [(ax - 6, ay - 6), (ax + 6, ay - 6), (ax + 3, ay - 2), (ax + 4, ay + 2),
                                                 (ax - 4, ay + 2), (ax - 3, ay - 2)])
        pygame.draw.line(surf, (110, 110, 120), (ax - 6, ay - 6), (ax + 6, ay - 6), 1)
    hx, hy = fx + 7 * f, base - 20
    ang = math.sin(t * 16) * 1.4 if grabbed else (0.35 + m.anim * 2.0) * f
    ex, ey = hx + math.sin(ang) * 14, hy - math.cos(ang) * 14
    pygame.draw.line(surf, (120, 82, 44), (hx, hy), (ex, ey), 3)
    perp = (math.cos(ang) * 5, math.sin(ang) * 5)
    pygame.draw.line(surf, (90, 92, 104), (ex - perp[0], ey - perp[1]), (ex + perp[0], ey + perp[1]), 6)


def _draw_bow(surf, m, fx, base, grabbed, t):
    """The Archer's longbow, held out in front: the string drawn back (an arrow nocked) as they take aim."""
    f = m.facing
    x, y = fx + 9 * f, base - 20
    if grabbed:
        y += math.sin(t * 16) * 4
    rect = pygame.Rect(x - 6, y - 13, 12, 26)
    start, end = (-math.pi / 2, math.pi / 2) if f > 0 else (math.pi / 2, 3 * math.pi / 2)
    pygame.draw.arc(surf, (130, 85, 45), rect, start, end, 3)
    top, bottom = (x, y - 13), (x, y + 13)
    pull = 0 if grabbed else m.anim * 8
    nock = (x - pull * f, y)
    pygame.draw.line(surf, (230, 230, 220), top, nock, 1)
    pygame.draw.line(surf, (230, 230, 220), nock, bottom, 1)
    if pull > 1:   # an arrow on the string
        pygame.draw.line(surf, (150, 110, 60), nock, (nock[0] + 16 * f, y), 2)
        pygame.draw.polygon(surf, (200, 200, 210), [(nock[0] + 16 * f, y - 2), (nock[0] + 20 * f, y),
                                                    (nock[0] + 16 * f, y + 2)])


def _draw_ledger(surf, m, fx, base, grabbed, t):
    """The Tax Collector's ledger, and the quill scratching in it while they write."""
    f = m.facing
    x, y = fx + 8 * f, base - 20
    if grabbed:
        y += math.sin(t * 16) * 4
    pygame.draw.rect(surf, (120, 30, 40), (x - 5, y - 4, 10, 8), border_radius=1)
    pygame.draw.line(surf, (240, 236, 220), (x - 4, y + 3), (x + 4, y + 3), 1)
    if m.anim > 0 and not grabbed:
        qx = x + math.sin(t * 14) * 3
        pygame.draw.line(surf, (245, 245, 245), (qx, y - 2), (qx + 4 * f, y - 10), 2)


def draw_knocked_out(surf, fonts, m, fx, fy, t):
    """One of the camp's people, out cold on the ground, stars circling - back up in a few seconds."""
    pygame.draw.ellipse(surf, (16, 12, 20), (fx - 18, fy - 5, 36, 9))
    pygame.draw.rect(surf, (60, 50, 40), (fx + 4, fy - 8, 12, 6), border_radius=2)
    pygame.draw.rect(surf, m.shirt, (fx - 10, fy - 10, 16, 8), border_radius=3)
    head = (fx - 15, fy - 7)
    pygame.draw.circle(surf, m.skin, head, 7)
    for d in (-3, 3):   # x_x
        pygame.draw.line(surf, (30, 24, 28), (head[0] + d - 1, head[1] - 3), (head[0] + d + 1, head[1] - 1), 1)
        pygame.draw.line(surf, (30, 24, 28), (head[0] + d + 1, head[1] - 3), (head[0] + d - 1, head[1] - 1), 1)
    for k in range(3):   # stars going round
        a = t * 4 + k * math.tau / 3
        sx, sy = head[0] + math.cos(a) * 11, head[1] - 14 + math.sin(a) * 4
        pygame.draw.circle(surf, (255, 230, 120), (int(sx), int(sy)), 2)
    img = fonts[18].render(f"KO {math.ceil(m.respawn)}s", True, (255, 220, 140))
    surf.blit(img, img.get_rect(midbottom=(fx, fy - 24)))


def draw_grave(surf, fonts, fx, fy, secs):
    pygame.draw.ellipse(surf, (92, 68, 48), (fx - 14, fy - 6, 28, 10))
    stone = pygame.Rect(fx - 9, fy - 28, 18, 25)
    pygame.draw.rect(surf, (128, 128, 140), stone, border_top_left_radius=9, border_top_right_radius=9)
    pygame.draw.rect(surf, (80, 80, 92), stone, 2, border_top_left_radius=9, border_top_right_radius=9)
    pygame.draw.line(surf, (80, 80, 92), (fx, fy - 23), (fx, fy - 10), 2)
    pygame.draw.line(surf, (80, 80, 92), (fx - 5, fy - 19), (fx + 5, fy - 19), 2)
    img = fonts[20].render(f"{math.ceil(secs)}s", True, MUTED)
    surf.blit(img, img.get_rect(midbottom=(fx, fy - 31)))


# ----- dynamite ------------------------------------------------------------
BOMB_SURF = 80                      # bundle is drawn on a square surface (so it can spin in flight)
BOMB_BASE = (40, 66)                # where the bottom of the sticks sits on that surface
STICK_STEP = STICK_H - 1      # stacked sticks overlap by a pixel


def _bomb_land(b, world):
    cx, cy = b.cell
    return iso(cx + 0.5, cy + 0.5, world.column_height(cx, cy) + world.rise)


def _bomb_jitter(b, t):
    """The bundle starts rattling as the fuse gets short."""
    left = b.fuse_left()
    return math.sin(t * 50) * 2.5 * (1 - left / 0.4) if b.landed and left < 0.4 else 0.0


def _stick_rect(i):
    """Rect of the i-th stick from the bottom of the pile (sticks lie sideways, stacked up)."""
    x = BOMB_BASE[0] - STICK_W // 2 + STICK_STAGGER[i % len(STICK_STAGGER)]
    y = BOMB_BASE[1] - STICK_H - i * STICK_STEP
    return pygame.Rect(x, y, STICK_W, STICK_H)


def _bomb_fuse_base(b):
    top = _stick_rect(b.sticks - 1)   # fuse comes out of the end of the top stick
    return top.right - 2, top.y + 3


def bomb_fuse_tip(b, world, t=0.0):
    """Screen position of the burning end of the fuse (for spark particles)."""
    lx, ly = _bomb_land(b, world)
    bx, by = _bomb_fuse_base(b)
    tip = fuse_points(bx, by, FUSE_LEN * b.fuse_left())[-1]
    return lx - BOMB_BASE[0] + tip[0] + _bomb_jitter(b, t), ly - BOMB_BASE[1] + tip[1]


def draw_bomb(surf, b, world, t):
    """A bundle of dynamite sticks with a burning fuse; spins in on an arc, then sits and fizzes."""
    img = pygame.Surface((BOMB_SURF, BOMB_SURF), pygame.SRCALPHA)
    n = b.sticks
    for i in range(n):   # bottom stick first, so each one sits on the one below
        stick = _stick_rect(i)
        x, y = stick.topleft
        pygame.draw.rect(img, (205, 38, 38), stick, border_radius=4)
        pygame.draw.line(img, (250, 125, 105), (x + 6, y + 2), (stick.right - 5, y + 2), 2)   # shine
        pygame.draw.line(img, (150, 22, 22), (x + 6, stick.bottom - 2), (stick.right - 5, stick.bottom - 2), 1)
        pygame.draw.rect(img, (105, 15, 15), stick, 1, border_radius=4)
        cap = pygame.Rect(x, y, 6, STICK_H)   # paper end of the stick
        pygame.draw.ellipse(img, (238, 218, 190), cap)
        pygame.draw.ellipse(img, (150, 110, 80), cap, 1)
    pile_top = _stick_rect(n - 1).y
    pile_left = BOMB_BASE[0] - STICK_W // 2
    for frac in (0.32, 0.68):   # two bands of twine around the bundle
        bx = pile_left + int(STICK_W * frac)
        band = pygame.Rect(bx, pile_top - 1, 4, BOMB_BASE[1] - pile_top + 2)
        pygame.draw.rect(img, (222, 192, 135), band)
        pygame.draw.rect(img, (135, 105, 65), band, 1)
    fuse = fuse_points(*_bomb_fuse_base(b), FUSE_LEN * b.fuse_left())
    if len(fuse) > 1:
        pygame.draw.lines(img, (70, 58, 46), False, fuse, 2)
    tx, ty = fuse[-1]
    flick = 1 + 0.35 * math.sin(t * 47)
    pygame.draw.circle(img, (255, 170, 60, 110), (int(tx), int(ty)), int(6 * flick))
    pygame.draw.circle(img, (255, 235, 150, 230), (int(tx), int(ty)), int(3 * flick))
    pygame.draw.circle(img, (255, 255, 255, 255), (int(tx), int(ty)), 1)

    lx, ly = _bomb_land(b, world)
    if b.landed:
        surf.blit(img, (lx - BOMB_BASE[0] + _bomb_jitter(b, t), ly - BOMB_BASE[1]))
        return
    # in flight: arc in from above the top-right of the board, spinning end over end
    p = b.throw_progress()
    sx, sy = lx + 300, -60
    ex, ey = lx, ly - (BOMB_BASE[1] - BOMB_SURF // 2)
    x = sx + (ex - sx) * p
    y = sy + (ey - sy) * p - math.sin(math.pi * p) * 140
    spun = pygame.transform.rotate(img, -p * 540)
    surf.blit(spun, spun.get_rect(center=(x, y)))
    shadow = 4 + 10 * p   # shadow grows on the landing spot
    pygame.draw.ellipse(surf, (16, 12, 20), (lx - shadow, ly - shadow * 0.35, shadow * 2, shadow * 0.7))


# ----- enemies -------------------------------------------------------------
def _neck_side(e):
    """+1 if the enemy is on the miner's screen-right, -1 if on the left."""
    return 1 if e.grab_offset[0] - e.grab_offset[1] >= 0 else -1


def _fly_bob(e):
    return math.sin(e.anim_t * 3) * 4


def enemy_anchor(e, rise, t):
    """Centre of the enemy's body on screen; used for clicking and effects."""
    if e.state == "burrowing":   # a Burrower's mound
        fx, fy = _feet(e, rise)
        return fx, fy - 4
    if getattr(e, "mode", "") == "pile":   # the Bone Tyrant in pieces on the ground
        fx, fy = _feet(e, rise)
        return fx, fy - 12
    scale = e.draw_scale
    if e.kind in boss_sprites.DRAWERS and e.mode != "bats":   # (a boss with a sprite of its own)
        fx, fy = _feet(e, rise)
        return fx, fy - boss_sprites.anchor_height(e) * scale
    ax, ay = _base_anchor(e, rise, t)
    if scale:   # bosses are drawn scaled up around their feet
        fx, fy = _feet(e, rise)
        return fx + (ax - fx) * scale, fy + (ay - fy) * scale
    return ax, ay


def _base_anchor(e, rise, t):
    if e.state == "attacking" and e.victim:
        style = e.spec["grab"]
        if style == "head":
            hx, hy = miner_head(e.victim, rise, t)
            return hx, hy - 6
        if style == "neck":
            nx, ny = miner_neck(e.victim, rise, t)
            return nx + _neck_side(e) * 9, ny - 2
        if style == "orbit":   # circling the miner's head
            hx, hy = miner_head(e.victim, rise, t)
            a = e.anim_t * 9
            return hx + math.cos(a) * 14, hy - 4 + math.sin(a) * 5
        if style == "engulf":  # wrapped around the whole miner
            mx, my = _feet(e.victim, rise)
            return mx + (struggle_shake(t) if e.victim.state == "grabbed" else 0), my - 24
    fx, fy = _feet(e, rise)
    if e.look.startswith("slime"):   # (low blobs: the middle of the body, not head height)
        return fx, fy - SLIME_SIZE.get(e.kind, 13) * 0.9
    if e.flying and e.state != "transforming":
        return fx, fy - e.altitude * BLOCK_H + _fly_bob(e)
    if e.kind in ("mimic", "burrower"):   # (squat: the middle of the body, not head height)
        return fx, fy - 12
    return (fx, fy - 22) if e.spec["grab"] == "side" else (fx, fy - 8)


def pick_enemy(world, pos, t):
    for e in reversed(world.enemies):
        if not e.targetable:
            continue
        ax, ay = enemy_anchor(e, world.rise, t)
        if math.hypot(pos[0] - ax, pos[1] - ay) <= ENEMY_HIT_RADIUS[e.kind] * ((e.draw_scale or 1) if e.elite else 1):
            return e
    return None


def draw_enemy(surf, e, rise, t, hovered=False, bar=True):
    scale = e.draw_scale
    if scale:
        _draw_boss(surf, e, rise, t, hovered, scale, bar)
    else:
        _draw_enemy(surf, e, rise, t, hovered)


def _draw_enemy(surf, e, rise, t, hovered):
    if e.state == "emerging":
        _draw_entrance(surf, e, rise, t)
    elif e.state == "transforming":
        _draw_transform(surf, e, rise, t)
    else:
        DRAWERS[e.kind](surf, e, rise, t, hovered)


def _draw_boss(surf, e, rise, t, hovered, scale, bar=True):
    """A boss drawn on a canvas around its feet, then scaled up: its own sprite (boss_sprites.py), or the
    Zombie King's zombie with a crown on top."""
    if e.mode == "split":   # the Slime King in pieces: only its chunks are on the board
        return
    fx, fy = _feet(e, rise)
    cw, ch = BOSS_CANVAS
    ax, ay = cw // 2, ch - 24                     # where the feet sit on the canvas
    if e.state != "emerging" or e.entrance_progress() >= 0:   # menacing shadow pooling under it
        pulse = 0.5 + 0.5 * math.sin(t * 4)
        rx, ry = 34 * scale * 0.5, 12 * scale * 0.5
        aura = pygame.Surface((int(rx * 2 + 8), int(ry * 2 + 8)), pygame.SRCALPHA)
        glow = (235, 60, 40) if e.elite else (150, 20, 30)   # (elites: a brighter, angrier red)
        pygame.draw.ellipse(aura, (*glow, int(70 + 50 * pulse)), aura.get_rect().inflate(-8, -8))
        surf.blit(aura, (fx - aura.get_width() / 2, fy - aura.get_height() / 2))
    if e.mode == "pile":   # the Bone Tyrant in pieces, rattling as it tries to pull itself together
        _draw_bone_pile(surf, e, rise, t, hovered)
        return
    if e.mode == "bats":   # the Vampire Lord as a swarm of bats, flitting around where he is
        _draw_bat_swarm(surf, e, rise, t)
        return
    canvas = pygame.Surface((cw, ch), pygame.SRCALPHA)
    ox, oy = current_origin()
    with origin_at((ox + ax - fx, oy + ay - fy)):
        _draw_enemy(canvas, e, rise, t, hovered)
    own = e.kind in boss_sprites.DRAWERS   # (drawn facing right, crowned, flashing by itself)
    if own and e.facing < 0 and e.kind not in boss_sprites.NO_FLIP:
        canvas = pygame.transform.flip(canvas, True, False)
    if own and e.flash > 0:
        canvas.fill((150, 150, 150), special_flags=pygame.BLEND_RGB_ADD)
    big = pygame.transform.scale(canvas, (int(cw * scale), int(ch * scale)))
    if e.enraged:   # (the Zombie King below half health)
        big.fill((255, 150, 140), special_flags=pygame.BLEND_RGB_MULT)
    surf.blit(big, (fx - ax * scale, fy - ay * scale))
    if own:
        if e.targetable and bar:
            _hp_bar(surf, fx, fy - boss_sprites.bar_height(e) * scale, e.hp / e.max_hp, BAD, 60)
    elif e.state != "emerging" and e.boss:
        bx, by = enemy_anchor(e, rise, t)
        _draw_crown(surf, bx, by - 40 * scale, t)


def _draw_bat_swarm(surf, e, rise, t):
    fx, fy = _feet(e, rise)
    pygame.draw.ellipse(surf, (16, 12, 20), (fx - 22, fy - 6, 44, 12))
    for i in range(7):
        a = t * 5 + i * math.tau / 7
        r = 16 + 6 * math.sin(t * 3 + i)
        x = fx + math.cos(a) * r
        y = fy - 46 + math.sin(a) * r * 0.5 + math.sin(t * 9 + i * 2) * 4
        _draw_bat(surf, e, rise, t + i * 0.13, False, pos=(x, y))


def _draw_bone_pile(surf, e, rise, t, hovered):
    fx, fy = _feet(e, rise)
    urgency = 1 - e.pile_timer / PILE_SECS
    rng = random.Random(7)
    if hovered:
        pygame.draw.ellipse(surf, BAD, (fx - 46, fy - 16, 92, 32), 2)
    pygame.draw.ellipse(surf, (16, 12, 20), (fx - 40, fy - 10, 80, 20))
    flash = e.flash > 0
    for k in range(11):   # a heap of big bones, twitching harder as it gets ready to rise
        jig = math.sin(t * (12 + 25 * urgency) + k) * (1 + 4 * urgency)
        x0, y0 = fx + rng.uniform(-30, 30), fy - rng.uniform(2, 18) + jig * 0.4
        a = rng.uniform(0, math.pi)
        dx, dy = math.cos(a) * 13, math.sin(a) * 5
        col = (255, 255, 255) if flash else BONE_COL
        pygame.draw.line(surf, BONE_SHADE, (x0 - dx, y0 - dy), (x0 + dx, y0 + dy), 7)
        pygame.draw.line(surf, col, (x0 - dx, y0 - dy), (x0 + dx, y0 + dy), 5)
        for sx, sy in ((x0 - dx, y0 - dy), (x0 + dx, y0 + dy)):
            pygame.draw.circle(surf, col, (int(sx), int(sy)), 4)
    skull = (int(fx + math.sin(t * 20) * 2 * urgency), int(fy - 20))
    pygame.draw.circle(surf, BONE_SHADE, skull, 12)
    pygame.draw.circle(surf, (255, 255, 255) if flash else BONE_COL, skull, 11)
    for ex in (-4, 4):   # its eyes still glow
        pygame.draw.circle(surf, (255, int(60 + 150 * urgency), 40), (skull[0] + ex, skull[1] - 1), 3)
    _hp_bar(surf, fx, fy - 40, e.hp / e.max_hp, BAD, 40)


def _draw_crown(surf, x, y, t):
    bob = math.sin(t * 3) * 2
    x, y = int(x), int(y + bob)
    pts = [(x - 13, y + 6), (x - 13, y - 4), (x - 7, y + 1), (x, y - 8), (x + 7, y + 1), (x + 13, y - 4),
           (x + 13, y + 6)]
    pygame.draw.polygon(surf, (255, 205, 60), pts)
    pygame.draw.polygon(surf, (150, 100, 20), pts, 2)
    for gx, col in ((x - 7, (220, 40, 60)), (x, (80, 200, 255)), (x + 7, (220, 40, 60))):
        pygame.draw.circle(surf, col, (gx, y + 3), 2)


# ----- spawn-in animations -------------------------------------------------
def _ease_out(p):
    return 1 - (1 - p) ** 3


def _draw_entrance(surf, e, rise, t):
    if e.timer < 0:            # staggered wave: not this enemy's turn yet
        return
    p = e.entrance_progress()  # <0 telegraph, 0..1 entrance
    style = e.spec["entrance"]
    if style == "dig":
        _draw_ground_cracks(surf, e, rise, t, min(1.0, e.timer / TELEGRAPH_SECS))
        if p >= 0:
            _draw_rising(surf, e, rise, t, min(1.0, p))
    elif style == "drop":
        _draw_spider_dropping(surf, e, rise, t, max(0.0, min(1.0, p)))
    elif style == "swoop":
        _draw_bat_swooping(surf, e, rise, t, p)
    else:
        _draw_materialising(surf, e, rise, t, p)


def _draw_materialising(surf, e, rise, t, p):
    """Cold mist swirls on the spawn cell, then the spirit fades in out of it."""
    fx, fy = _feet(e, rise)
    gather = min(1.0, e.timer / TELEGRAPH_SECS)
    fade = 1 - min(1.0, max(0.0, p)) if p >= 0 else 1.0   # mist clears as the spirit appears
    mist = pygame.Surface((90, 60), pygame.SRCALPHA)
    for i in range(9):
        a = i / 9 * math.tau + t * (2.5 + i % 3)
        r = 30 * (1.2 - gather * 0.7)                       # swirls inwards
        x, y = 45 + math.cos(a) * r, 40 + math.sin(a) * r * 0.45 - gather * 6
        pygame.draw.circle(mist, (190, 215, 255, int(120 * fade * gather)), (int(x), int(y)), int(4 + 4 * gather))
    surf.blit(mist, (fx - 45, fy - 44))
    if p >= 0:
        DRAWERS[e.kind](surf, e, rise, t, False, dy=int((1 - _ease_out(min(1.0, p))) * 14),
                        alpha=_ease_out(min(1.0, p)))


def _draw_ground_cracks(surf, e, rise, t, strength):
    """Glowing cracks spreading across the spawn cell, then a hole once the ground breaks."""
    fx, fy = _feet(e, rise)
    rng = random.Random(int(e.x * 100) * 31 + int(e.y * 100))
    pulse = 0.6 + 0.4 * math.sin(t * 14)
    glow = (int(230 * pulse), int(70 * pulse), 40)
    z = e.draw_z + rise
    for k in range(7):
        a = k / 7 * math.tau + rng.uniform(-0.3, 0.3)
        pts = [(fx, fy)]
        for seg in (0.2, 0.33, 0.46):
            r = seg * strength
            jitter = rng.uniform(-0.25, 0.25)
            pts.append(iso(e.x + math.cos(a + jitter) * r, e.y + math.sin(a + jitter) * r, z))
        pygame.draw.lines(surf, glow, False, pts, 2)
    if e.entrance_progress() >= 0:   # the hole it climbs out of
        pygame.draw.ellipse(surf, (28, 18, 14), (fx - 14, fy - 6, 28, 12))
    elif strength > 0.5:            # ground bulging just before it breaks
        shake = math.sin(t * 50) * 2
        pygame.draw.ellipse(surf, (110, 84, 60), (fx - 8 + shake, fy - 4, 16, 7))


def _draw_clipped_rise(surf, e, rise, t, sink):
    """Draw a ground-dweller `sink` px lower, hiding everything below ground level."""
    fx, fy = _feet(e, rise)
    old_clip = surf.get_clip()
    surf.set_clip(pygame.Rect(0, 0, surf.get_width(), fy).clip(old_clip))
    DRAWERS[e.kind](surf, e, rise, t, False, dy=sink)
    surf.set_clip(old_clip)
    return fx, fy


def _draw_rising(surf, e, rise, t, p):
    """Claws its way up out of the hole."""
    depth = boss_sprites.RISE_DEPTH.get(e.kind, 48)
    fx, fy = _draw_clipped_rise(surf, e, rise, t, int((1 - _ease_out(p)) * depth))
    # front lip of the hole drawn over the waist
    pygame.draw.arc(surf, (130, 98, 66), (fx - 15, fy - 7, 30, 14), math.pi * 1.05, math.pi * 1.95, 3)


def _draw_spider_dropping(surf, e, rise, t, p):
    """Spider drops in on a silk thread while its shadow grows on the landing spot."""
    fx, fy = _feet(e, rise)
    shadow = 0.25 + 0.75 * p if e.entrance_progress() >= 0 else 0.25 * min(1.0, e.timer / 0.7)
    w, h = int(24 * shadow), int(8 * shadow)
    if w > 1:
        pygame.draw.ellipse(surf, (16, 12, 20), (fx - w // 2, fy - h // 2, w, h))
    if e.entrance_progress() < 0:   # warning: a strand of silk drops to the landing spot first
        strand = min(1.0, e.timer / TELEGRAPH_SECS)
        shimmer = (215, 215, 225) if int(t * 10) % 2 else (160, 160, 175)
        pygame.draw.line(surf, shimmer, (fx, 0), (fx, int((fy - 6) * _ease_out(strand))), 1)
        return
    lift = int((1 - _ease_out(p)) * 320)
    cy = fy - boss_sprites.DROP_TOP.get(e.kind, 8) - lift
    pygame.draw.line(surf, (215, 215, 225), (fx, 0), (fx, cy - 5), 1)
    DRAWERS[e.kind](surf, e, rise, t, False, dy=-lift)


def _swoop_start(e, rise):
    """Point out in the darkness beyond the board edge where a bat swoops in from."""
    cx, cy = e.x - GRID / 2, e.y - GRID / 2
    norm = math.hypot(cx, cy) or 1.0
    sx, sy = e.x + cx / norm * 3.5, e.y + cy / norm * 3.5
    px, py = iso(sx, sy, e.draw_z + rise + 2.5)
    return px, max(24, py)   # keep the warning eyes on screen for cells along the top edges


def _draw_bat_swooping(surf, e, rise, t, p):
    """Red eyes blink in the darkness off the board, then the bat swoops in on an arc."""
    sx, sy = _swoop_start(e, rise)
    if p < 0:
        if int(t * 6) % 3:   # blinking eyes
            for d in (-3, 3):
                pygame.draw.circle(surf, (255, 40, 40), (int(sx + d), int(sy)), 2)
        return
    fx, fy = _feet(e, rise)
    ex, ey = fx, fy - FLY_ALTITUDE * BLOCK_H + _fly_bob(e)
    q = _ease_out(min(1.0, p))
    x = sx + (ex - sx) * q
    y = sy + (ey - sy) * q + math.sin(q * math.pi) * 40   # dips low mid-swoop
    pygame.draw.ellipse(surf, (16, 12, 20), (fx - 4 - 4 * q, fy - 2, 8 + 8 * q, 4 + 2 * q))
    DRAWERS[e.kind](surf, e, rise, t, False, pos=(x, y))


def _draw_transform(surf, e, rise, t):
    """Bat flutters down into a cloud of purple smoke and a vampire rises out of it."""
    p = min(1.0, e.timer / TRANSFORM_SECS)
    fx, fy = _feet(e, rise)
    if p < 0.5:
        alt = (1 - p / 0.5) * FLY_ALTITUDE * BLOCK_H
        _draw_bat(surf, e, rise, t, False, pos=(fx, fy - 8 - alt))
    else:
        _draw_clipped_rise(surf, e, rise, t, int((1 - _ease_out((p - 0.5) / 0.5)) * 40))
    swell = math.sin(math.pi * p)
    for i in range(10):
        a = i / 10 * math.tau + t * 3
        r = 6 + 22 * swell
        px, py = fx + math.cos(a) * r, fy - 20 + math.sin(a) * r * 0.6
        color = ((120, 60, 160), (80, 40, 110), (170, 120, 200))[i % 3]
        pygame.draw.circle(surf, color, (int(px), int(py)), int(3 + 7 * swell))


# ----- enemies in play -----------------------------------------------------
def _draw_zombie(surf, e, rise, t, hovered, dy=0):
    fx, fy = _feet(e, rise)
    fy += dy
    entering = e.state == "emerging"
    attacking = e.state == "attacking" and e.victim is not None
    flash = e.flash > 0
    skin = (255, 255, 255) if flash else ZOMBIE_SKIN
    shirt = (255, 255, 255) if flash else ZOMBIE_SHIRT
    if hovered:
        pygame.draw.ellipse(surf, BAD, (fx - 17, fy - 7, 34, 14), 2)
    if not entering:
        pygame.draw.ellipse(surf, (16, 12, 20), (fx - 11, fy - 4, 22, 8))
    if attacking:
        fx += struggle_shake(t, 1.3)
    sway = math.sin(e.anim_t * 3) * 2
    step = math.sin(e.anim_t * 5) * 3 if e.state == "hunting" else 0
    pygame.draw.line(surf, (50, 50, 60), (fx - 3, fy - 9), (fx - 3 + step, fy - 1), 3)
    pygame.draw.line(surf, (50, 50, 60), (fx + 3, fy - 9), (fx + 3 - step, fy - 1), 3)
    bx = fx + sway * 0.5
    pygame.draw.rect(surf, shirt, (bx - 7, fy - 26, 14, 18), border_radius=3)
    pygame.draw.polygon(surf, (40, 50, 80), [(bx - 7, fy - 9), (bx - 2, fy - 14), (bx + 2, fy - 9)])  # torn
    head = (int(fx + sway), fy - 33)
    pygame.draw.circle(surf, skin, head, 7)
    pygame.draw.circle(surf, (230, 40, 40), (head[0] + 2 * e.facing, head[1] - 1), 2)
    pygame.draw.circle(surf, (230, 40, 40), (head[0] + 5 * e.facing, head[1] - 1), 1)
    pygame.draw.line(surf, (40, 60, 30), (head[0] + e.facing, head[1] + 4), (head[0] + 5 * e.facing, head[1] + 3), 2)
    shoulder = (bx, fy - 22)
    if attacking:   # both hands around the miner's neck
        nx, ny = miner_neck(e.victim, rise, t)
        for d in (-3, 3):
            pygame.draw.line(surf, skin, (shoulder[0], shoulder[1] + d * 0.5), (nx + d, ny), 4)
            pygame.draw.circle(surf, skin, (int(nx + d), int(ny)), 3)
    elif entering:  # clawing upward out of the ground
        for d in (-1, 1):
            claw = math.sin(t * 12 + d) * 4
            pygame.draw.line(surf, skin, (shoulder[0] + d * 4, shoulder[1]),
                             (shoulder[0] + d * 9, shoulder[1] - 16 + claw), 4)
            pygame.draw.circle(surf, skin, (int(shoulder[0] + d * 9), int(shoulder[1] - 16 + claw)), 3)
    else:           # arms stretched out in front
        reach = math.sin(e.anim_t * 4)
        for d in (-2, 2):
            pygame.draw.line(surf, skin, (shoulder[0], shoulder[1] + d),
                             (shoulder[0] + 15 * e.facing, shoulder[1] - 2 + d + reach), 4)
    if not entering:
        _hp_bar(surf, head[0], head[1] - 11, e.hp / e.max_hp, BAD)


def _draw_spider(surf, e, rise, t, hovered, dy=0):
    entering = e.state == "emerging"
    attacking = e.state == "attacking" and e.victim is not None
    curled = attacking or entering   # legs wrap a head, or tuck in while dangling
    cx, cy = _base_anchor(e, rise, t)   # (unscaled: a boss canvas is scaled up afterwards)
    cy += dy
    color = (255, 255, 255) if e.flash > 0 else SPIDER_BODY
    leg_col = (255, 255, 255) if e.flash > 0 else (40, 32, 50)
    if hovered:
        pygame.draw.ellipse(surf, BAD, (cx - 20, cy - 10, 40, 20), 2)
    if not attacking and not entering:
        pygame.draw.ellipse(surf, (16, 12, 20), (cx - 12, cy + 4, 24, 8))
    bite = math.sin(t * 20) * 2 if attacking else 0
    cy += bite
    for i in range(4):
        wig = math.sin(e.anim_t * (24 if curled else 18) + i * 1.7) * 2
        for s in (-1, 1):
            knee = (cx + s * (9 + i * 2), cy - 7 + i * 2 + wig)
            foot = (cx + s * (8 + i * 2), cy + 12 + i) if curled else (cx + s * (14 + i * 3), cy + 5 + i * 2 - wig)
            pygame.draw.lines(surf, leg_col, False, [(cx + s * 3, cy), knee, foot], 2)
    pygame.draw.ellipse(surf, color, (cx - 10, cy - 7, 20, 13))
    head = (int(cx + 8 * e.facing), int(cy + 1))
    pygame.draw.circle(surf, color, head, 5)
    pygame.draw.circle(surf, (240, 50, 50), (head[0] + 2 * e.facing, head[1] - 1), 1)
    pygame.draw.circle(surf, (240, 50, 50), (head[0] + 4 * e.facing, head[1]), 1)
    if not entering:
        _hp_bar(surf, cx, cy - 12, e.hp / e.max_hp, BAD, 26)


def _draw_bat(surf, e, rise, t, hovered, dy=0, pos=None):
    """Flapping bat. `pos` overrides where it is drawn (swoop-in / transformation)."""
    attacking = e.state == "attacking" and e.victim is not None
    free_flying = pos is None and not attacking
    cx, cy = pos if pos else _base_anchor(e, rise, t)
    flash = e.flash > 0
    body = (255, 255, 255) if flash else BAT_BODY
    wing = (255, 255, 255) if flash else BAT_WING
    if free_flying:   # shadow on the ground below
        fx, fy = _feet(e, rise)
        pygame.draw.ellipse(surf, (16, 12, 20), (fx - 8, fy - 3, 16, 6))
    if hovered:
        pygame.draw.ellipse(surf, BAD, (cx - 22, cy - 12, 44, 24), 2)
    flap = math.sin(e.anim_t * (34 if attacking or e.state == "transforming" else 20))
    for s in (-1, 1):
        pts = [(cx + s * 3, cy - 2), (cx + s * 11, cy - 6 - 7 * flap), (cx + s * 19, cy - 2 - 9 * flap),
               (cx + s * 15, cy + 1 - 3 * flap), (cx + s * 11, cy + 3 - 2 * flap), (cx + s * 7, cy + 2)]
        pygame.draw.polygon(surf, wing, pts)
        pygame.draw.polygon(surf, BAT_EDGE, pts, 1)
    pygame.draw.ellipse(surf, body, (cx - 5, cy - 5, 10, 11))
    for s in (-1, 1):   # ears
        pygame.draw.polygon(surf, body, [(cx + s * 4, cy - 3), (cx + s * 3, cy - 9), (cx + s, cy - 4)])
    pygame.draw.circle(surf, (255, 50, 50), (int(cx - 2), int(cy - 2)), 1)
    pygame.draw.circle(surf, (255, 50, 50), (int(cx + 2), int(cy - 2)), 1)
    if attacking:       # fangs sunk in
        pygame.draw.line(surf, (255, 255, 255), (cx - 1, cy + 3), (cx - 1, cy + 6), 1)
        pygame.draw.line(surf, (255, 255, 255), (cx + 1, cy + 3), (cx + 1, cy + 6), 1)
    if e.targetable:   # below the bat while biting, so it doesn't cover the miner's own bar
        _hp_bar(surf, cx, cy + 16 if attacking else cy - 11, e.hp / e.max_hp, BAD, 22)


def _draw_vampire(surf, e, rise, t, hovered, dy=0):
    fx, fy = _feet(e, rise)
    fy += dy
    entering = not e.targetable
    attacking = e.state == "attacking" and e.victim is not None
    flash = e.flash > 0
    skin = (255, 255, 255) if flash else VAMP_SKIN
    suit = (255, 255, 255) if flash else VAMP_SUIT
    f = e.facing
    if hovered:
        pygame.draw.ellipse(surf, BAD, (fx - 17, fy - 7, 34, 14), 2)
    if not entering:
        pygame.draw.ellipse(surf, (16, 12, 20), (fx - 12, fy - 4, 24, 8))
    if attacking:
        fx += struggle_shake(t, 2.1) * 0.5
    flare = 2 * math.sin(e.anim_t * 3)
    bx = fx
    # cape flaring out behind the body, red lining inside
    pygame.draw.polygon(surf, VAMP_CAPE, [(bx - 7, fy - 26), (bx + 7, fy - 26),
                                          (bx + 12 + flare, fy - 1), (bx - 12 - flare, fy - 1)])
    pygame.draw.polygon(surf, VAMP_LINING, [(bx - 5, fy - 24), (bx + 5, fy - 24),
                                            (bx + 9 + flare, fy - 3), (bx - 9 - flare, fy - 3)])
    step = math.sin(e.anim_t * 5) * 3 if e.state == "hunting" else 0
    pygame.draw.line(surf, VAMP_HAIR, (fx - 3, fy - 9), (fx - 3 + step, fy - 1), 3)
    pygame.draw.line(surf, VAMP_HAIR, (fx + 3, fy - 9), (fx + 3 - step, fy - 1), 3)
    pygame.draw.rect(surf, suit, (bx - 6, fy - 26, 12, 18), border_radius=3)
    pygame.draw.polygon(surf, (235, 235, 240), [(bx - 3, fy - 26), (bx + 3, fy - 26), (bx, fy - 19)])
    pygame.draw.rect(surf, VAMP_LINING, (bx - 2, fy - 25, 4, 2))
    if attacking:   # leans in and bites the miner's neck
        nx, ny = miner_neck(e.victim, rise, t)
        head = (int(fx + (nx - fx) * 0.55), int(fy - 31))
    else:
        head = (int(fx), int(fy - 33))
    hx, hy = head
    for s in (-1, 1):   # high collar
        pygame.draw.polygon(surf, VAMP_CAPE, [(hx + s * 9, hy + 6), (hx + s * 8, hy - 6), (hx + s * 3, hy + 6)])
        pygame.draw.line(surf, VAMP_LINING, (hx + s * 8, hy - 6), (hx + s * 3, hy + 6), 1)
    pygame.draw.circle(surf, skin, head, 7)
    pygame.draw.polygon(surf, VAMP_HAIR, [(hx - 7, hy - 1), (hx - 6, hy - 6), (hx, hy - 8), (hx + 6, hy - 6),
                                          (hx + 7, hy - 1), (hx + 3, hy - 4), (hx, hy - 1), (hx - 3, hy - 4)])
    pygame.draw.circle(surf, (230, 20, 30), (hx + 2 * f, hy + 1), 1)
    pygame.draw.circle(surf, (230, 20, 30), (hx + 5 * f, hy + 1), 1)
    for d in (1, 4):    # fangs
        pygame.draw.polygon(surf, (255, 255, 255), [(hx + d * f, hy + 4), (hx + (d + 1) * f, hy + 4),
                                                    (hx + (d + 0.5) * f, hy + 7)])
    shoulder = (bx, fy - 22)
    if attacking:     # hands clamped on the miner's shoulders
        nx, ny = miner_neck(e.victim, rise, t)
        for d in (-5, 5):
            pygame.draw.line(surf, suit, shoulder, (nx + d, ny + 5), 4)
            pygame.draw.circle(surf, skin, (int(nx + d), int(ny + 5)), 3)
    elif entering:    # arms raised, cape spread wide
        for s in (-1, 1):
            hand = (bx + s * 12, fy - 38)
            pygame.draw.polygon(surf, VAMP_CAPE, [shoulder, hand, (bx + s * 14, fy - 4)])
            pygame.draw.line(surf, suit, shoulder, hand, 3)
            pygame.draw.circle(surf, skin, hand, 2)
    else:             # dramatic arm holding the cape up in front of the face
        hand = (bx + 12 * f, fy - 30)
        pygame.draw.polygon(surf, VAMP_CAPE, [(bx, fy - 24), hand, (bx + 14 * f, fy - 5), (bx + 4 * f, fy - 2)])
        pygame.draw.line(surf, VAMP_LINING, hand, (bx + 14 * f, fy - 5), 1)
        pygame.draw.line(surf, suit, shoulder, hand, 3)
        pygame.draw.circle(surf, skin, hand, 2)
    if not entering:   # over the body, not the leaning head, so it doesn't sit on the victim's bar
        _hp_bar(surf, bx, fy - 44, e.hp / e.max_hp, BAD)


def _screen_heading(e):
    """Enemy's grid heading converted to a unit vector on screen."""
    hx, hy = e.heading
    sx, sy = (hx - hy) * 2, (hx + hy)          # iso: TILE_W/2 : TILE_H/2 = 2 : 1
    norm = math.hypot(sx, sy) or 1.0
    return sx / norm, sy / norm


def _draw_wisp(surf, e, rise, t, hovered, dy=0, alpha=1.0):
    """A flickering ball of blue fire with a fading trail."""
    attacking = e.state == "attacking" and e.victim is not None
    cx, cy = _base_anchor(e, rise, t)
    cy += dy
    flash = e.flash > 0
    if not attacking and e.state == "hunting":   # faint glow on the ground below
        fx, fy = _feet(e, rise)
        pygame.draw.ellipse(surf, (40, 60, 90), (fx - 7, fy - 3, 14, 6))
    if hovered:
        pygame.draw.circle(surf, BAD, (int(cx), int(cy)), 17, 2)
    glow = pygame.Surface((80, 80), pygame.SRCALPHA)
    o = 40
    hx, hy = (math.cos(e.anim_t * 9 + math.pi / 2), 0.4) if attacking else _screen_heading(e)
    for i in range(5, 0, -1):   # trail behind it
        px, py = o - hx * i * 5, o - hy * i * 5 + math.sin(e.anim_t * 14 + i) * 1.5
        pygame.draw.circle(glow, (120, 190, 255, int(26 * (6 - i))), (int(px), int(py)), 6 - i)
    flicker = 1 + 0.15 * math.sin(e.anim_t * 23)
    core = (255, 255, 255, 255) if flash else (235, 248, 255, 255)
    pygame.draw.circle(glow, (90, 170, 255, 60), (o, o), int(12 * flicker))
    pygame.draw.circle(glow, (150, 215, 255, 150), (o, o), int(7 * flicker))
    pygame.draw.circle(glow, core, (o, o), 4)
    for k in range(3):          # sparks orbiting the flame
        a = e.anim_t * 6 + k * math.tau / 3
        pygame.draw.circle(glow, (200, 235, 255, 200), (int(o + math.cos(a) * 10), int(o + math.sin(a) * 6)), 1)
    glow.set_alpha(int(255 * alpha))
    surf.blit(glow, (cx - o, cy - o))
    if e.targetable:
        _hp_bar(surf, cx, cy - 13, e.hp / e.max_hp, BAD, 18)


def _draw_ghost(surf, e, rise, t, hovered, dy=0, alpha=1.0):
    """Floating sheet ghost. Translucent; nearly invisible while phased; engulfs miners."""
    attacking = e.state == "attacking" and e.victim is not None
    flash = e.flash > 0
    if attacking:
        mx, my = _feet(e.victim, rise)
        bx, by = mx + (struggle_shake(t) if e.victim.state == "grabbed" else 0), my + 2
    else:
        fx, fy = _feet(e, rise)
        bx, by = fx, fy - e.altitude * BLOCK_H + _fly_bob(e) + dy
        if e.state == "hunting":   # cold shadow on the ground
            pygame.draw.ellipse(surf, (34, 40, 60), (fx - 10, fy - 3, 20, 6))
    if e.phased:
        opacity = 0.18 + 0.1 * math.sin(t * 20)    # flickering, barely there
    else:
        opacity = 0.72 if attacking else 0.88
    opacity *= alpha

    big = attacking                                 # stretches to wrap the whole miner
    half = 17 if big else 13
    height = 52 if big else 40
    ghost = pygame.Surface((64, 72), pygame.SRCALPHA)
    ox, base = 32, 66
    top = base - height
    body = (255, 255, 255, 255) if flash else (232, 240, 255, 255)
    pygame.draw.circle(ghost, body, (ox, top + half), half)
    hem_y = base - 6
    pygame.draw.rect(ghost, body, (ox - half, top + half, half * 2, hem_y - top - half))
    hem = [(ox - half, hem_y)]
    for i in range(7):   # wavy, rippling hem
        x = ox - half + i * (2 * half / 6)
        hem.append((x, hem_y + (5 if i % 2 else 0) + math.sin(e.anim_t * 6 + i) * 2))
    hem.append((ox + half, hem_y))
    pygame.draw.polygon(ghost, body, hem)
    arm_y = top + half + (2 if big else 6) + math.sin(e.anim_t * 4) * 2
    for s in (-1, 1):   # little arms: raised "boo" pose, or hugging the miner
        ax = ox + s * (half - 2 if big else half + 3)
        pygame.draw.circle(ghost, body, (int(ax), int(arm_y)), 4)
    eye_y = top + half - 4
    for s in (-1, 1):
        pygame.draw.ellipse(ghost, (20, 24, 40, 255), (ox + s * 5 - 2 + e.facing * 2, eye_y, 5, 8))
    mouth = (ox - 3 + e.facing * 2, eye_y + 11, 7, 9 if not attacking else 6)
    pygame.draw.ellipse(ghost, (20, 24, 40, 255), mouth)
    pygame.draw.circle(ghost, (150, 190, 255, 90), (ox, top + half), half + 3, 2)   # cold aura
    ghost.set_alpha(int(255 * opacity))
    surf.blit(ghost, (bx - ox, by - base))
    if hovered:
        pygame.draw.ellipse(surf, BAD, (bx - 19, by - 46, 38, 48), 2)
    if e.targetable:
        _hp_bar(surf, bx, by - height - 6, e.hp / e.max_hp, BAD, 28)


def _draw_eggsac(surf, e, rise, t, hovered, dy=0, alpha=1.0):
    """A clutch of spider eggs in silk; it pulses and shudders harder as it gets ready to hatch."""
    fx, fy = _feet(e, rise)
    p = min(1.0, e.timer / e.spec["hatch"]["after"])
    shake = math.sin(t * (10 + 30 * p)) * (0.5 + 2.5 * p)
    flash = e.flash > 0
    silk = (255, 255, 255) if flash else _lerp((225, 222, 205), (240, 225, 190), p)
    if hovered:
        pygame.draw.ellipse(surf, BAD, (fx - 16, fy - 7, 32, 14), 2)
    pygame.draw.ellipse(surf, (16, 12, 20), (fx - 11, fy - 4, 22, 8))
    cx = fx + shake
    for ox, oy, r in ((-5, -6, 6), (5, -6, 6), (0, -12, 7)):
        pygame.draw.circle(surf, silk, (int(cx + ox), int(fy + oy)), r)
        pygame.draw.circle(surf, (170, 165, 150), (int(cx + ox), int(fy + oy)), r, 1)
    pulse = 0.5 + 0.5 * math.sin(t * (4 + 10 * p))
    for ox, oy in ((-5, -6), (5, -6), (0, -12)):   # something moving inside
        pygame.draw.circle(surf, _lerp((150, 190, 110), (90, 60, 120), p), (int(cx + ox), int(fy + oy)),
                           max(1, int(2 + 2 * pulse * p)))
    for k in range(3):   # silk strands
        pygame.draw.line(surf, (200, 198, 185), (cx - 8 + k * 8, fy - 2), (cx - 4 + k * 4, fy - 18), 1)
    if e.targetable:
        _hp_bar(surf, fx, fy - 24, e.hp / e.max_hp, BAD, 20)


def _draw_skeleton(surf, e, rise, t, hovered, dy=0):
    """A rattling skeleton: bone limbs, ribcage, a grinning skull with red pinprick eyes."""
    fx, fy = _feet(e, rise)
    fy += dy
    entering = e.state == "emerging"
    attacking = e.state == "attacking" and e.victim is not None
    bone = (255, 255, 255) if e.flash > 0 else BONE_COL
    if hovered:
        pygame.draw.ellipse(surf, BAD, (fx - 17, fy - 7, 34, 14), 2)
    if not entering:
        pygame.draw.ellipse(surf, (16, 12, 20), (fx - 10, fy - 4, 20, 8))
    if attacking:
        fx += struggle_shake(t, 0.7)
    step = math.sin(e.anim_t * 7) * 3 if e.state == "hunting" else 0
    for side, st in ((-1, step), (1, -step)):   # legs
        pygame.draw.line(surf, BONE_SHADE, (fx + side * 3, fy - 11), (fx + side * 3 + st, fy - 1), 3)
        pygame.draw.line(surf, bone, (fx + side * 3, fy - 11), (fx + side * 3 + st, fy - 1), 2)
    pygame.draw.ellipse(surf, bone, (fx - 5, fy - 14, 10, 5))   # pelvis
    pygame.draw.line(surf, bone, (fx, fy - 13), (fx, fy - 27), 2)   # spine
    for k in range(3):   # ribs
        ry = fy - 25 + k * 4
        pygame.draw.arc(surf, bone, (fx - 7, ry - 3, 14, 7), math.pi * 1.05, math.pi * 1.95, 2)
    shoulder = (fx, fy - 26)
    throw = 1 - e.throw_anim / THROW_ANIM_SECS if getattr(e, "throw_anim", 0) > 0 else None   # (Bone Tyrant)
    lean = 0
    if throw is not None:   # rears back with the bone, then lunges into the throw
        lean = -3 * _ease_out(throw / THROW_RELEASE) if throw < THROW_RELEASE else 3
        lean *= e.facing
    if attacking:   # bony hands round the miner's neck
        nx, ny = miner_neck(e.victim, rise, t)
        for d in (-3, 3):
            pygame.draw.line(surf, bone, (shoulder[0], shoulder[1] + d * 0.5), (nx + d, ny), 2)
    elif entering:  # clawing up out of the ground
        for d in (-1, 1):
            claw = math.sin(t * 12 + d) * 4
            pygame.draw.line(surf, bone, (shoulder[0] + d * 4, shoulder[1]),
                             (shoulder[0] + d * 9, shoulder[1] - 15 + claw), 2)
    else:           # arms swinging stiffly
        swing = math.sin(e.anim_t * 7) * 5
        for d in (-1, 1):
            if throw is not None and d == e.facing:   # (the throwing arm is drawn below)
                continue
            pygame.draw.line(surf, bone, (shoulder[0] + d * 5, shoulder[1]),
                             (shoulder[0] + d * 7 + swing * d * 0.3 + 4 * e.facing, shoulder[1] + 11), 2)
        if throw is not None:
            _draw_throwing_arm(surf, e, (shoulder[0] + e.facing * 5 + lean, shoulder[1]), throw, bone)
    head = (int(fx + e.facing + lean), fy - 34)
    pygame.draw.circle(surf, BONE_SHADE, head, 7)
    pygame.draw.circle(surf, bone, head, 6)
    pygame.draw.rect(surf, bone, (head[0] - 3, head[1] + 3, 6, 4))   # jaw
    for ex in (-2, 2):
        pygame.draw.circle(surf, (40, 30, 34), (head[0] + ex + e.facing, head[1] - 1), 2)
        pygame.draw.circle(surf, (255, 60, 50), (head[0] + ex + e.facing, head[1] - 1), 1)
    if not entering and getattr(e, "show_hp", True):   # (not on the title screen)
        _hp_bar(surf, head[0], head[1] - 11, e.hp / e.max_hp, BAD)


def draw_bone(surf, x, y, angle, half, width, col=BONE_COL):
    """A bone: a shaft with a pair of knobs at each end, `half` px long each way, outlined so it reads."""
    dx, dy = math.cos(angle) * half, math.sin(angle) * half
    nx, ny = -math.sin(angle) * width * 0.45, math.cos(angle) * width * 0.45
    ends = ((x - dx, y - dy), (x + dx, y + dy))
    pygame.draw.line(surf, (40, 30, 30), *ends, width + 4)
    for ex, ey in ends:
        for s in (-1, 1):
            pygame.draw.circle(surf, (40, 30, 30), (int(ex + nx * s), int(ey + ny * s)), int(width * 0.6) + 2)
    pygame.draw.line(surf, BONE_SHADE, *ends, width + 2)
    pygame.draw.line(surf, col, *ends, width)
    for ex, ey in ends:
        for s in (-1, 1):
            pygame.draw.circle(surf, col, (int(ex + nx * s), int(ey + ny * s)), int(width * 0.6))


def _draw_throwing_arm(surf, e, shoulder, p, bone):
    """The Bone Tyrant's throw (`p` 0..1): the arm swings up and back over its shoulder with a bone in hand,
    then whips forward and lets go at THROW_RELEASE."""
    f = e.facing
    if p < THROW_RELEASE:
        k = _ease_out(p / THROW_RELEASE)
        hand = (shoulder[0] + f * (4 - 13 * k), shoulder[1] + 10 - 24 * k)
    else:
        k = (p - THROW_RELEASE) / (1 - THROW_RELEASE)
        hand = (shoulder[0] + f * (8 + 6 * k), shoulder[1] - 12 + 18 * k)
    elbow = ((shoulder[0] + hand[0]) / 2 - f * 2, (shoulder[1] + hand[1]) / 2 - 2)
    pygame.draw.line(surf, BONE_SHADE, shoulder, elbow, 4)
    pygame.draw.line(surf, bone, shoulder, elbow, 3)
    pygame.draw.line(surf, BONE_SHADE, elbow, hand, 4)
    pygame.draw.line(surf, bone, elbow, hand, 3)
    if p < THROW_RELEASE:   # the bone it's about to throw
        draw_bone(surf, hand[0], hand[1] - 2, -0.9 * f - p * 2 * f, 6, 3)


def _draw_slime(surf, e, rise, t, hovered, dy=0):
    """A wobbling blob of green ooze with beady eyes that hops along; winding up a slam it swells and reddens."""
    fx, fy = _feet(e, rise)
    fy += dy
    r = SLIME_SIZE.get(e.kind, 13)
    entering = e.state == "emerging"
    attacking = e.state == "attacking" and e.victim is not None
    charge = 1 - e.windup / e.windup_total if e.windup > 0 else 0.0
    hop = max(0.0, math.sin(e.anim_t * 6)) if e.state == "hunting" and not charge else 0.0
    if attacking:
        fx += struggle_shake(t, 0.4)
    if hovered:
        pygame.draw.ellipse(surf, BAD, (fx - r - 5, fy - 7, 2 * r + 10, 14), 2)
    if not entering:
        sw = r * 1.8 * (1 - 0.3 * hop)
        pygame.draw.ellipse(surf, (16, 12, 20), (fx - sw / 2, fy - 4, sw, 8))
    wob = math.sin(e.anim_t * 9) * 0.06
    w = r * (1.1 + wob - 0.18 * hop + 0.3 * charge)
    h = r * (0.85 - wob + 0.25 * hop + 0.2 * charge)
    lift = hop * r * 0.6
    col = (255, 255, 255) if e.flash > 0 else _lerp(SLIME_GREEN, SLIME_ANGRY, charge * 0.8)
    body = pygame.Surface((int(w * 2) + 4, int(h * 2) + 4), pygame.SRCALPHA)
    rect = body.get_rect().inflate(-4, -4)
    pygame.draw.ellipse(body, (*col, 215), rect)
    for bx, by, br in ((0.35, 0.6, 0.12), (0.62, 0.42, 0.08)):   # bubbles inside
        pygame.draw.circle(body, (*_lerp(col, (255, 255, 255), 0.4), 150),
                           (int(rect.x + rect.w * bx), int(rect.y + rect.h * by)), max(1, int(r * br)))
    pygame.draw.ellipse(body, (255, 255, 255, 110),
                        (rect.x + rect.w * 0.2, rect.y + rect.h * 0.12, rect.w * 0.3, rect.h * 0.22))   # shine
    pygame.draw.ellipse(body, (*SLIME_DARK, 255), rect, 2)
    top = fy - lift - 2 * h
    surf.blit(body, (fx - w - 2, top - 2))
    if attacking:   # a gob of it reaching out over the miner
        nx, ny = miner_neck(e.victim, rise, t)
        pygame.draw.line(surf, col, (fx, top + h), (nx, ny), max(2, r // 3))
        pygame.draw.circle(surf, col, (int(nx), int(ny)), max(2, r // 3))
    eye_y = int(top + h * 0.75)
    for ex in (-1, 1):
        cx = int(fx + e.facing * r * 0.2 + ex * r * 0.3)
        pygame.draw.circle(surf, (250, 250, 240), (cx, eye_y), max(2, int(r * 0.2)))
        pygame.draw.circle(surf, (20, 20, 24), (cx + e.facing, eye_y), max(1, int(r * 0.11)))
    if not entering:
        _hp_bar(surf, fx, int(top) - 5, e.hp / e.max_hp, BAD, 28 if r >= 10 else 20)


# ----- the deep: Mimic, Rock Golem, Abyssal Shade -------------------------------------------------------------------
WOOD, WOOD_DARK, CHEST_GOLD = (140, 90, 50), (88, 54, 30), (230, 180, 60)
STONE_COL, STONE_EDGE, MOSS = (128, 126, 138), (78, 76, 90), (96, 130, 80)


def _ip(fx, fy, x, y, z):
    """A point on an isometric prop standing at (fx, fy): `x` px along the board's down-right axis, `y` along its
    down-left one, `z` up."""
    return (fx + x - y, fy + (x + y) * 0.5 - z)


def _iso_box(surf, fx, fy, x0, x1, y0, y1, z0, z1, color, edge=None):
    """A box on the isometric board: its top and the two sides that face the viewer (lit like the dig's blocks).
    Returns the faces: top, left (facing down-left) and right (facing down-right)."""
    def p(x, y, z):
        return _ip(fx, fy, x, y, z)
    faces = dict(top=[p(x0, y0, z1), p(x1, y0, z1), p(x1, y1, z1), p(x0, y1, z1)],
                 left=[p(x0, y1, z0), p(x1, y1, z0), p(x1, y1, z1), p(x0, y1, z1)],
                 right=[p(x1, y0, z0), p(x1, y1, z0), p(x1, y1, z1), p(x1, y0, z1)])
    edge = edge or shade(color, 0.45)
    for name, f in (("left", 0.72), ("right", 0.55), ("top", 1.0)):
        pygame.draw.polygon(surf, shade(color, f), faces[name])
        pygame.draw.polygon(surf, edge, faces[name], 1)
    return faces


def _iso_ring(fx, fy, c, r, plane="ground", n=20, a0=0.0, rs=None):
    """Points round a circle of radius `r` about `c` (x, y, z), lying on the ground ("ground"), or standing up facing
    down-right ("x") or down-left ("y"). `rs`: a radius for each point instead (gear teeth)."""
    cx, cy, cz = c
    pts = []
    for k in range(n):
        a = a0 + k * math.tau / n
        rr = rs[k] if rs else r
        u, v = math.cos(a) * rr, math.sin(a) * rr
        x, y, z = (cx + u, cy + v, cz) if plane == "ground" else (cx, cy - u, cz + v) if plane == "x" else \
            (cx + u, cy, cz + v)
        pts.append(_ip(fx, fy, x, y, z))
    return pts


def _iso_shadow(surf, fx, fy, r):
    """A round shadow on the ground, `r` px across in board terms."""
    pygame.draw.ellipse(surf, (16, 12, 20), (fx - r * 1.41, fy - r * 0.71, r * 2.83, r * 1.41))


def _iso_gear(surf, fx, fy, c, r, plane, spin, color):
    """A brass cog standing up on the board, turned `spin` radians."""
    teeth = [r + 2.2 if (k // 2) % 2 == 0 else r for k in range(32)]
    pygame.draw.polygon(surf, shade(color, 0.7), _iso_ring(fx, fy, c, r, plane, 32, spin, teeth))
    pygame.draw.polygon(surf, color, _iso_ring(fx, fy, c, r - 1, plane, 20, spin))
    pygame.draw.polygon(surf, shade(color, 0.6), _iso_ring(fx, fy, c, r - 1, plane, 20, spin), 1)
    for k in range(3):   # spokes
        a = spin + k * math.tau / 3
        tip = _iso_ring(fx, fy, c, r * 0.7, plane, 1, a)[0]
        pygame.draw.line(surf, shade(color, 0.7), _iso_ring(fx, fy, c, 0, plane, 1)[0], tip, 1)
    pygame.draw.polygon(surf, shade(color, 0.55), _iso_ring(fx, fy, c, max(1.5, r * 0.28), plane, 10))


def draw_pet_chest(surf, fx, fy, t, gape=0.0, facing=1, lift=0.0, size=1.0, spiked=False):
    """Chompers, the camp's Friendly Mimic: a treasure chest on stubby legs with a gold collar, big friendly eyes peeping
    out of the seam - lid shut (`gape` 0) or flung open (1) with a tongue lolling out. `lift`: px off the ground.
    Its front faces down-right (`facing` 1) or down-left (-1). `size`: smaller for the Mimic Pup; `spiked`: the
    Spiked Collar on."""
    fx, fy = int(fx), int(fy)
    sw = (24 - lift * 0.2) * size
    pygame.draw.ellipse(surf, (16, 12, 20), (fx - sw / 2, fy - 4 * size, sw, 8 * size))
    base = fy - lift - abs(math.sin(t * 3 + size * 5)) * 1.5
    hw, hd, hb, open_by, lid_h = 8.0 * size, 5.5 * size, 9.0 * size, 8 * gape * size, 5 * size

    def front(u, z):   # a point on the chest's front: `u` across it (left to right on screen), `z` up
        return _ip(fx, base, hd, -u, z) if facing >= 0 else _ip(fx, base, u, hd, z)
    ext = (-hd, hd, -hw, hw) if facing >= 0 else (-hw, hw, -hd, hd)
    for d in (-0.6, 0.6):   # stubby legs
        x, y = front(d * hw, 0)
        kick = math.sin(t * 10 + d * 9) * 2 if lift else 0
        pygame.draw.line(surf, WOOD_DARK, (x, y - 2), (x + kick, y + 2), 3)
    box = _iso_box(surf, fx, base, *ext, 0, hb, WOOD, WOOD_DARK)
    if gape > 0.05:   # (open: dark inside, and the gap under the lid all the way round)
        pygame.draw.polygon(surf, (70, 20, 28), box["top"])
        for side in ("left", "right"):
            lo = box[side][3], box[side][2]
            pygame.draw.polygon(surf, (110, 30, 40), [lo[0], lo[1], (lo[1][0], lo[1][1] - open_by),
                                                      (lo[0][0], lo[0][1] - open_by)])
    for d in (-0.55, 0.55):   # iron-bound with gold
        pygame.draw.line(surf, CHEST_GOLD, front(d * hw, 0.5), front(d * hw, hb), 2)
    collar_z = 2.5 * size
    if spiked:   # the Spiked Collar: black leather, studded
        pygame.draw.line(surf, (40, 30, 34), front(-hw, collar_z), front(hw, collar_z), 3)
        nx, ny = (1, 0.5) if facing >= 0 else (-1, 0.5)
        for k in range(5):
            sx, sy = front(-hw * 0.8 + k * hw * 0.4, collar_z)
            pygame.draw.polygon(surf, (210, 210, 220), [(sx - 1.5, sy - 1), (sx + 1.5, sy - 1), (sx + nx * 3, sy + ny * 3 + 1)])
    else:
        pygame.draw.line(surf, (250, 215, 90), front(-hw, collar_z), front(hw, collar_z), 2)   # its collar...
    tag = front(0, 1.5 * size)
    pygame.draw.circle(surf, (250, 215, 90), (int(tag[0]), int(tag[1])), 2)   # ...and tag
    if gape > 0.05:   # mouth open: a friendly row of blunt teeth and a tongue lolling out
        lo, hi = -0.92, 0.92
        pygame.draw.polygon(surf, (110, 30, 40), [front(lo * hw, hb), front(hi * hw, hb),
                                                  front(hi * hw, hb + open_by), front(lo * hw, hb + open_by)])
        for k in range(3):
            u = (k - 1) * 0.55 * hw
            tw, th = 1.8 * size, 2.5 * size
            pygame.draw.polygon(surf, (245, 240, 225), [front(u - tw, hb), front(u + tw, hb), front(u + tw, hb + th),
                                                        front(u - tw, hb + th)])
        nx, ny = (1, 0.5) if facing >= 0 else (-1, 0.5)   # (out of the chest, towards the viewer)
        root = front(0, hb + 0.5)
        tongue = [root, (root[0] + nx * 5, root[1] + ny * 5 + 4 + math.sin(t * 9) * 1.5),
                  (root[0] + nx * 8, root[1] + ny * 8 + 2)]
        pygame.draw.lines(surf, (230, 90, 110), False, tongue, 3)
    lx0, lx1, ly0, ly1 = ext
    lid = _iso_box(surf, fx, base, lx0 - 0.5, lx1 + 0.5, ly0 - 0.5, ly1 + 0.5, hb + open_by, hb + open_by + lid_h, WOOD,
                   WOOD_DARK)
    pygame.draw.line(surf, CHEST_GOLD, *(lid["top"][2:4] if facing < 0 else lid["top"][1:3]), 1)   # the lid's rim
    for d in (-0.55, 0.55):
        pygame.draw.line(surf, CHEST_GOLD, front(d * hw, hb + open_by), front(d * hw, hb + open_by + lid_h), 2)
    blink = (t * 0.7 + fx * 0.01) % 3.0 < 0.12
    for d in (-0.45, 0.45):   # big friendly eyes, peeping out from under the lid
        ex, ey = (int(v) for v in front(d * hw, hb + open_by - 2.5 * size))
        if blink:
            pygame.draw.line(surf, (30, 20, 20), (ex - 2, ey), (ex + 2, ey), 1)
        else:
            pygame.draw.circle(surf, (250, 250, 240), (ex, ey), max(2, round(3 * size)))
            pygame.draw.circle(surf, (30, 20, 20), (ex + (1 if facing >= 0 else -1), ey), 1)
    if gape <= 0.05:   # the clasp
        cx, cy = front(0, hb - 0.5)
        pygame.draw.rect(surf, CHEST_GOLD, (int(cx) - 2, int(cy) - 1, 4, 3))


def draw_collar_post(surf, fx, fy, t):
    """The Spiked Collar at camp: a short post with Chompers' studded collar hung on it, and its food bowl - a bone
    in it - beside."""
    fx, fy = int(fx), int(fy)
    _iso_shadow(surf, fx, fy, 10)
    bx, by = _ip(fx, fy, -3, 8, 0)   # the bowl
    pygame.draw.ellipse(surf, (150, 40, 40), (bx - 9, by - 5, 18, 9))
    pygame.draw.ellipse(surf, (200, 70, 60), (bx - 8, by - 7, 16, 7))
    pygame.draw.ellipse(surf, (90, 24, 24), (bx - 6, by - 6, 12, 4))
    pygame.draw.line(surf, (236, 230, 210), (bx - 4, by - 6), (bx + 3, by - 8), 2)   # (a bone)
    for ex, ey in ((bx - 4, by - 6), (bx + 3, by - 8)):
        pygame.draw.circle(surf, (236, 230, 210), (ex, ey), 2)
    _iso_box(surf, fx, fy, -2, 2, -2, 2, 0, 26, (120, 84, 50))   # the post...
    pygame.draw.circle(surf, (190, 190, 200), (int(fx + 1), int(fy - 24)), 1)   # ...and its nail
    ring = _iso_ring(fx, fy, (3, 0, 16), 7, "x", 20)   # the collar, hung on it, facing down-right
    pygame.draw.polygon(surf, (40, 30, 34), ring, 3)
    for k in range(0, 20, 3):   # studs
        sx, sy = ring[k]
        pygame.draw.circle(surf, (215, 215, 225), (int(sx), int(sy)), 2)
    tag = ring[15]
    pygame.draw.circle(surf, (250, 215, 90), (int(tag[0]), int(tag[1]) + 3), 2)


def draw_tax_strongbox(surf, fx, fy, t, lit=True):
    """Death and Taxes: an iron strongbox with a coin slot and a padlock, a borrowed scythe leaning on it - and
    (once it's yours) a coin now and then dropping in."""
    fx, fy = int(fx), int(fy)
    _iso_shadow(surf, fx, fy, 12)
    blade = [_ip(fx, fy, -4, -9, 44), _ip(fx, fy, 7, -16, 40), _ip(fx, fy, 12, -18, 34), _ip(fx, fy, 6, -14, 39)]
    pygame.draw.line(surf, (96, 70, 44), _ip(fx, fy, 6, -10, 0), _ip(fx, fy, -4, -9, 46), 2)   # the scythe's snath...
    pygame.draw.polygon(surf, (190, 196, 206), blade)                                         # ...and blade
    pygame.draw.lines(surf, (120, 124, 134), False, blade[:3], 1)
    box = _iso_box(surf, fx, fy, -9, 9, -6, 6, 0, 12, (78, 78, 90), (40, 40, 48))   # the strongbox
    for face in ("left", "right"):   # gold rivets at its corners
        for p in box[face]:
            pygame.draw.circle(surf, (210, 170, 70), (int(p[0]), int(p[1])), 1)
    pygame.draw.line(surf, (24, 24, 30), _ip(fx, fy, -3, 0, 12), _ip(fx, fy, 3, 0, 12), 2)   # the coin slot
    lx, ly = _ip(fx, fy, 0, 6, 6)   # the padlock on its front
    pygame.draw.arc(surf, (200, 170, 70), (lx - 3, ly - 6, 6, 6), 0, math.pi, 1)
    pygame.draw.rect(surf, (210, 170, 70), (lx - 3, ly - 3, 6, 5), border_radius=1)
    if lit:
        q = (t * 0.6) % 1
        if q < 0.5:   # a coin dropping in
            cx, cy = _ip(fx, fy, 0, 0, 12 + 14 * (1 - q * 2))
            pygame.draw.ellipse(surf, (250, 210, 80), (cx - 2, cy - 3, 4, 6))


def draw_mudling(surf, fx, fy, t, anim=0.0, left=10.0, shaped=False):
    """A Clay Pit mudling: a knee-high blob of wet clay with coal-dot eyes and stubby arms, swinging at the rock -
    slumping as it starts to crumble. `shaped`: thrown on the Potter's Wheel - a proper clay soldier, helmet and
    all."""
    fx, fy = int(fx), int(fy)
    slump = max(0.0, 1 - left / 1.5)   # (its last second and a half: sagging back into mud)
    h = int(16 * (1 - 0.6 * slump))
    pygame.draw.ellipse(surf, (16, 12, 20), (fx - 8, fy - 3, 16, 6))
    body = pygame.Rect(0, 0, 14 + int(6 * slump), h)
    body.midbottom = (fx, fy + 1)
    pygame.draw.ellipse(surf, (132, 80, 50), body.inflate(2, 2))
    pygame.draw.ellipse(surf, (186, 116, 74), body)
    pygame.draw.ellipse(surf, (214, 150, 104), (body.x + 3, body.y + 2, 5, 3))
    for d in (-2, 2):
        pygame.draw.circle(surf, (40, 24, 16), (fx + d, body.y + h // 3 + 1), 1)
    swing = anim * 6
    for d in (-1, 1):   # stubby arms - up, then down on the rock
        pygame.draw.line(surf, (132, 80, 50), (fx + d * 6, body.y + h // 2), (fx + d * 9, body.y + h // 2 - 4 + swing), 3)
    if shaped and slump < 0.5:   # a clay soldier: a pot helmet with a rim, and a belt
        helm = pygame.Rect(fx - 6, body.y - 3, 12, 7)
        pygame.draw.ellipse(surf, (150, 88, 56), helm)
        pygame.draw.line(surf, (110, 62, 38), (helm.x - 1, helm.bottom - 2), (helm.right, helm.bottom - 2), 2)
        pygame.draw.circle(surf, (200, 140, 96), (fx, helm.y + 1), 1)
        pygame.draw.line(surf, (120, 70, 44), (body.x + 2, body.y + h * 2 // 3), (body.right - 2, body.y + h * 2 // 3), 1)


def draw_banner(surf, fx, fy, t, fringe=False):
    """Rocco's Banner of the Deep: a deep blue standard with gold trim and a pick on it, hung from a crossbar on a
    tall pole planted in a heap of stones, rippling (`fringe`: with the Gold Fringe sewn on)."""
    fx, fy = int(fx), int(fy)
    _iso_shadow(surf, fx, fy, 6)
    for x, y, r in ((-3, 2, 3.5), (3, -2, 3.5), (2, 3, 3), (-2, -3, 3)):   # the stones it's wedged in
        sx, sy = _ip(fx, fy, x, y, 1)
        pygame.draw.ellipse(surf, (96, 92, 100), (sx - r, sy - r * 0.7, r * 2, r * 1.4))
        pygame.draw.ellipse(surf, (130, 126, 136), (sx - r + 1, sy - r * 0.7, r * 2 - 2, r * 0.8))
    top, hem = 46, 20
    pygame.draw.line(surf, (110, 80, 50), (fx, fy - 2), (fx, fy - top - 4), 3)   # the pole...
    pygame.draw.circle(surf, (250, 205, 70), (fx, fy - top - 6), 3)            # ...its gold finial...
    pygame.draw.line(surf, (110, 80, 50), _ip(fx, fy, 0, 8, top), _ip(fx, fy, 0, -8, top), 2)   # ...and crossbar

    def cloth(y, z):   # a point on the banner (facing down-right), rippling more the further down it hangs
        sx, sy = _ip(fx, fy, 0, y, z)
        return sx + math.sin(t * 3 + y * 0.45) * 1.6 * (top - z) / (top - hem), sy

    edge = [cloth(y, top - 1) for y in (7, 3.5, 0, -3.5, -7)]
    tails = [cloth(-7, hem), cloth(-3.5, hem + 1), cloth(0, hem + 5), cloth(3.5, hem + 1), cloth(7, hem)]   # (swallowtail)
    pts = edge + tails
    pygame.draw.polygon(surf, (52, 88, 170), pts)
    pygame.draw.polygon(surf, (250, 205, 70), pts, 1)
    mid = cloth(0, (top + hem) / 2 + 2)
    pygame.draw.circle(surf, (36, 62, 128), (int(mid[0]), int(mid[1])), 5)
    pygame.draw.line(surf, (250, 205, 70), (mid[0] - 3, mid[1] + 3), (mid[0] + 3, mid[1] - 3), 2)   # a pick on it
    pygame.draw.line(surf, (250, 205, 70), (mid[0] - 1, mid[1] - 4), (mid[0] + 5, mid[1] - 1), 2)
    if fringe:
        draw_banner_fringe(surf, fx, fy, t)


def draw_banner_fringe(surf, fx, fy, t):
    """The Gold Fringe, on Rocco's banner (drawn over it, at its feet): gold tassels along its swallowtail, and a
    little gold pennant flying from the top of the pole."""
    fx, fy = int(fx), int(fy)
    top, hem = 46, 20

    def cloth(y, z):   # (the banner's own ripple: see draw_banner)
        sx, sy = _ip(fx, fy, 0, y, z)
        return sx + math.sin(t * 3 + y * 0.45) * 1.6 * (top - z) / (top - hem), sy
    tails = [(-7, hem), (-3.5, hem + 1), (0, hem + 5), (3.5, hem + 1), (7, hem)]
    for (y0, z0), (y1, z1) in zip(tails, tails[1:]):   # tassels all along the hem
        for k in range(3):
            q = k / 3
            x, y = cloth(y0 + (y1 - y0) * q, z0 + (z1 - z0) * q)
            sway = math.sin(t * 4 + k + y0) * 0.8
            pygame.draw.line(surf, (250, 205, 70), (x, y), (x + sway, y + 4), 1)
    pygame.draw.line(surf, (250, 205, 70), cloth(7, top - 1), cloth(-7, top - 1), 2)   # (a gold band across the top)
    wave = math.sin(t * 5) * 2   # the pennant, flying from the pole's top
    pole = (fx, fy - top - 10)
    pygame.draw.line(surf, (110, 80, 50), (fx, fy - top - 4), pole, 2)
    pygame.draw.polygon(surf, (250, 205, 70), [pole, (pole[0] + 12, pole[1] + 3 + wave), (pole[0], pole[1] + 6)])
    pygame.draw.circle(surf, (255, 235, 150), (fx, fy - top - 11), 2)


def draw_divining_rod(surf, fx, fy, t, live=True, pick=False):
    """Rocco's Divining Rod: a forked hazel twig standing in an old tree stump, twitching now and then - and, once
    it's yours, glinting at something buried. `pick`: the Heirloom Pickaxe driven into the stump beside it."""
    fx, fy = int(fx), int(fy)
    _iso_shadow(surf, fx, fy, 9)
    R, h = 7.5, 8
    rx, ry = R * 1.41, R * 0.71
    bark, cut = (96, 66, 42), (176, 136, 90)
    pygame.draw.ellipse(surf, shade(bark, 0.8), (fx - rx, fy - ry, rx * 2, ry * 2))   # the stump
    pygame.draw.rect(surf, bark, (fx - rx, fy - h, rx, h))
    pygame.draw.rect(surf, shade(bark, 0.75), (fx, fy - h, rx, h))
    pygame.draw.ellipse(surf, cut, (fx - rx, fy - h - ry, rx * 2, ry * 2))
    pygame.draw.ellipse(surf, shade(cut, 0.8), (fx - rx * 0.55, fy - h - ry * 0.55, rx * 1.1, ry * 1.1), 1)   # rings
    twitch = math.sin(t * 9) * 2.5 if live and math.sin(t * 1.3) > 0.6 else math.sin(t * 1.5) * 0.6
    base = (fx, fy - h - 1)
    fork = (fx + twitch * 0.3, fy - h - 15)
    pygame.draw.line(surf, (150, 110, 60), base, fork, 3)   # the stem...
    for side in (-1, 1):   # ...and its two arms
        tip = (fork[0] + side * 8 + twitch, fork[1] - 13)
        pygame.draw.line(surf, (150, 110, 60), fork, tip, 2)
        pygame.draw.line(surf, (190, 150, 90), (fork[0] + side, fork[1] - 1), (tip[0], tip[1] + 1), 1)
    if live:   # glints of something old, somewhere close
        for k in range(3):
            q = (t * 0.7 + k / 3) % 1
            gx, gy = fx + math.cos(k * 2.1 + t * 0.5) * 13, fy - h - 30 + q * 18
            size = 2.5 * math.sin(q * math.pi)
            pygame.draw.line(surf, (255, 240, 170), (gx - size, gy), (gx + size, gy), 1)
            pygame.draw.line(surf, (255, 240, 170), (gx, gy - size), (gx, gy + size), 1)
    if pick:
        draw_heirloom_pick(surf, fx, fy, t)


def draw_heirloom_pick(surf, fx, fy, t):
    """The Heirloom Pickaxe, driven into the Divining Rod's stump (drawn over it, at the stump's feet): a handle worn
    black, leaning back, and a gold head bitten into the wood, glinting now and then."""
    fx, fy = int(fx), int(fy)
    h = 8
    head = (fx + 5, fy - h - 1)
    grip = (fx - 9, fy - h - 24)
    pygame.draw.line(surf, (54, 40, 32), head, grip, 3)   # the handle...
    pygame.draw.line(surf, (96, 72, 52), (head[0] - 1, head[1] - 2), (grip[0] + 1, grip[1] + 1), 1)
    blade = [(head[0] - 8, head[1] - 4), (head[0] - 2, head[1] - 4), (head[0] + 6, head[1] + 1),
             (head[0] + 3, head[1] + 2), (head[0] - 2, head[1] - 1)]
    pygame.draw.polygon(surf, (236, 186, 60), blade)   # ...and its gold head, half buried
    pygame.draw.polygon(surf, (160, 110, 30), blade, 1)
    pygame.draw.line(surf, (255, 236, 150), (head[0] - 6, head[1] - 4), (head[0] - 1, head[1] - 4), 1)
    if (t * 0.5) % 1 < 0.12:   # (a glint)
        gx, gy = head[0] - 4, head[1] - 5
        pygame.draw.line(surf, (255, 250, 220), (gx - 3, gy), (gx + 3, gy), 1)
        pygame.draw.line(surf, (255, 250, 220), (gx, gy - 3), (gx, gy + 3), 1)


def draw_lightning_rod(surf, fx, fy, t, live=True, perched=False):
    """Grizzle's Lightning Rod: a copper spike on a little tripod, a coil of wire round it and a glowing ball on top
    (crackling while it's live). `perched`: up on something (a tent's ridge), with no shadow on the ground."""
    fx, fy = int(fx), int(fy)
    if not perched:
        _iso_shadow(surf, fx, fy, 8)
    apex = _ip(fx, fy, 0, 0, 12)
    feet = sorted((math.radians(a) for a in (45, 165, 285)), key=lambda a: math.cos(a) + math.sin(a))
    back = [a for a in feet if math.cos(a) + math.sin(a) < 0]
    for a in back:   # the tripod's back legs...
        pygame.draw.line(surf, (70, 64, 70), _ip(fx, fy, 8 * math.cos(a), 8 * math.sin(a), 0), apex, 2)
    pygame.draw.line(surf, (120, 80, 50), (fx, fy - 4), (fx, fy - 40), 3)   # the copper spike
    pygame.draw.line(surf, (220, 150, 90), (fx - 1, fy - 4), (fx - 1, fy - 40), 1)
    for a in feet:   # ...and the one in front of the spike
        if a not in back:
            pygame.draw.line(surf, (70, 64, 70), _ip(fx, fy, 8 * math.cos(a), 8 * math.sin(a), 0), apex, 2)
    for k in range(4):   # the coil, wound round it
        pygame.draw.polygon(surf, (200, 130, 70), _iso_ring(fx, fy, (0, 0, 22 + k * 4), 3.6, n=12), 1)
    glow = 0.6 + 0.4 * math.sin(t * 13) if live else 0.2
    pygame.draw.circle(surf, (120, 170, 220), (fx, fy - 43), 5)
    pygame.draw.circle(surf, (int(170 + 80 * glow), int(210 + 40 * glow), 255), (fx, fy - 43), 3)
    if live and (t * 7) % 1 < 0.4:   # a little crackle round the ball
        a = t * 11
        pygame.draw.line(surf, (220, 240, 255), (fx + math.cos(a) * 6, fy - 43 + math.sin(a) * 6),
                         (fx + math.cos(a + 1) * 10, fy - 43 + math.sin(a + 1) * 9), 1)


def draw_toolkit(surf, fx, fy, t, wound=True, geared=False):
    """The Clockwork Toolkit: a brass-cornered toolbox, lid propped open on spanners and a whirring gear (`geared`:
    with the Clockwork Gears fitted to it)."""
    fx, fy = int(fx), int(fy)
    _iso_shadow(surf, fx, fy, 13)
    x0, x1, y0, y1, h = -11, 11, -6, 6, 10
    lid = [_ip(fx, fy, x0, y0, h), _ip(fx, fy, x1, y0, h), _ip(fx, fy, x1, y0 - 4, h + 11),
           _ip(fx, fy, x0, y0 - 4, h + 11)]   # propped open, leaning back
    pygame.draw.polygon(surf, (130, 74, 50), lid)
    pygame.draw.polygon(surf, (70, 36, 24), lid, 1)
    box = _iso_box(surf, fx, fy, x0, x1, y0, y1, 0, h, (110, 60, 40), (70, 36, 24))
    inside = [_ip(fx, fy, x0 + 1.5, y0 + 1.5, h), _ip(fx, fy, x1 - 1.5, y0 + 1.5, h), _ip(fx, fy, x1 - 1.5, y1 - 1.5, h),
              _ip(fx, fy, x0 + 1.5, y1 - 1.5, h)]
    pygame.draw.polygon(surf, (52, 28, 20), inside)   # (it's open)
    for xa, xb in ((x0, x0 + 3), (x1 - 3, x1)):   # brass corners
        pygame.draw.polygon(surf, (210, 170, 70), [_ip(fx, fy, xa, y1, 0), _ip(fx, fy, xb, y1, 0), _ip(fx, fy, xb, y1, h),
                                                   _ip(fx, fy, xa, y1, h)])
    pygame.draw.polygon(surf, (180, 140, 56), box["right"], 2)
    pygame.draw.line(surf, (170, 170, 180), _ip(fx, fy, -6, -1, h - 2), _ip(fx, fy, -8, 1, h + 11), 3)   # a spanner
    _iso_gear(surf, fx, fy, (3, 0, h + 7), 5.5, "y", t * 3 if wound else 0, (200, 180, 120))   # a gear, turning
    if geared:
        draw_gear_addon(surf, fx, fy, t, wound)


def draw_gear_addon(surf, fx, fy, t, running=True):
    """The Clockwork Gears, fitted to the Clockwork Toolkit (drawn over it, at its feet): a train of brass cogs up
    its end, another meshing with the gear on top, and a big wind-up key in its side, turning."""
    fx, fy = int(fx), int(fy)
    spin = t * 3 if running else 0.0
    brass, dark = (226, 186, 84), (150, 110, 40)
    pygame.draw.line(surf, dark, _ip(fx, fy, 11.5, -3, 3), _ip(fx, fy, 11.5, 3, 14), 2)   # (their bracket)
    _iso_gear(surf, fx, fy, (11.5, -2.5, 5), 4.5, "x", -spin * 1.2, brass)   # cogs up its end...
    _iso_gear(surf, fx, fy, (11.5, 3, 12), 3.5, "x", spin * 1.6, brass)
    _iso_gear(surf, fx, fy, (-4, 0, 21), 4, "y", -spin * 1.4, brass)       # ...one meshing with the gear on top
    root, tip = _ip(fx, fy, -5, 6, 5), _ip(fx, fy, -5, 11, 5)   # the wind-up key, sticking out of its side...
    pygame.draw.line(surf, dark, root, tip, 2)
    turn = abs(math.cos(t * 2)) if running else 1.0   # (...turning)
    for side in (-1, 1):
        cx, cy = tip[0] + side * 3.5 * turn, tip[1] - 1
        pygame.draw.ellipse(surf, brass, (cx - 3 * turn - 1, cy - 3, 6 * turn + 2, 6))
        pygame.draw.ellipse(surf, dark, (cx - 3 * turn - 1, cy - 3, 6 * turn + 2, 6), 1)


def draw_pocket_watch(surf, fx, fy, t, running=True, hanging=False):
    """The Pocket Watch: a big brass watch, hands turning - hung by its chain from a little wooden stand, or
    (`hanging`) from whatever's at (fx, fy), swaying gently below it."""
    fx, fy = int(fx), int(fy)
    if hanging:   # dangling: its chain from (fx, fy), the face turned down-right
        sway = math.sin(t * 1.6) * 2.5
        end = (fx + sway, fy + 9)
        pygame.draw.line(surf, (200, 170, 70), (fx, fy), end, 1)
        pygame.draw.circle(surf, (200, 170, 70), (int(end[0]), int(end[1])), 2)
        _watch_face(surf, end[0] + sway * 0.4, end[1] + 11, (0, 0, 0), "x", t, running)
        return
    _iso_shadow(surf, fx, fy, 10)
    _iso_box(surf, fx, fy, -9, 9, -5, 5, 0, 3, (110, 76, 46))   # the stand's foot...
    post_lo, post_hi, arm = _ip(fx, fy, -6, 0, 3), _ip(fx, fy, -6, 0, 38), _ip(fx, fy, 6, 0, 38)
    pygame.draw.line(surf, (96, 66, 40), post_lo, post_hi, 3)   # ...its post and arm
    pygame.draw.line(surf, (96, 66, 40), post_hi, arm, 3)
    pygame.draw.line(surf, (200, 170, 70), _ip(fx, fy, 4, 0, 37), _ip(fx, fy, 4, 0, 31), 1)   # the chain
    crown = _ip(fx, fy, 4, 0, 30.5)
    pygame.draw.circle(surf, (200, 170, 70), (int(crown[0]), int(crown[1])), 2)
    _watch_face(surf, fx, fy, (4, 0, 20), "y", t, running)


def _watch_face(surf, fx, fy, face, plane, t, running):
    """The Pocket Watch itself, standing up on `plane` at `face`: brass case, cream face, the hours and its hands."""
    back = (face[0] - 2, face[1], face[2]) if plane == "x" else (face[0], face[1] - 2, face[2])
    pygame.draw.polygon(surf, (150, 110, 40), _iso_ring(fx, fy, back, 10, plane, 24))   # its back...
    pygame.draw.polygon(surf, (230, 190, 80), _iso_ring(fx, fy, face, 10, plane, 24))   # ...case...
    pygame.draw.polygon(surf, (150, 110, 40), _iso_ring(fx, fy, face, 10, plane, 24), 1)
    pygame.draw.polygon(surf, (245, 240, 225), _iso_ring(fx, fy, face, 7.5, plane, 24))   # ...and face
    for k in range(12):   # the hours
        a = k * math.tau / 12
        pygame.draw.line(surf, (150, 130, 110), _iso_ring(fx, fy, face, 6.5, plane, 1, a)[0],
                         _iso_ring(fx, fy, face, 7.3, plane, 1, a)[0], 1)
    turn = t if running else 0.0
    centre = _ip(fx, fy, *face)
    for a, length, w in ((turn * 2, 5.5, 1), (turn * 0.2, 3.5, 2)):   # the hands
        tip = _iso_ring(fx, fy, face, length, plane, 1, math.pi / 2 - a)[0]
        pygame.draw.line(surf, (40, 30, 30), centre, tip, w)


def draw_kiln(surf, fx, fy, t, lit=True):
    """The Hands Tent's kiln: a squat round brick kiln with a domed top, a stubby chimney and a mouth glowing with the
    fire inside."""
    fx, fy = int(fx), int(fy)
    brick, dark = (110, 54, 40), (80, 38, 28)
    R, body_h, dome_h = 14, 16, 10
    rx, ry = R * 1.41, R * 0.71
    _iso_shadow(surf, fx, fy, R + 3)

    def level(z):   # the kiln's round outline at height z
        return pygame.Rect(fx - rx, fy - z - ry, rx * 2, ry * 2)
    pygame.draw.ellipse(surf, shade(brick, 0.7), level(0))
    pygame.draw.rect(surf, shade(brick, 0.85), (fx - rx, fy - body_h, rx * 2, body_h))
    for side, f in ((-1, 0.95), (1, 0.7)):   # (lit from the left)
        pygame.draw.rect(surf, shade(brick, f), (fx if side > 0 else fx - rx, fy - body_h, rx, body_h))
    pygame.draw.ellipse(surf, shade(brick, 0.85), level(0).inflate(-2, -2))
    for z in (4, 8, 12):   # brick courses, round the front
        pygame.draw.arc(surf, dark, level(z), math.pi, math.tau, 1)
    _iso_box(surf, fx, fy, 3, 8, -10, -5, body_h, body_h + dome_h + 7, (90, 44, 32))   # the chimney, at the back
    top = level(body_h)
    arc = [(fx + rx * math.cos(a), fy - body_h - (ry + dome_h) * math.sin(a)) for a in
           (k * math.pi / 16 for k in range(17))]   # the dome, over the top...
    ledge = [(fx - rx * math.cos(a), fy - body_h + ry * math.sin(a)) for a in (k * math.pi / 16 for k in range(17))]
    pygame.draw.polygon(surf, brick, arc + ledge)
    pygame.draw.polygon(surf, shade(brick, 1.15), [(fx - rx * 0.7 * math.cos(a), fy - body_h - (ry + dome_h) * 0.85 *
                                                    math.sin(a)) for a in (k * math.pi / 16 for k in range(4, 13))])
    pygame.draw.arc(surf, dark, top, math.pi, math.tau, 2)   # ...on a ledge
    pygame.draw.arc(surf, dark, level(body_h + 6).inflate(-6, -3), math.pi * 1.05, math.pi * 1.95, 1)
    face = math.radians(60)   # the mouth's facing: towards you, and a little to the left

    def arch(half, sill, spring, rise):   # an arched opening on the kiln's wall
        nx, ny, tx, ty = math.cos(face) * R, math.sin(face) * R, -math.sin(face), math.cos(face)
        pts = [(-half, sill), (-half, spring)] + [(half * math.cos(a), spring + rise * math.sin(a))
                                                  for a in (k * math.pi / 8 for k in range(9))][::-1] + [(half, spring), (half, sill)]
        return [_ip(fx, fy, nx + tx * u, ny + ty * u, z) for u, z in pts]
    mouth = arch(6, 0, 8, 5)
    pygame.draw.polygon(surf, (40, 20, 16), mouth)
    pygame.draw.polygon(surf, dark, mouth, 2)
    if lit:
        glow = 0.6 + 0.4 * math.sin(t * 5)
        inner = arch(4, 1, 7, 3.5)
        pygame.draw.polygon(surf, (255, int(140 + 60 * glow), 60), inner)
        if (t * 1.3) % 1 < 0.6:   # smoke
            cx, cy = _ip(fx, fy, 5.5, -7.5, body_h + dome_h + 9)
            pygame.draw.circle(surf, (120, 116, 120), (int(cx + (t * 8) % 4), int(cy - (t * 20) % 8)), 3)


def draw_glaze_pots(surf, fx, fy, t):
    """Glazed Fists, fitted to the Kiln (drawn over it, at its feet): three pots of glaze by its left side - deep blue,
    green and white - drips down their sides, a brush in one."""
    fx, fy = int(fx), int(fy)
    for x, y, col in ((-15, 7, (230, 230, 220)), (-13, 13, (70, 150, 110)), (-8, 17, (60, 110, 200))):   # back to front
        px, py = _ip(fx, fy, x, y, 0)
        rx, ry, h = 4.5, 2.2, 7
        pygame.draw.ellipse(surf, (16, 12, 20), (px - rx - 1, py - ry, rx * 2 + 2, ry * 2 + 1))
        pygame.draw.rect(surf, (150, 100, 70), (px - rx, py - h, rx, h))
        pygame.draw.rect(surf, (120, 78, 54), (px, py - h, rx, h))
        pygame.draw.ellipse(surf, (120, 78, 54), (px - rx, py - ry, rx * 2, ry * 2))
        pygame.draw.ellipse(surf, col, (px - rx, py - h - ry, rx * 2, ry * 2))   # the glaze in it...
        pygame.draw.line(surf, col, (px - 2, py - h), (px - 2, py - h + 4), 2)    # ...and a drip down its side
    bx, by = _ip(fx, fy, -8, 17, 7)
    pygame.draw.line(surf, (150, 110, 70), (bx + 1, by - 1), (bx + 5, by - 9), 2)   # a brush
    pygame.draw.line(surf, (60, 110, 200), (bx + 5, by - 9), (bx + 6, by - 11), 2)


def draw_potters_wheel(surf, fx, fy, t, live=True):
    """The Potter's Wheel, fitted to the Clay Pit (drawn over it, at the pit's middle): a kick-wheel on a little
    stand at its edge, a half-thrown clay soldier spinning on it."""
    fx, fy = int(fx), int(fy)
    wx, wy = _ip(fx, fy, -6, 19, 0)   # (at the pit's front-left edge)
    _iso_shadow(surf, wx, wy, 7)
    _iso_box(surf, wx, wy, -5, 5, -5, 5, 0, 7, (120, 84, 52))   # the stand
    top = wy - 8
    pygame.draw.ellipse(surf, (90, 70, 60), (wx - 9, top - 4, 18, 9))   # the wheel...
    pygame.draw.ellipse(surf, (150, 140, 130), (wx - 8, top - 4, 16, 7))
    spin = t * 6 if live else 0.0
    for k in range(3):   # (its spokes, going round)
        a = spin + k * math.tau / 3
        pygame.draw.line(surf, (110, 100, 96), (wx, top - 1), (wx + math.cos(a) * 7, top - 1 + math.sin(a) * 3), 1)
    body = pygame.Rect(wx - 4, top - 13, 8, 12)   # ...and the clay soldier on it, half made
    pygame.draw.ellipse(surf, (186, 116, 74), body)
    pygame.draw.ellipse(surf, (150, 88, 56), (wx - 4, top - 15, 8, 5))   # (its helmet)
    stripe = body.x + 1 + int((spin * 2) % 6)   # (a ridge where Mitts' thumb went, turning)
    pygame.draw.line(surf, (214, 150, 104), (stripe, body.y + 3), (stripe, body.bottom - 2), 1)


def draw_clay_pit(surf, fx, fy, t, alive=True):
    """The Hands Tent's clay pit: a pool of wet river clay ringed with stones, bubbling - and (once it's yours) a
    mudling peeping out."""
    fx, fy = int(fx), int(fy)
    R = 15
    pygame.draw.ellipse(surf, (90, 56, 36), (fx - R * 1.41 - 2, fy - R * 0.71 - 1, R * 2.83 + 4, R * 1.41 + 2))
    pygame.draw.ellipse(surf, (150, 96, 62), (fx - R * 1.41 + 3, fy - R * 0.71 + 2, R * 2.83 - 6, R * 1.41 - 3))
    pygame.draw.ellipse(surf, (170, 112, 74), (fx - 10, fy - 5, 12, 4))   # (wet shine)
    stones = sorted(((math.cos(k * math.tau / 11) * R, math.sin(k * math.tau / 11) * R) for k in range(11)),
                    key=lambda p: p[0] + p[1])
    for k, (x, y) in enumerate(stones):   # the stones round its rim, back to front
        sx, sy = _ip(fx, fy, x, y, 0)
        size = 5 + (k * 7) % 3
        pygame.draw.ellipse(surf, (96, 92, 100), (sx - size / 2, sy - size / 2 - 1, size, size * 0.7))
        pygame.draw.ellipse(surf, (130, 126, 136), (sx - size / 2 + 1, sy - size / 2 - 1, size - 2, size * 0.4))
    for k in range(3):   # bubbles
        q = (t * 0.8 + k * 0.33) % 1
        bx, by = _ip(fx, fy, -7 + k * 5, 3 - k * 4, 0)
        pygame.draw.circle(surf, (190, 130, 90), (int(bx), int(by - q * 3)), max(1, int(3 * (1 - q))), 1)
    if alive:
        peek = max(0.0, math.sin(t * 0.9)) ** 2
        if peek > 0.05:
            mx, my = _ip(fx, fy, 5, 3, 0)
            draw_mudling(surf, mx, my, t, 0.0, 10.0 * peek)


def draw_target_dummy(surf, fx, fy, t):
    """Wren's Target Dummy: a straw figure on a post with a crossbar for arms, a sackcloth head and a red-and-white
    target painted on its chest (and a fuse poking out of the stuffing)."""
    fx, fy = int(fx), int(fy)
    sway = math.sin(t * 2 + fx * 0.05) * 1.5
    _iso_shadow(surf, fx, fy, 9)
    _iso_box(surf, fx, fy, -10, 10, -2, 2, 0, 3, (110, 76, 46))   # its foot: two planks, crossed
    _iso_box(surf, fx, fy, -2, 2, -10, 10, 0, 3, (110, 76, 46))
    pygame.draw.line(surf, (96, 66, 40), (fx, fy - 3), (fx + sway, fy - 40), 3)   # the post

    def up(x, y, z):   # (the top sways)
        px, py = _ip(fx, fy, x, y, z)
        return px + sway * z / 40, py
    pygame.draw.line(surf, (96, 66, 40), up(0, -12, 30), up(0, 12, 30), 3)   # arms, along the crossbar
    body = pygame.Rect(0, 0, 18, 22)
    body.midbottom = (fx + sway, fy - 14)
    pygame.draw.ellipse(surf, (110, 86, 50), body.inflate(2, 2))
    pygame.draw.ellipse(surf, (214, 182, 112), body)
    for r, col in ((7, (210, 50, 50)), (5, (245, 240, 230)), (3, (210, 50, 50))):   # the target, facing down-right
        pts = _iso_ring(fx, fy, (6, 0, 24), r, "x", 18)
        pygame.draw.polygon(surf, col, [(x + sway * 24 / 40, y) for x, y in pts])
    head = (int(fx + sway), fy - 41)
    pygame.draw.circle(surf, (110, 86, 50), head, 7)
    pygame.draw.circle(surf, (200, 172, 120), head, 6)
    for ex in (-1, 4):   # stitched eyes, looking down-right with the target
        pygame.draw.line(surf, (110, 86, 50), (head[0] + ex - 1, head[1]), (head[0] + ex + 1, head[1] + 2), 1)
    for k in range(3):   # straw poking out
        pygame.draw.line(surf, (230, 200, 120), (body.x + 2, body.y + 6 + k * 4), (body.x - 3, body.y + 4 + k * 5), 1)
    spark = (fx + sway - 8, body.y + 1)   # the fuse
    pygame.draw.line(surf, (40, 30, 30), (fx + sway - 4, body.y + 5), spark, 1)
    if (t * 6) % 1 < 0.5:
        pygame.draw.circle(surf, (255, 210, 90), spark, 2)


def draw_brazier(surf, fx, fy, t, lit=True, explosive=False):
    """The Combat Tent's brazier: an iron bowl on three legs, a bundle of pitch-soaked arrows leaning on it, and
    (once it's yours) a fire burning in it. `explosive`: with the Explosive Arrows' powder keg and bomb tips."""
    fx, fy = int(fx), int(fy)
    _iso_shadow(surf, fx, fy, 11)
    for k in range(4):   # the arrows, leaning on it from behind - a bundle, fanned out at the top
        x0, y0 = _ip(fx, fy, 7 + k, -12 + k, 0)
        x1, y1 = _ip(fx, fy, k * 4, -11 + k * 2.5, 31 - k)
        pygame.draw.line(surf, (150, 110, 70), (x0, y0), (x1, y1), 2)
        pygame.draw.polygon(surf, (60, 50, 50), [(x1 - 2, y1 - 1), (x1 + 2, y1 - 1), (x1, y1 - 5)])
    legs = sorted((math.radians(a) for a in (45, 165, 285)), key=lambda a: math.cos(a) + math.sin(a))
    for a in legs:   # three legs, splayed
        pygame.draw.line(surf, (50, 46, 50), _ip(fx, fy, 9 * math.cos(a), 9 * math.sin(a), 0),
                         _ip(fx, fy, 5 * math.cos(a), 5 * math.sin(a), 15), 3)
    R, rim = 10, 22
    rx, ry = R * 1.41, R * 0.71
    cy = fy - rim
    pygame.draw.ellipse(surf, (54, 50, 56), (fx - rx * 0.6, cy - 4, rx * 1.2, ry + 8))   # the bowl's belly...
    pygame.draw.ellipse(surf, (70, 64, 70), (fx - rx, cy - ry, rx * 2, ry * 2))           # ...its rim...
    pygame.draw.ellipse(surf, (40, 36, 42), (fx - rx, cy - ry, rx * 2, ry * 2), 2)
    inner = pygame.Rect(fx - rx + 3, cy - ry + 2, rx * 2 - 6, ry * 2 - 4)
    pygame.draw.ellipse(surf, (60, 30, 24) if lit else (34, 30, 34), inner)                # ...and the coals in it
    if lit:
        for k in range(5):
            ex, ey = _ip(fx, fy, math.cos(k * 1.3) * 5, math.sin(k * 1.3) * 5, rim)
            pygame.draw.circle(surf, (255, 120 + 30 * (k % 3), 40), (int(ex), int(ey)), 2)
        for k, (col, h) in enumerate((((255, 120, 40), 18), ((255, 190, 70), 12), ((255, 245, 190), 6))):
            flick = math.sin(t * (9 + k * 3)) * 2
            pygame.draw.polygon(surf, col, [(fx - 9 + k * 3, cy), (fx + flick, cy - h), (fx + 9 - k * 3, cy)])
    if explosive:
        draw_powder_keg(surf, fx, fy, t, lit)


def draw_powder_keg(surf, fx, fy, t, lit=True):
    """Explosive Arrows, fitted to the Fire Arrows' brazier (drawn over it, at its feet): a clay bulb of black powder
    tied behind each arrowhead in the bundle, and a little powder keg beside it, its fuse fizzing."""
    fx, fy = int(fx), int(fy)
    for k in range(4):   # bomb tips on the arrows
        x1, y1 = _ip(fx, fy, k * 4, -11 + k * 2.5, 31 - k)
        pygame.draw.circle(surf, (40, 36, 40), (int(x1), int(y1 + 1)), 3)
        pygame.draw.circle(surf, (110, 100, 100), (int(x1 - 1), int(y1)), 1)
    kx, ky = _ip(fx, fy, -9, 10, 0)   # the keg
    rx, ry, h = 6.5, 3.2, 10
    pygame.draw.ellipse(surf, (16, 12, 20), (kx - rx - 1, ky - ry, rx * 2 + 2, ry * 2 + 1))
    pygame.draw.ellipse(surf, (74, 48, 30), (kx - rx, ky - ry, rx * 2, ry * 2))
    pygame.draw.rect(surf, (104, 68, 40), (kx - rx, ky - h, rx, h))
    pygame.draw.rect(surf, (80, 52, 32), (kx, ky - h, rx, h))
    for z in (2, h - 2):   # iron hoops
        pygame.draw.arc(surf, (60, 60, 66), (kx - rx, ky - z - ry, rx * 2, ry * 2), math.pi, math.tau, 2)
    pygame.draw.ellipse(surf, (130, 92, 56), (kx - rx, ky - h - ry, rx * 2, ry * 2))
    pygame.draw.ellipse(surf, (90, 60, 36), (kx - rx + 2, ky - h - ry + 1, rx * 2 - 4, ry * 2 - 2), 1)
    fuse = [(kx + 1, ky - h - 1), (kx + 3, ky - h - 5), (kx + 1, ky - h - 8)]
    pygame.draw.lines(surf, (40, 30, 30), False, fuse, 1)
    if lit and (t * 6) % 1 < 0.55:   # (fizzing)
        pygame.draw.circle(surf, (255, 210, 90), fuse[-1], 2)
        pygame.draw.circle(surf, (255, 250, 210), fuse[-1], 1)


def draw_ledger_desk(surf, bx, by, t, lit=True, wing=False):
    """The Crooked Ledger on its writing desk at camp: a fat book lying open on the desk, a quill in the inkpot, and
    (once it's yours) a candle burning low beside it. `wing`: Rounding Errors' extra leg of the desk, making an L,
    with a little abacus on it."""
    bx, by = int(bx), int(by)

    def _q(x, y, z):   # (the desk stands turned a quarter: its length runs down-left)
        return _ip(bx, by, y, x, z)
    _iso_shadow(surf, bx, by, 14)
    top = 17
    for x, y in ((-11, -5), (11, -5), (-11, 5), (11, 5)):   # legs
        pygame.draw.line(surf, WOOD_DARK, _q(x, y, 0), _q(x, y, top), 3)
    _iso_box(surf, bx, by, -7, 7, -13, 13, top, top + 3, WOOD, WOOD_DARK)   # the desk top
    z = top + 3
    for side in (-1, 1):   # the open book: two pages, lines of figures, a red ribbon down the middle
        page = [_q(0, -5, z + 1.5), _q(side * 9, -5, z + 0.5), _q(side * 9, 5, z + 0.5),
                _q(0, 5, z + 1.5)]
        pygame.draw.polygon(surf, (236, 226, 196), page)
        pygame.draw.polygon(surf, (150, 130, 100), page, 1)
        for k in range(3):
            y = -3 + k * 3
            pygame.draw.line(surf, (176, 160, 136), _q(side * 2, y, z + 1.3), _q(side * 7.5, y, z + 0.7), 1)
    pygame.draw.line(surf, (200, 40, 50), _q(0, -5, z + 1.5), _q(0, 5, z + 1.5), 2)
    pygame.draw.line(surf, (200, 40, 50), _q(0, 5, z + 1.5), _q(0.5, 8, z - 3), 2)
    _iso_box(surf, bx, by, -6, -3, 9, 12, z, z + 3, (40, 40, 52))   # the inkpot...
    pygame.draw.line(surf, (240, 240, 230), _q(10.5, -4.5, z + 3), _q(14, -8, z + 15), 2)   # ...quill
    if lit:   # a candle burning low
        cx, cy = _q(-10, -4, z)
        pygame.draw.rect(surf, (236, 230, 210), (cx - 2, cy - 8, 4, 8))
        pygame.draw.ellipse(surf, (250, 246, 232), (cx - 2, cy - 9, 4, 2))
        flick = math.sin(t * 11) * 1.2
        pygame.draw.polygon(surf, (255, 200, 90), [(cx - 2, cy - 8), (cx + flick, cy - 15), (cx + 2, cy - 8)])
    if wing:
        draw_desk_wing(surf, bx, by, t, lit)


def draw_desk_wing(surf, bx, by, t, live=True):
    """Rounding Errors, at camp: a second leg of the ledger desk (drawn over it, at its feet) running off its back
    end to make an L - and on it, Mr. Pennyworth's little abacus, one bead that won't stop sliding."""
    bx, by = int(bx), int(by)
    top = 17
    for x, y in ((20, -12), (20, -5), (9, -5)):   # its legs
        pygame.draw.line(surf, WOOD_DARK, _ip(bx, by, x, y, 0), _ip(bx, by, x, y, top), 3)
    _iso_box(surf, bx, by, 7, 21, -13, -4, top, top + 3, WOOD, WOOD_DARK)
    z = top + 3
    wood = (130, 86, 50)
    for x in (9, 19):   # the abacus: its frame...
        pygame.draw.line(surf, wood, _ip(bx, by, x, -9, z), _ip(bx, by, x, -9, z + 11), 2)
    for zz in (z + 1, z + 11):
        pygame.draw.line(surf, wood, _ip(bx, by, 9, -9, zz), _ip(bx, by, 19, -9, zz), 2)
    colours = [(200, 60, 50), (240, 200, 80), (80, 150, 220)]
    for row, zz in enumerate((z + 3.5, z + 6, z + 8.5)):   # ...its rods and beads
        pygame.draw.line(surf, (170, 160, 150), _ip(bx, by, 9.5, -9, zz), _ip(bx, by, 18.5, -9, zz), 1)
        beads = [10.5, 12] if row != 1 else [10.5]
        if row == 1:   # (the one that sticks - and slides)
            beads.append(14.5 + (2.5 * math.sin(t * 2) if live else 0))
        else:
            beads.append(17.5)
        for x in beads:
            px, py = _ip(bx, by, x, -9, zz)
            pygame.draw.ellipse(surf, colours[row], (px - 2, py - 1.5, 4, 3))


def _draw_mimic(surf, e, rise, t, hovered, dy=0):
    """A treasure chest... with teeth. Lurking it sits shut on its block, a tongue flicking out now and then;
    sprung, it hops along on stubby legs, lid gaping, and chomps whoever it catches."""
    fx, fy = _feet(e, rise)
    fy += dy
    lurking = e.state == "lurking"
    attacking = e.state == "attacking" and e.victim is not None
    flash = e.flash > 0
    wood = (255, 255, 255) if flash else WOOD
    if hovered:
        pygame.draw.ellipse(surf, BAD, (fx - 16, fy - 6, 32, 12), 2)
    pygame.draw.ellipse(surf, (16, 12, 20), (fx - 12, fy - 4, 24, 8))
    hop = 0 if lurking else abs(math.sin(e.anim_t * 7)) * (5 if e.state == "hunting" else 2)
    if attacking:
        fx += struggle_shake(t, 0.9) * 0.5
    base = fy - hop
    if not lurking:   # stubby legs under it
        for d in (-6, 6):
            pygame.draw.line(surf, WOOD_DARK, (fx + d, base - 2), (fx + d + math.sin(e.anim_t * 14 + d) * 2, fy), 3)
    box = pygame.Rect(fx - 11, base - 12, 22, 11)
    pygame.draw.rect(surf, wood, box, border_radius=2)
    pygame.draw.rect(surf, WOOD_DARK, box, 1, border_radius=2)
    for bx in (box.x + 4, box.right - 5):   # iron-bound with gold
        pygame.draw.line(surf, CHEST_GOLD, (bx, box.y), (bx, box.bottom - 1), 2)
    if lurking:   # shut tight - but now and then a tongue flicks out of the seam
        lid = pygame.Rect(fx - 11, base - 18, 22, 7)
        pygame.draw.rect(surf, wood, lid, border_top_left_radius=5, border_top_right_radius=5)
        pygame.draw.rect(surf, WOOD_DARK, lid, 1, border_top_left_radius=5, border_top_right_radius=5)
        pygame.draw.rect(surf, CHEST_GOLD, (fx - 2, base - 14, 4, 4))   # the clasp
        if (t + e.x * 3.1) % 4.0 < 0.3:
            pygame.draw.line(surf, (220, 80, 100), (fx + 4 * e.facing, base - 12), (fx + 9 * e.facing, base - 9), 2)
        return
    gape = 0.55 + 0.35 * abs(math.sin(t * (14 if attacking else 5)))   # how wide the lid is open
    pygame.draw.polygon(surf, (90, 20, 30), [(box.x + 1, box.y + 1), (box.right - 1, box.y + 1),
                                             (box.right - 1, box.y - 8 * gape), (box.x + 1, box.y - 8 * gape)])
    for k in range(4):   # teeth along both jaws
        tx = box.x + 3 + k * 5
        pygame.draw.polygon(surf, (245, 240, 225), [(tx, box.y), (tx + 4, box.y), (tx + 2, box.y - 3)])
    lid_y = box.y - 8 - 8 * gape
    lid = pygame.Rect(fx - 11, int(lid_y), 22, 7)
    pygame.draw.rect(surf, wood, lid, border_top_left_radius=5, border_top_right_radius=5)
    pygame.draw.rect(surf, WOOD_DARK, lid, 1, border_top_left_radius=5, border_top_right_radius=5)
    for k in range(4):
        tx = lid.x + 3 + k * 5
        pygame.draw.polygon(surf, (245, 240, 225), [(tx, lid.bottom), (tx + 4, lid.bottom), (tx + 2, lid.bottom + 3)])
    for d in (-4, 4):   # beady eyes glinting inside the lid
        pygame.draw.circle(surf, (255, 220, 80), (fx + d, int(lid.bottom + 4)), 1)
    tongue = [(fx, box.y - 2), (fx + 7 * e.facing, box.y + 2 + math.sin(t * 9) * 2), (fx + 10 * e.facing, box.y)]
    pygame.draw.lines(surf, (220, 80, 100), False, tongue, 2)
    if e.targetable:
        _hp_bar(surf, fx, int(lid_y) - 6, e.hp / e.max_hp, BAD, 24)


def _draw_golem(surf, e, rise, t, hovered, dy=0):
    """A hulking golem of stacked boulders. Armoured, it's plated in mossy slabs; once a heavy hit cracks it,
    the slabs are gone and a glowing core shows through the cracks."""
    fx, fy = _feet(e, rise)
    fy += dy
    entering = e.state == "emerging"
    attacking = e.state == "attacking" and e.victim is not None
    cracked = getattr(e, "cracked", False)
    flash = e.flash > 0
    stone = (255, 255, 255) if flash else STONE_COL
    if hovered:
        pygame.draw.ellipse(surf, BAD, (fx - 20, fy - 7, 40, 14), 2)
    if not entering:
        pygame.draw.ellipse(surf, (16, 12, 20), (fx - 15, fy - 5, 30, 10))
    if attacking:
        fx += struggle_shake(t, 0.5) * 0.4
    stomp = math.sin(e.anim_t * 4) * 2 if e.state == "hunting" else 0
    for d, st in ((-6, stomp), (6, -stomp)):   # stumpy legs
        pygame.draw.rect(surf, STONE_EDGE, (fx + d - 4, fy - 10 + min(0, st), 8, 10 - min(0, st)), border_radius=3)
    body = pygame.Rect(fx - 14, fy - 34, 28, 26)
    pygame.draw.rect(surf, stone, body, border_radius=9)
    pygame.draw.rect(surf, STONE_EDGE, body, 2, border_radius=9)
    if cracked:   # the armour's gone: glowing cracks over a hot core
        pulse = 0.6 + 0.4 * math.sin(t * 5)
        glow = (255, int(150 + 60 * pulse), 70)
        for pts in (((fx - 8, fy - 30), (fx - 2, fy - 22), (fx - 6, fy - 14)),
                    ((fx + 6, fy - 31), (fx + 2, fy - 24), (fx + 8, fy - 16)), ((fx - 1, fy - 18), (fx + 3, fy - 10))):
            pygame.draw.lines(surf, glow, False, pts, 2)
    else:   # mossy slabs of armour over the chest and shoulders
        for plate in ((fx - 13, fy - 33, 12, 12), (fx + 1, fy - 33, 12, 12), (fx - 9, fy - 20, 18, 10)):
            pygame.draw.rect(surf, (104, 102, 116), plate, border_radius=3)
            pygame.draw.rect(surf, STONE_EDGE, plate, 1, border_radius=3)
        pygame.draw.line(surf, MOSS, (fx - 12, fy - 33), (fx - 4, fy - 33), 2)
        pygame.draw.line(surf, MOSS, (fx + 3, fy - 21), (fx + 9, fy - 21), 2)
    head = (int(fx + 2 * e.facing), fy - 39)   # a small boulder of a head, sunk between the shoulders
    pygame.draw.circle(surf, stone, head, 7)
    pygame.draw.circle(surf, STONE_EDGE, head, 7, 1)
    eye = (255, 170, 80) if cracked else (120, 230, 255)
    for d in (-3, 2):
        pygame.draw.line(surf, eye, (head[0] + d * e.facing, head[1] - 1), (head[0] + (d + 2) * e.facing, head[1] - 1), 2)
    shoulder = (fx, fy - 30)
    if attacking:   # both great fists round the miner
        nx, ny = miner_neck(e.victim, rise, t)
        for d in (-4, 4):
            pygame.draw.line(surf, STONE_EDGE, (shoulder[0] + d, shoulder[1]), (nx + d, ny), 6)
            pygame.draw.circle(surf, stone, (int(nx + d), int(ny)), 5)
    else:   # long arms swinging, knuckles near the ground
        swing = math.sin(e.anim_t * 4) * 3
        for d in (-1, 1):
            hand = (fx + d * 16, fy - 10 + swing * d)
            pygame.draw.line(surf, STONE_EDGE, (fx + d * 12, fy - 30), hand, 6)
            pygame.draw.circle(surf, stone, (int(hand[0]), int(hand[1])), 6)
            pygame.draw.circle(surf, STONE_EDGE, (int(hand[0]), int(hand[1])), 6, 1)
    if not entering:
        _hp_bar(surf, head[0], head[1] - 13, e.hp / e.max_hp, BAD, 30)


def _draw_shade(surf, e, rise, t, hovered, dy=0, alpha=1.0):
    """A drifting knot of darkness with two pale eyes, ragged wisps trailing beneath it."""
    cx, cy = _base_anchor(e, rise, t)
    cy += dy
    flash = e.flash > 0
    if e.state == "hunting":   # (its pool of darkness on the ground is drawn by the renderer)
        fx, fy = _feet(e, rise)
        pygame.draw.ellipse(surf, (10, 8, 16), (fx - 12, fy - 4, 24, 8))
    if hovered:
        pygame.draw.circle(surf, BAD, (int(cx), int(cy)), 24, 2)
    img = pygame.Surface((80, 90), pygame.SRCALPHA)
    ox, oy = 40, 40
    body = (230, 230, 245) if flash else (24, 16, 40)
    for k in range(9):   # a churning knot of dark puffs
        a = k / 9 * math.tau + e.anim_t * 0.8
        r = 9 + 3 * math.sin(e.anim_t * 2 + k)
        pygame.draw.circle(img, (*body, 200), (int(ox + math.cos(a) * 8), int(oy + math.sin(a) * 6)), int(r))
    pygame.draw.circle(img, (*body, 235), (ox, oy), 12)
    pygame.draw.circle(img, (110, 80, 170, 110), (ox, oy), 19, 2)   # a faint violet rim, so it reads on the dark
    for k in range(4):   # ragged wisps trailing below
        x = ox - 10 + k * 7
        sway = math.sin(e.anim_t * 3 + k) * 3
        pygame.draw.polygon(img, (*body, 170), [(x - 3, oy + 8), (x + 3, oy + 8), (x + sway, oy + 26 + (k % 2) * 5)])
    glint = 0.75 + 0.25 * math.sin(e.anim_t * 1.7)
    for d in (-5, 5):   # two pale eyes
        pygame.draw.ellipse(img, (int(200 * glint), int(215 * glint), 255, 255), (ox + d - 2 + e.facing, oy - 4, 4, 6))
    img.set_alpha(int(255 * alpha))
    surf.blit(img, (cx - ox, cy - oy))
    if e.targetable:
        _hp_bar(surf, cx, cy - 22, e.hp / e.max_hp, BAD, 24)


FUR, FUR_DARK, CLAW = (120, 88, 64), (78, 56, 40), (230, 220, 200)


def _draw_burrower(surf, e, rise, t, hovered, dy=0):
    """Underground: a mound of earth ploughing along, clods flying. Up: a big-clawed, near-blind mole-thing."""
    fx, fy = _feet(e, rise)
    fy += dy
    flash = e.flash > 0
    if hovered:
        pygame.draw.ellipse(surf, BAD, (fx - 16, fy - 7, 32, 14), 2)
    if e.state == "burrowing":   # just the mound it pushes up as it tunnels
        churn = math.sin(e.anim_t * 10) * 1.5
        pygame.draw.ellipse(surf, (16, 12, 20), (fx - 12, fy - 4, 24, 8))
        mound = pygame.Rect(fx - 11, fy - 9 + churn, 22, 11)
        pygame.draw.ellipse(surf, (255, 255, 255) if flash else (118, 88, 60), mound)
        pygame.draw.ellipse(surf, (72, 52, 34), mound, 1)
        for k in range(3):   # clods of earth thrown up behind it
            a = (e.anim_t * 3 + k * 0.33) % 1
            pygame.draw.circle(surf, (96, 70, 46), (int(fx - 8 * e.facing - a * 6 * e.facing), int(fy - 8 - a * 10 + a * a * 12)), 2)
        pygame.draw.line(surf, (60, 44, 30), (fx + 9 * e.facing, fy - 2), (fx + 14 * e.facing, fy + 1), 1)   # cracks ahead
        return
    attacking = e.state == "attacking" and e.victim is not None
    fur = (255, 255, 255) if flash else FUR
    pygame.draw.ellipse(surf, (16, 12, 20), (fx - 12, fy - 4, 24, 8))
    if attacking:
        fx += struggle_shake(t, 0.6) * 0.5
    body = pygame.Rect(fx - 11, fy - 20, 22, 18)
    pygame.draw.ellipse(surf, fur, body)
    pygame.draw.ellipse(surf, FUR_DARK, body, 1)
    head = (int(fx + 7 * e.facing), fy - 16)
    pygame.draw.circle(surf, fur, head, 7)
    pygame.draw.circle(surf, (240, 140, 150), (head[0] + 6 * e.facing, head[1] + 1), 3)   # pink snout
    pygame.draw.circle(surf, (20, 16, 20), (head[0] + 2 * e.facing, head[1] - 3), 1)       # tiny eye
    reach = math.sin(e.anim_t * 8) * 3
    for d in (-1, 1):   # great digging claws
        paw = (fx + (8 + reach) * e.facing + d * 3, fy - 8 + d * 3)
        pygame.draw.circle(surf, fur, (int(paw[0]), int(paw[1])), 4)
        for k in range(3):
            pygame.draw.line(surf, CLAW, paw, (paw[0] + 6 * e.facing, paw[1] - 2 + k * 2), 1)
    if e.targetable:
        _hp_bar(surf, fx, fy - 30, e.hp / e.max_hp, BAD, 22)


DRAWERS = {"zombie": _draw_zombie, "spider": _draw_spider, "bat": _draw_bat, "vampire": _draw_vampire,
           "wisp": _draw_wisp, "ghost": _draw_ghost, "eggsac": _draw_eggsac, "skeleton": _draw_skeleton,
           "slime": _draw_slime, "slimeling": _draw_slime, "slimechunk": _draw_slime,
           "mimic": _draw_mimic, "golem": _draw_golem, "shade": _draw_shade, "burrower": _draw_burrower}
DRAWERS.update({kind: DRAWERS[spec["look"]] for kind, spec in ENEMY_TYPES.items() if "look" in spec})   # bosses

from . import boss_sprites   # noqa: E402  (bosses with sprites of their own; it borrows the helpers above)

DRAWERS.update(boss_sprites.DRAWERS)
