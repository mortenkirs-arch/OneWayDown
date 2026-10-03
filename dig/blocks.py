"""Block types and layer generation."""
import random

from .config import GRID

# name: colour, base hp, base value, (min depth, chance) or None for base rock
BLOCKS = {
    "dirt":    dict(color=(139, 98, 62),   hp=2,  value=1,   ore=None),
    "stone":   dict(color=(122, 122, 132), hp=5,  value=2,   ore=None),
    "coal":    dict(color=(122, 122, 132), hp=8,  value=6,   ore=(2, 0.14),  fleck=(30, 30, 34)),
    "copper":  dict(color=(122, 122, 132), hp=11, value=12,  ore=(6, 0.11),  fleck=(214, 128, 60)),
    "iron":    dict(color=(122, 122, 132), hp=15, value=22,  ore=(12, 0.09), fleck=(226, 206, 190)),
    "gold":    dict(color=(122, 122, 132), hp=22, value=45,  ore=(20, 0.07), fleck=(255, 212, 60)),
    "ruby":    dict(color=(122, 122, 132), hp=32, value=100, ore=(32, 0.05), fleck=(225, 40, 70)),
    "diamond": dict(color=(122, 122, 132), hp=48, value=230, ore=(45, 0.035), fleck=(110, 235, 245)),
}
ORE_ORDER = ["diamond", "ruby", "gold", "iron", "copper", "coal"]

# How fast things get tougher / richer per metre of depth (blocks and monsters share these).
# Value grows a little slower than health, so each metre is slightly harder than the last;
# upgrades are what keep you ahead.
HP_GROWTH = 1.12
VALUE_GROWTH = 1.115


def hp_scale(depth):
    return HP_GROWTH ** depth


def value_scale(depth):
    return VALUE_GROWTH ** depth


class Block:
    __slots__ = ("kind", "hp", "max_hp", "value")

    def __init__(self, kind, depth, hp=None):
        spec = BLOCKS[kind]
        self.kind = kind
        self.max_hp = spec["hp"] * hp_scale(depth)
        self.hp = self.max_hp if hp is None else hp
        self.value = spec["value"] * value_scale(depth)


def generate_layer(depth, ore_boost=1.0, rng=random):
    layer = {}
    base = "dirt" if depth < 4 else "stone"
    for x in range(GRID):
        for y in range(GRID):
            kind = base
            for ore in ORE_ORDER:
                mind, chance = BLOCKS[ore]["ore"]
                if depth >= mind and rng.random() < chance * ore_boost * (1 + (depth - mind) * 0.01):
                    kind = ore
                    break
            layer[(x, y)] = Block(kind, depth)
    return layer
