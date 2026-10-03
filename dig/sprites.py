"""Character sprites: miners, gravestones and enemies, plus enemy hit-testing."""
import math

import pygame

from .config import BAD, GOOD, MUTED
from .iso import iso

CHOKED_SKIN = (150, 130, 210)
ENEMY_HIT_RADIUS = {"zombie": 26, "spider": 20}


def _lerp(a, b, t):
    return tuple(int(x + (y - x) * t) for x, y in zip(a, b))


def _feet(e, rise):
    fx, fy = iso(e.x, e.y, e.draw_z + rise)
    return int(fx), int(fy)


def _hp_bar(surf, cx, top, frac, width=32):
    bar = pygame.Rect(0, 0, width, 5)
    bar.midbottom = (cx, top)
    pygame.draw.rect(surf, (20, 16, 24), bar.inflate(2, 2))
    pygame.draw.rect(surf, GOOD if frac > 0.5 else BAD, (bar.x, bar.y, int(bar.w * max(0, frac)), bar.h))


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


def draw_miner(surf, fonts, m, rise, t):
    fx, fy = _feet(m, rise)
    if m.state == "down":
        draw_grave(surf, fonts, fx, fy, m.respawn)
        return
    grabbed = m.state == "grabbed"
    lift = m.height
    pygame.draw.ellipse(surf, (16, 12, 20), (fx - 11, fy - 4, 22, 8))
    if grabbed:
        fx += struggle_shake(t)
        kick = math.sin(t * 22) * 4                       # legs kicking
        pygame.draw.line(surf, (60, 50, 40), (fx - 3, fy - 9), (fx - 3 + kick, fy - 1), 3)
        pygame.draw.line(surf, (60, 50, 40), (fx + 3, fy - 9), (fx + 3 - kick, fy - 1), 3)
        bob = 0
    else:
        bob = abs(math.sin(t * 10)) * 2 if m.anim == 0 else 0
    body = pygame.Rect(fx - 7, fy - 26 - bob - lift, 14, 18 + lift)
    head = (fx, int(fy - 32 - bob - lift))
    _draw_hair_back(surf, m, head)
    pygame.draw.rect(surf, m.shirt, body, border_radius=4)
    pygame.draw.rect(surf, (60, 50, 40), (fx - 7, fy - 10 - bob, 14, 8), border_radius=2)
    skin = _lerp(m.skin, CHOKED_SKIN, 1 - m.hp / m.max_hp) if grabbed else m.skin
    pygame.draw.circle(surf, skin, head, 7)
    _draw_face(surf, m, head, grabbed)
    pygame.draw.ellipse(surf, (240, 200, 40), (head[0] - 9, head[1] - 10, 18, 9))
    pygame.draw.circle(surf, (255, 250, 200), (head[0] + 5 * m.facing, head[1] - 6), 2)
    if m.style == "mohawk":
        _draw_mohawk(surf, m, head)
    # pickaxe: normal swing, or flailing wildly while grabbed
    # (rests raised in front of the miner so it doesn't hide their face)
    ang = math.sin(t * 16) * 1.4 if grabbed else (0.35 + m.anim * 2.0) * m.facing
    hx, hy = fx + 7 * m.facing, fy - 20 - bob - lift
    ex, ey = hx + math.sin(ang) * 18, hy - math.cos(ang) * 18
    pygame.draw.line(surf, (120, 82, 44), (hx, hy), (ex, ey), 3)
    perp = (math.cos(ang) * 8, math.sin(ang) * 8)
    pygame.draw.line(surf, (190, 190, 200), (ex - perp[0], ey - perp[1]), (ex + perp[0], ey + perp[1]), 3)
    if m.hp < m.max_hp:
        _hp_bar(surf, fx, fy - 46 - lift, m.hp / m.max_hp, 26)
    if grabbed and int(t * 4) % 2 == 0:
        img = fonts[26].render("!!", True, BAD)
        surf.blit(img, img.get_rect(midbottom=(fx, fy - 50 - lift)))


