"""Tiny procedural icons for upgrade nodes."""
import math

import pygame

from .util import shade


def draw_icon(surf, kind, c, s, col):
    """Draw icon `kind` centred on c with half-size s."""
    x, y = c
    dark = shade(col, 0.45)
    if kind == "pick":
        pygame.draw.line(surf, col, (x - s * 0.6, y + s * 0.7), (x + s * 0.4, y - s * 0.3), 4)
        pygame.draw.arc(surf, col, (x - s * 0.5, y - s * 0.9, s * 1.6, s * 1.2), 0.3, 2.6, 4)
    elif kind == "miner":
        pygame.draw.circle(surf, col, (x, y - s * 0.25), s * 0.35)
        pygame.draw.arc(surf, col, (x - s * 0.5, y - s * 0.85, s, s * 0.8), 0, math.pi, 4)
        pygame.draw.rect(surf, col, (x - s * 0.45, y + s * 0.2, s * 0.9, s * 0.6), border_radius=4)
    elif kind == "boot":
        pygame.draw.polygon(surf, col, [(x - s * 0.4, y - s * 0.7), (x + s * 0.1, y - s * 0.7),
                                        (x + s * 0.1, y + s * 0.1), (x + s * 0.7, y + s * 0.3),
                                        (x + s * 0.7, y + s * 0.7), (x - s * 0.4, y + s * 0.7)])
    elif kind == "team":
        for dx, dy in ((-0.5, 0.1), (0.5, 0.1), (0, -0.25)):
            pygame.draw.circle(surf, col, (x + dx * s, y + dy * s - s * 0.2), s * 0.24)
            pygame.draw.rect(surf, col, (x + dx * s - s * 0.25, y + dy * s + s * 0.1, s * 0.5, s * 0.45),
                             border_radius=3)
    elif kind == "clock":
        pygame.draw.circle(surf, col, c, s * 0.75, 3)
        pygame.draw.line(surf, col, c, (x, y - s * 0.5), 3)
        pygame.draw.line(surf, col, c, (x + s * 0.35, y + s * 0.15), 3)
    elif kind == "star":
        pts = []
        for i in range(10):
            r = s * (0.8 if i % 2 == 0 else 0.35)
            a = -math.pi / 2 + i * math.pi / 5
            pts.append((x + math.cos(a) * r, y + math.sin(a) * r))
        pygame.draw.polygon(surf, col, pts)
    elif kind == "bolt":
        pygame.draw.polygon(surf, col, [(x + s * 0.1, y - s * 0.85), (x - s * 0.5, y + s * 0.1),
                                        (x - s * 0.05, y + s * 0.1), (x - s * 0.2, y + s * 0.85),
                                        (x + s * 0.5, y - s * 0.15), (x + s * 0.05, y - s * 0.15)])
    elif kind == "hand":
        pygame.draw.rect(surf, col, (x - s * 0.45, y - s * 0.1, s * 0.9, s * 0.8), border_radius=6)
        for i in range(4):
            fx = x - s * 0.42 + i * s * 0.25
            pygame.draw.rect(surf, col, (fx, y - s * 0.75, s * 0.18, s * 0.75), border_radius=3)
        pygame.draw.rect(surf, col, (x + s * 0.35, y - s * 0.05, s * 0.4, s * 0.2), border_radius=3)
    elif kind == "wave":
        pygame.draw.circle(surf, col, c, s * 0.2)
        for r in (0.5, 0.8):
            pygame.draw.circle(surf, col, c, s * r, 3)
    elif kind == "cursor":
        pygame.draw.polygon(surf, col, [(x - s * 0.45, y - s * 0.8), (x - s * 0.45, y + s * 0.5),
                                        (x - s * 0.1, y + s * 0.2), (x + s * 0.2, y + s * 0.8),
                                        (x + s * 0.4, y + s * 0.7), (x + s * 0.1, y + s * 0.1),
                                        (x + s * 0.55, y + s * 0.05)])
    elif kind == "coin":
        pygame.draw.circle(surf, col, c, s * 0.75)
        pygame.draw.circle(surf, dark, c, s * 0.55, 2)
        pygame.draw.line(surf, dark, (x, y - s * 0.4), (x, y + s * 0.4), 3)
    elif kind == "gem":
        pygame.draw.polygon(surf, col, [(x - s * 0.7, y - s * 0.25), (x - s * 0.35, y - s * 0.65),
                                        (x + s * 0.35, y - s * 0.65), (x + s * 0.7, y - s * 0.25),
                                        (x, y + s * 0.75)])
        pygame.draw.line(surf, dark, (x - s * 0.7, y - s * 0.25), (x + s * 0.7, y - s * 0.25), 2)
    elif kind == "coins":
        for i in range(3):
            r = pygame.Rect(0, 0, s * 1.3, s * 0.5)
            r.center = (x, y + s * 0.45 - i * s * 0.38)
            pygame.draw.ellipse(surf, col, r)
            pygame.draw.ellipse(surf, dark, r, 2)
    elif kind == "crown":
        pygame.draw.polygon(surf, col, [(x - s * 0.75, y + s * 0.5), (x - s * 0.75, y - s * 0.5),
                                        (x - s * 0.35, y), (x, y - s * 0.7), (x + s * 0.35, y),
                                        (x + s * 0.75, y - s * 0.5), (x + s * 0.75, y + s * 0.5)])
    elif kind == "bomb":
        pygame.draw.circle(surf, col, (x - s * 0.1, y + s * 0.15), s * 0.6)
        pygame.draw.line(surf, col, (x + s * 0.25, y - s * 0.3), (x + s * 0.5, y - s * 0.65), 3)
        pygame.draw.circle(surf, (255, 200, 80), (x + s * 0.55, y - s * 0.72), s * 0.16)
    elif kind == "nugget":
        pygame.draw.polygon(surf, col, [(x - s * 0.7, y + s * 0.2), (x - s * 0.35, y - s * 0.5),
                                        (x + s * 0.2, y - s * 0.65), (x + s * 0.7, y - s * 0.1),
                                        (x + s * 0.5, y + s * 0.55), (x - s * 0.3, y + s * 0.6)])
        pygame.draw.circle(surf, (255, 255, 255), (x - s * 0.1, y - s * 0.2), max(2, s * 0.12))
    # ----- crew ------------------------------------------------------------
    elif kind == "map":
        pygame.draw.polygon(surf, col, [(x - s * 0.75, y - s * 0.5), (x - s * 0.25, y - s * 0.65),
                                        (x + s * 0.25, y - s * 0.5), (x + s * 0.75, y - s * 0.65),
                                        (x + s * 0.75, y + s * 0.5), (x + s * 0.25, y + s * 0.65),
                                        (x - s * 0.25, y + s * 0.5), (x - s * 0.75, y + s * 0.65)])
        for dx, dy in ((-0.45, 0.3), (-0.15, 0.0), (0.15, 0.15)):   # dotted trail
            pygame.draw.circle(surf, dark, (x + dx * s, y + dy * s), max(1, s * 0.08))
        pygame.draw.line(surf, dark, (x + s * 0.35, y - s * 0.3), (x + s * 0.55, y - s * 0.1), 2)
        pygame.draw.line(surf, dark, (x + s * 0.55, y - s * 0.3), (x + s * 0.35, y - s * 0.1), 2)
    elif kind == "wind":
        for i, (dy, ln) in enumerate(((-0.4, 1.1), (0.0, 1.4), (0.4, 0.9))):
            x0 = x - s * 0.7
            pygame.draw.line(surf, col, (x0, y + dy * s), (x0 + ln * s, y + dy * s), 3)
            pygame.draw.arc(surf, col, (x0 + ln * s - s * 0.2, y + dy * s - s * 0.35, s * 0.35, s * 0.35),
                            -math.pi / 2, math.pi, 3)
    elif kind == "jackhammer":
        pygame.draw.line(surf, col, (x - s * 0.55, y - s * 0.7), (x + s * 0.55, y - s * 0.7), 4)
        pygame.draw.rect(surf, col, (x - s * 0.3, y - s * 0.6, s * 0.6, s * 0.75), border_radius=3)
        pygame.draw.rect(surf, dark, (x - s * 0.3, y - s * 0.35, s * 0.6, s * 0.15))
        pygame.draw.line(surf, col, (x, y + s * 0.15), (x, y + s * 0.8), 3)
        for d in (-1, 1):   # it's rattling
            pygame.draw.line(surf, col, (x + d * s * 0.5, y + s * 0.35), (x + d * s * 0.75, y + s * 0.2), 2)
    elif kind == "lantern":
        pygame.draw.arc(surf, col, (x - s * 0.3, y - s * 0.95, s * 0.6, s * 0.5), 0, math.pi, 2)
        pygame.draw.rect(surf, col, (x - s * 0.45, y - s * 0.6, s * 0.9, s * 0.15))
        pygame.draw.rect(surf, col, (x - s * 0.38, y - s * 0.45, s * 0.76, s * 1.0), 2, border_radius=3)
        pygame.draw.circle(surf, (255, 225, 130), (x, y + s * 0.05), max(2, s * 0.22))
        pygame.draw.rect(surf, col, (x - s * 0.45, y + s * 0.55, s * 0.9, s * 0.15))
    elif kind == "tnt":
        for i, dy in enumerate((0.35, 0.0, -0.35)):   # sideways sticks, stacked
            pygame.draw.rect(surf, col, (x - s * 0.7 + (i % 2) * s * 0.1, y + dy * s - s * 0.15, s * 1.3, s * 0.3),
                             border_radius=3)
        pygame.draw.line(surf, dark, (x - s * 0.15, y - s * 0.55), (x - s * 0.15, y + s * 0.55), 2)
        pygame.draw.line(surf, col, (x + s * 0.6, y - s * 0.4), (x + s * 0.8, y - s * 0.75), 2)
        pygame.draw.circle(surf, (255, 200, 80), (x + s * 0.82, y - s * 0.8), max(2, s * 0.13))
    elif kind == "moon":
        pygame.draw.circle(surf, col, c, s * 0.7)
        pygame.draw.circle(surf, dark, (x + s * 0.3, y - s * 0.2), s * 0.6)
        pygame.draw.circle(surf, col, (x + s * 0.55, y + s * 0.45), max(1, s * 0.1))
    # ----- tools -----------------------------------------------------------
    elif kind == "tip":
        pygame.draw.line(surf, col, (x - s * 0.7, y + s * 0.7), (x + s * 0.1, y - s * 0.1), 4)
        pygame.draw.polygon(surf, (150, 235, 245), [(x + s * 0.05, y - s * 0.15), (x + s * 0.45, y - s * 0.75),
                                                   (x + s * 0.75, y - s * 0.45), (x + s * 0.15, y - s * 0.05)])
    elif kind == "drill":
        pygame.draw.polygon(surf, col, [(x - s * 0.45, y - s * 0.7), (x + s * 0.45, y - s * 0.7), (x, y + s * 0.8)])
        for i in range(3):
            yy = y - s * 0.45 + i * s * 0.4
            pygame.draw.line(surf, dark, (x - s * (0.35 - i * 0.1), yy), (x + s * (0.35 - i * 0.1), yy + s * 0.15), 2)
    elif kind == "anvil":
        pygame.draw.polygon(surf, col, [(x - s * 0.8, y - s * 0.35), (x + s * 0.6, y - s * 0.35),
                                        (x + s * 0.8, y - s * 0.15), (x + s * 0.3, y + s * 0.05),
                                        (x + s * 0.25, y + s * 0.45), (x - s * 0.25, y + s * 0.45),
                                        (x - s * 0.3, y + s * 0.05), (x - s * 0.55, y - s * 0.05)])
        pygame.draw.rect(surf, col, (x - s * 0.5, y + s * 0.45, s, s * 0.25))
    # ----- hands -----------------------------------------------------------
    elif kind == "bigbomb":
        pygame.draw.circle(surf, col, (x - s * 0.15, y + s * 0.15), s * 0.7)
        pygame.draw.line(surf, col, (x + s * 0.3, y - s * 0.35), (x + s * 0.55, y - s * 0.7), 3)
        for a in range(0, 360, 60):   # spiky spark
            r = math.radians(a)
            pygame.draw.line(surf, (255, 200, 80), (x + s * 0.6, y - s * 0.75),
                             (x + s * 0.6 + math.cos(r) * s * 0.25, y - s * 0.75 + math.sin(r) * s * 0.25), 2)
    elif kind == "touch":
        pygame.draw.circle(surf, (255, 205, 70), (x + s * 0.35, y - s * 0.35), s * 0.35)
        pygame.draw.rect(surf, col, (x - s * 0.6, y - s * 0.05, s * 0.75, s * 0.7), border_radius=5)
        pygame.draw.rect(surf, col, (x - s * 0.15, y - s * 0.6, s * 0.2, s * 0.65), border_radius=3)
    elif kind == "target":
        for r, w in ((0.75, 3), (0.45, 3)):
            pygame.draw.circle(surf, col, c, s * r, w)
        pygame.draw.circle(surf, col, c, max(2, s * 0.15))
    # ----- fortune ---------------------------------------------------------
    elif kind == "skull":
        pygame.draw.circle(surf, col, (x, y - s * 0.15), s * 0.6)
        pygame.draw.rect(surf, col, (x - s * 0.35, y + s * 0.2, s * 0.7, s * 0.45), border_radius=3)
        for d in (-1, 1):
            pygame.draw.circle(surf, dark, (x + d * s * 0.25, y - s * 0.15), max(2, s * 0.17))
        for d in (-0.15, 0.15):
            pygame.draw.line(surf, dark, (x + d * s, y + s * 0.35), (x + d * s, y + s * 0.65), 2)
    elif kind == "bag":
        pygame.draw.circle(surf, col, (x, y + s * 0.2), s * 0.6)
        pygame.draw.polygon(surf, col, [(x - s * 0.3, y - s * 0.7), (x + s * 0.3, y - s * 0.7),
                                        (x + s * 0.15, y - s * 0.3), (x - s * 0.15, y - s * 0.3)])
        pygame.draw.line(surf, dark, (x - s * 0.25, y - s * 0.32), (x + s * 0.25, y - s * 0.32), 2)
        pygame.draw.line(surf, dark, (x, y), (x, y + s * 0.45), 2)
    elif kind == "sun":
        pygame.draw.circle(surf, col, c, s * 0.42)
        for a in range(0, 360, 45):
            r = math.radians(a)
            pygame.draw.line(surf, col, (x + math.cos(r) * s * 0.55, y + math.sin(r) * s * 0.55),
                             (x + math.cos(r) * s * 0.85, y + math.sin(r) * s * 0.85), 3)
    # ----- combat ----------------------------------------------------------
    elif kind == "sword":
        pygame.draw.line(surf, col, (x - s * 0.55, y + s * 0.55), (x + s * 0.65, y - s * 0.65), 5)
        pygame.draw.line(surf, col, (x - s * 0.55, y + s * 0.1), (x - s * 0.1, y + s * 0.55), 4)
        pygame.draw.line(surf, col, (x - s * 0.55, y + s * 0.55), (x - s * 0.8, y + s * 0.8), 4)
    elif kind == "axe":
        pygame.draw.line(surf, col, (x - s * 0.5, y + s * 0.75), (x + s * 0.3, y - s * 0.6), 4)
        pygame.draw.polygon(surf, col, [(x + s * 0.1, y - s * 0.5), (x + s * 0.75, y - s * 0.75),
                                        (x + s * 0.6, y + s * 0.05), (x + s * 0.25, y - s * 0.1)])
    elif kind == "burst":
        pts = []
        for i in range(16):
            r = s * (0.85 if i % 2 == 0 else 0.4)
            a = i / 16 * math.tau
            pts.append((x + math.cos(a) * r, y + math.sin(a) * r))
        pygame.draw.polygon(surf, col, pts)
    elif kind == "slash":
        for d in (-0.35, 0, 0.35):
            pygame.draw.arc(surf, col, (x - s * 0.9 + d * s, y - s * 0.9 - d * s, s * 1.4, s * 1.4),
                            -0.3, 1.2, 3)
    elif kind == "shield":
        pygame.draw.polygon(surf, col, [(x - s * 0.65, y - s * 0.6), (x + s * 0.65, y - s * 0.6),
                                        (x + s * 0.6, y + s * 0.1), (x, y + s * 0.8), (x - s * 0.6, y + s * 0.1)])
        pygame.draw.line(surf, dark, (x, y - s * 0.5), (x, y + s * 0.6), 2)
        pygame.draw.line(surf, dark, (x - s * 0.55, y - s * 0.1), (x + s * 0.55, y - s * 0.1), 2)
    elif kind == "helmet":
        pygame.draw.circle(surf, col, (x, y + s * 0.2), s * 0.65, draw_top_left=True, draw_top_right=True)
        pygame.draw.rect(surf, col, (x - s * 0.85, y + s * 0.15, s * 1.7, s * 0.22), border_radius=3)
        pygame.draw.circle(surf, (255, 250, 200), (x, y - s * 0.2), max(2, s * 0.15))
    elif kind == "cross":
        pygame.draw.rect(surf, col, (x - s * 0.22, y - s * 0.7, s * 0.44, s * 1.4), border_radius=3)
        pygame.draw.rect(surf, col, (x - s * 0.7, y - s * 0.22, s * 1.4, s * 0.44), border_radius=3)
    elif kind == "fist":
        pygame.draw.rect(surf, col, (x - s * 0.55, y - s * 0.45, s * 1.1, s * 0.8), border_radius=6)
        for i in range(3):
            pygame.draw.line(surf, dark, (x - s * 0.2 + i * s * 0.25, y - s * 0.45),
                             (x - s * 0.2 + i * s * 0.25, y - s * 0.15), 2)
        pygame.draw.rect(surf, col, (x - s * 0.35, y + s * 0.3, s * 0.7, s * 0.4))
