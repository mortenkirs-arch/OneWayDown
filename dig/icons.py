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
