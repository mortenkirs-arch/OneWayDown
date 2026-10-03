"""Isometric projection, cube drawing and polygon hit-testing."""
import random
from contextlib import contextmanager

import pygame

from .config import BLOCK_H, BOARD_ORIGIN, TILE_H, TILE_W
from .util import shade

_origin = BOARD_ORIGIN


@contextmanager
def origin_at(pos):
    """Temporarily project around a different screen origin (e.g. menu decorations)."""
    global _origin
    saved, _origin = _origin, pos
    try:
        yield
    finally:
        _origin = saved


def iso(gx, gy, gz):
    """Grid coordinates (gz in block units) -> screen pixels."""
    return (_origin[0] + (gx - gy) * TILE_W / 2,
            _origin[1] + (gx + gy) * TILE_H / 2 - gz * BLOCK_H)


def cube_faces(x, y, z):
    """Screen polygons of the three visible faces of a cube whose top is at height z."""
    return {
        "top": [iso(x, y, z), iso(x + 1, y, z), iso(x + 1, y + 1, z), iso(x, y + 1, z)],
        "left": [iso(x, y + 1, z), iso(x + 1, y + 1, z), iso(x + 1, y + 1, z - 1), iso(x, y + 1, z - 1)],
        "right": [iso(x + 1, y, z), iso(x + 1, y + 1, z), iso(x + 1, y + 1, z - 1), iso(x + 1, y, z - 1)],
    }


def point_in_poly(pt, poly):
    px, py = pt
    inside = False
    j = len(poly) - 1
    for i in range(len(poly)):
        xi, yi = poly[i]
        xj, yj = poly[j]
        if (yi > py) != (yj > py) and px < (xj - xi) * (py - yi) / (yj - yi) + xi:
            inside = not inside
        j = i
    return inside


def draw_cube(surf, x, y, z, color, fleck=None, seed=0, outline=True):
    """Draw a unit cube whose top face sits at height z. Returns its face polygons."""
    faces = cube_faces(x, y, z)
    top, left, right = faces["top"], faces["left"], faces["right"]
    pygame.draw.polygon(surf, shade(color, 1.0), top)
    pygame.draw.polygon(surf, shade(color, 0.72), left)
    pygame.draw.polygon(surf, shade(color, 0.55), right)
    if fleck:
        rng = random.Random(seed)
        for _ in range(5):
            u, v = rng.uniform(0.2, 0.8), rng.uniform(0.2, 0.8)
            px, py = iso(x + u, y + v, z)
            pygame.draw.circle(surf, fleck, (int(px), int(py)), rng.randint(2, 4))
        for _ in range(3):
            u, h = rng.uniform(0.15, 0.85), rng.uniform(0.2, 0.8)
            px, py = iso(x + u, y + 1, z - h)
            pygame.draw.circle(surf, shade(fleck, 0.75), (int(px), int(py)), rng.randint(2, 3))
    if outline:
        edge = shade(color, 0.4)
        pygame.draw.polygon(surf, edge, top, 1)
        pygame.draw.lines(surf, edge, False, [left[0], left[3], left[2], right[3], right[0]], 1)
        pygame.draw.line(surf, edge, left[1], left[2], 1)
    return faces
