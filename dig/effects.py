"""Short-lived visual effects in screen space."""
import math
import random


class Particle:
    def __init__(self, x, y, color, big=False):
        self.x, self.y = x, y
        ang = random.uniform(0, math.tau)
        spd = random.uniform(40, 160 if big else 90)
        self.vx, self.vy = math.cos(ang) * spd, math.sin(ang) * spd - random.uniform(60, 160)
        self.color = color
        self.size = random.randint(3, 6) if big else random.randint(2, 3)
        self.life = random.uniform(0.4, 0.9)

    def update(self, dt):
        self.vy += 500 * dt
        self.x += self.vx * dt
        self.y += self.vy * dt
        self.life -= dt


class Smoke:
    """A puff of smoke that drifts up, swells and fades."""

    def __init__(self, x, y, size=10, life=1.4):
        self.x, self.y = x + random.uniform(-size, size), y + random.uniform(-size * 0.5, size * 0.5)
        self.vx = random.uniform(-14, 14)
        self.vy = -random.uniform(18, 40)
        self.r = size * random.uniform(0.6, 1.0)
        self.life = self.max_life = life * random.uniform(0.7, 1.2)
        self.shade = random.randint(70, 120)

    def update(self, dt):
        self.x += self.vx * dt
        self.y += self.vy * dt
        self.vx *= 0.97
        self.r += 16 * dt
        self.life -= dt


class CoinFly:
    """A gold coin arcing from where it was earned to where it's going (the gold counter, an upgrade)."""

    def __init__(self, start, target, delay=0.0, duration=0.65, size=6, lift=(60, 130)):
        self.start, self.target = start, target
        self.t = -delay
        self.duration = duration * random.uniform(0.85, 1.15)
        self.size = size
        self.lift = random.uniform(*lift)         # how high above the higher end the arc peaks
        self.spread = random.uniform(-40, 40)     # sideways scatter at the start of the arc

    @property
    def progress(self):
        return max(0.0, min(1.0, self.t / self.duration))

    @property
    def arrived(self):
        return self.t >= self.duration

    def update(self, dt):
        self.t += dt

    def pos(self):
        p = self.progress
        e = p * p * (3 - 2 * p)                   # ease in-out
        (sx, sy), (tx, ty) = self.start, self.target
        cx, cy = (sx + tx) / 2 + self.spread, min(sy, ty) - self.lift
        x = (1 - e) ** 2 * sx + 2 * (1 - e) * e * cx + e ** 2 * tx
        y = (1 - e) ** 2 * sy + 2 * (1 - e) * e * cy + e ** 2 * ty
        return x, y


class Floater:
    def __init__(self, text, x, y, color, life=1.1, size=24, coin=False):
        self.text, self.x, self.y, self.color = text, x, y, color
        self.life = self.max_life = life
        self.size = size
        self.coin = coin   # draw a gold coin in front of the text

    def update(self, dt):
        self.y -= 40 * dt
        self.life -= dt
