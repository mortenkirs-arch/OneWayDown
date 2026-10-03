"""Dynamite: thrown onto the board, fuse burns down, then it explodes (see World.detonate)."""
import math

THROW_SECS = 0.6        # flying in from off-screen
FUSE_SECS = 1.6         # sitting on the block with a lit fuse - the warning window
EXPLOSION_SECS = 0.7    # fireball animation
FUSE_LEN = 22           # px of fuse when freshly lit
STICK_W, STICK_H = 34, 9     # sticks lie sideways: W is the length, H the thickness
STICK_STAGGER = (0, 3, -2, 2)  # sideways offset of each stacked stick, so the pile looks hand-tied


class Bomb:
    def __init__(self, cell, radius, owner=None):
        self.cell = cell
        self.radius = radius          # 1 = 3x3, 2 = 5x5, 3 = 7x7
        self.owner = owner            # demolitionist who planted it (None = your thrown Dynamite)
        self.age = THROW_SECS if owner else 0.0   # planted charges skip the throw: fuse is already lit

    @property
    def landed(self):
        return self.age >= THROW_SECS

    @property
    def done(self):
        return self.age >= THROW_SECS + FUSE_SECS

    def fuse_left(self):
        """1 when just landed, 0 at detonation."""
        return max(0.0, min(1.0, (THROW_SECS + FUSE_SECS - self.age) / FUSE_SECS))

    def throw_progress(self):
        return min(1.0, self.age / THROW_SECS)

    @property
    def sticks(self):
        return 1 + self.radius   # 2 / 3 / 4 sticks as Bigger Bombs grows the blast


def fuse_points(base_x, base_y, length):
    """Curly fuse rising out of the end of the top stick; returns the points, last one is the lit tip."""
    pts = []
    steps = max(2, int(length / 2))
    for i in range(steps + 1):
        f = i / steps * length
        pts.append((base_x + f * 0.55 + math.sin(f * 0.45) * 2.5, base_y - f * 0.8))
    return pts
