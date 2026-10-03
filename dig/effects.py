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


class Floater:
    def __init__(self, text, x, y, color, life=1.1, size=24):
        self.text, self.x, self.y, self.color = text, x, y, color
        self.life = self.max_life = life
        self.size = size

    def update(self, dt):
        self.y -= 40 * dt
        self.life -= dt
