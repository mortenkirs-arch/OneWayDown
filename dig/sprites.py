"""Character sprites: miners, gravestones and enemies, plus enemy hit-testing."""
import math
import random

import pygame

from .config import BAD, BLOCK_H, GOOD, GRID, MUTED
from .dynamite import FUSE_LEN, STICK_H, STICK_STAGGER, STICK_W, fuse_points
from .enemies import (ELITE_SCALE, ENEMY_TYPES, FLY_ALTITUDE, PILE_SECS, TELEGRAPH_SECS, THROW_ANIM_SECS,
                      THROW_RELEASE, TRANSFORM_SECS)
from .iso import current_origin, iso, origin_at
from .miners import CRIT_ANIM_SECS, LOOK_FIELDS

HI_VIS = (255, 140, 30)
HELMETS = {"miner": (240, 200, 40), "foreman": (245, 245, 250), "driller": (240, 130, 40),
           "guard": (62, 68, 86), "demolitionist": (200, 50, 45)}
STEEL, DIAMOND = (190, 190, 200), (110, 235, 245)   # pick head colour, before / after Diamond Tips
CRIT_SLAM = 0.3     # share of the crit animation spent slamming down (the rest is the recoil)
CRIT_WINDUP = -1.6  # pick angle at the start of a crit: raised back behind the shoulder
ENEMY_HIT_RADIUS = {"zombie": 26, "spider": 20, "bat": 20, "vampire": 26, "wisp": 16, "ghost": 24,
                    "zombieking": 54, "broodmother": 46, "vampirelord": 50, "lich": 50, "eggsac": 18,
                    "skeleton": 24, "greatbat": 48, "bonetyrant": 54,
                    "slime": 20, "slimeling": 14, "slimechunk": 24, "slimeking": 54}
BONE_COL, BONE_SHADE = (232, 226, 205), (150, 142, 120)
BOSS_CANVAS = (120, 200)   # a boss is drawn at normal size on this canvas, then scaled up
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


def pick_head_color(diamond_lv):
    """Steel turning to diamond blue as Diamond Tips levels up (fully blue at its max, 10)."""
    return _lerp(STEEL, DIAMOND, min(1.0, diamond_lv / 10))


def draw_miner(surf, fonts, m, rise, t, pick_level=0, spirit=False):
    fx, fy = _feet(m, rise)
    if m.state == "down":
        draw_grave(surf, fonts, fx, fy, m.respawn)
        return
    grabbed = m.state == "grabbed"
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
    pygame.draw.ellipse(surf, HELMETS.get(role, HELMETS["miner"]), (head[0] - 9, head[1] - 10, 18, 9))
    if foreman:
        pygame.draw.line(surf, HI_VIS, (head[0] - 6, head[1] - 7), (head[0] + 6, head[1] - 7), 2)
    lamp = (head[0] + 5 * m.facing, head[1] - 6)
    if role == "guard":   # a proper lantern on the helmet, glowing
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
    elif role == "driller":
        _draw_jackhammer(surf, m, fx, fy - max(0, bob), grabbed, t)
    elif role == "demolitionist":
        _draw_charge_stick(surf, m, fx, fy - bob - lift, skin, grabbed, t)
    else:
        # pickaxe: normal swing, flailing wildly while grabbed, or a crit's overhead slam
        # (rests raised in front of the miner so it doesn't hide their face)
        hx, hy = fx + 7 * m.facing, fy - 20 - bob - lift
        head_col = pick_head_color(pick_level)
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
    if getattr(e, "mode", "") == "pile":   # the Bone Tyrant in pieces on the ground
        fx, fy = _feet(e, rise)
        return fx, fy - 12
    ax, ay = _base_anchor(e, rise, t)
    scale = e.draw_scale
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
    if e.flying and e.state != "transforming":
        return fx, fy - e.altitude * BLOCK_H + _fly_bob(e)
    return (fx, fy - 22) if e.spec["grab"] == "side" else (fx, fy - 8)


def pick_enemy(world, pos, t):
    for e in reversed(world.enemies):
        if not e.targetable:
            continue
        ax, ay = enemy_anchor(e, world.rise, t)
        if math.hypot(pos[0] - ax, pos[1] - ay) <= ENEMY_HIT_RADIUS[e.kind] * (ELITE_SCALE if e.elite else 1):
            return e
    return None


def draw_enemy(surf, e, rise, t, hovered=False):
    scale = e.draw_scale
    if scale:
        _draw_boss(surf, e, rise, t, hovered, scale)
    else:
        _draw_enemy(surf, e, rise, t, hovered)


def _draw_enemy(surf, e, rise, t, hovered):
    if e.state == "emerging":
        _draw_entrance(surf, e, rise, t)
    elif e.state == "transforming":
        _draw_transform(surf, e, rise, t)
    else:
        DRAWERS[e.kind](surf, e, rise, t, hovered)


def _draw_boss(surf, e, rise, t, hovered, scale):
    """A boss: its monster's sprite drawn on a canvas around its feet, scaled up, with a crown on top."""
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
    big = pygame.transform.scale(canvas, (int(cw * scale), int(ch * scale)))
    tint = (255, 150, 140) if e.enraged else e.spec.get("boss_tint")
    if tint:
        big.fill(tint, special_flags=pygame.BLEND_RGB_MULT)
    surf.blit(big, (fx - ax * scale, fy - ay * scale))
    if e.state != "emerging" and e.boss:
        bx, by = enemy_anchor(e, rise, t)
        _draw_crown(surf, bx, by - e.spec.get("crown_lift", 40) * scale, t)


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
    fx, fy = _draw_clipped_rise(surf, e, rise, t, int((1 - _ease_out(p)) * 48))
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
    cy = fy - 8 - lift
    pygame.draw.line(surf, (215, 215, 225), (fx, 0), (fx, cy - 5), 1)
    _draw_spider(surf, e, rise, t, False, dy=-lift)


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
    _draw_bat(surf, e, rise, t, False, pos=(x, y))


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


DRAWERS = {"zombie": _draw_zombie, "spider": _draw_spider, "bat": _draw_bat, "vampire": _draw_vampire,
           "wisp": _draw_wisp, "ghost": _draw_ghost, "eggsac": _draw_eggsac, "skeleton": _draw_skeleton,
           "slime": _draw_slime, "slimeling": _draw_slime, "slimechunk": _draw_slime}
DRAWERS.update({kind: DRAWERS[spec["look"]] for kind, spec in ENEMY_TYPES.items() if "look" in spec})   # bosses