def draw_grave(surf, fonts, fx, fy, secs):
    pygame.draw.ellipse(surf, (92, 68, 48), (fx - 14, fy - 6, 28, 10))
    stone = pygame.Rect(fx - 9, fy - 28, 18, 25)
    pygame.draw.rect(surf, (128, 128, 140), stone, border_top_left_radius=9, border_top_right_radius=9)
    pygame.draw.rect(surf, (80, 80, 92), stone, 2, border_top_left_radius=9, border_top_right_radius=9)
    pygame.draw.line(surf, (80, 80, 92), (fx, fy - 23), (fx, fy - 10), 2)
    pygame.draw.line(surf, (80, 80, 92), (fx - 5, fy - 19), (fx + 5, fy - 19), 2)
    img = fonts[20].render(f"{math.ceil(secs)}s", True, MUTED)
    surf.blit(img, img.get_rect(midbottom=(fx, fy - 31)))


# ----- enemies -------------------------------------------------------------
def enemy_anchor(e, rise, t):
    """Centre of the enemy's body on screen; used for clicking and effects."""
    if e.kind == "spider" and e.state == "attacking" and e.victim:
        hx, hy = miner_head(e.victim, rise, t)
        return hx, hy - 6
    fx, fy = _feet(e, rise)
    return (fx, fy - 22) if e.kind == "zombie" else (fx, fy - 8)


def pick_enemy(world, pos, t):
    for e in reversed(world.enemies):
        if e.state == "emerging" and e.timer < 0.3:
            continue
        ax, ay = enemy_anchor(e, world.rise, t)
        if math.hypot(pos[0] - ax, pos[1] - ay) <= ENEMY_HIT_RADIUS[e.kind]:
            return e
    return None


def draw_enemy(surf, e, rise, t, hovered=False):
    if e.kind == "zombie":
        _draw_zombie(surf, e, rise, t, hovered)
    else:
        _draw_spider(surf, e, rise, t, hovered)


def _draw_zombie(surf, e, rise, t, hovered):
    fx, fy = _feet(e, rise)
    attacking = e.state == "attacking" and e.victim is not None
    flash = e.flash > 0
    skin = (255, 255, 255) if flash else e.spec["skin"]
    shirt = (255, 255, 255) if flash else e.spec["shirt"]
    if hovered:
        pygame.draw.ellipse(surf, BAD, (fx - 17, fy - 7, 34, 14), 2)
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
    else:           # arms stretched out in front
        reach = math.sin(e.anim_t * 4)
        for d in (-2, 2):
            pygame.draw.line(surf, skin, (shoulder[0], shoulder[1] + d),
                             (shoulder[0] + 15 * e.facing, shoulder[1] - 2 + d + reach), 4)
    _hp_bar(surf, head[0], head[1] - 11, e.hp / e.max_hp)


def _draw_spider(surf, e, rise, t, hovered):
    attacking = e.state == "attacking" and e.victim is not None
    cx, cy = enemy_anchor(e, rise, t)
    color = (255, 255, 255) if e.flash > 0 else e.spec["skin"]
    leg_col = (255, 255, 255) if e.flash > 0 else (40, 32, 50)
    if hovered:
        pygame.draw.ellipse(surf, BAD, (cx - 20, cy - 10, 40, 20), 2)
    if not attacking:
        pygame.draw.ellipse(surf, (16, 12, 20), (cx - 12, cy + 4, 24, 8))
    bite = math.sin(t * 20) * 2 if attacking else 0
    cy += bite
    for i in range(4):
        wig = math.sin(e.anim_t * (24 if attacking else 18) + i * 1.7) * 2
        for s in (-1, 1):
            knee = (cx + s * (9 + i * 2), cy - 7 + i * 2 + wig)
            # attacking legs curl down around the miner's head
            foot = (cx + s * (8 + i * 2), cy + 12 + i) if attacking else (cx + s * (14 + i * 3), cy + 5 + i * 2 - wig)
            pygame.draw.lines(surf, leg_col, False, [(cx + s * 3, cy), knee, foot], 2)
    pygame.draw.ellipse(surf, color, (cx - 10, cy - 7, 20, 13))
    head = (int(cx + 8 * e.facing), int(cy + 1))
    pygame.draw.circle(surf, color, head, 5)
    pygame.draw.circle(surf, (240, 50, 50), (head[0] + 2 * e.facing, head[1] - 1), 1)
    pygame.draw.circle(surf, (240, 50, 50), (head[0] + 4 * e.facing, head[1]), 1)
    _hp_bar(surf, cx, cy - 12, e.hp / e.max_hp, 26)
