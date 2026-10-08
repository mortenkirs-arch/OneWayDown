"""Block types and layer generation."""
import random

from .config import GRID

# name: colour, base hp, base value, (min depth, weight) or None for base rock. The weight is how common the
# ore is among the ore in a layer, once it has had a few metres to come in (see pick_ore).
BLOCKS = {
    "dirt":    dict(color=(139, 98, 62),   hp=1.4, value=1,  ore=None),   # one bare click, all the way down to 3m
    "stone":   dict(color=(122, 122, 132), hp=5,  value=2,   ore=None),
    "coal":    dict(color=(122, 122, 132), hp=8,  value=9,   ore=(2, 0.14),  fleck=(30, 30, 34)),
    "copper":  dict(color=(122, 122, 132), hp=11, value=24,  ore=(6, 0.11),  fleck=(214, 128, 60)),
    "iron":    dict(color=(122, 122, 132), hp=15, value=44,  ore=(12, 0.09), fleck=(226, 206, 190)),
    "gold":    dict(color=(122, 122, 132), hp=22, value=90,  ore=(20, 0.07), fleck=(255, 212, 60)),
    "ruby":    dict(color=(122, 122, 132), hp=32, value=200, ore=(32, 0.05), fleck=(225, 40, 70)),
    "diamond": dict(color=(122, 122, 132), hp=48, value=460, ore=(45, 0.035), fleck=(110, 235, 245)),
}
ORE_ORDER = ["diamond", "ruby", "gold", "iron", "copper", "coal"]

# How fast things get tougher / richer per metre of depth (blocks and monsters share these).
# Value grows a little slower than health, so each metre is slightly harder than the last;
# upgrades are what keep you ahead.
# Ore: a share of every layer, in veins of the same ore. The share creeps up with depth but is capped, so
# Prospector (more ore, and richer ore) stays worth having all the way down.
ORE_SHARE_START = 0.12      # share of a layer that is ore near the surface...
ORE_SHARE_DEEP = 0.25       # ...rising to this by ORE_SHARE_DEPTH, then holding
ORE_SHARE_DEPTH = 50
ORE_SHARE_CAP = 0.45        # never more than this, however much the boost
ORE_RAMP = 8                # metres a newly reachable ore takes to become as common as its weight says
VEIN_SIZES = (1, 2, 2, 3, 3, 4)
BONE_CHANCE = 0.08          # share of plain rock blocks (never ore) with old bones in them

HP_GROWTH = 1.12
VALUE_GROWTH = 1.115
DEEP_ROCK_FROM = 70         # the endgame: past this depth (within each expedition) the rock gets far harder...
DEEP_ROCK = 1.15            # ...this much more again every metre (on top of HP_GROWTH), without paying any more...
DEEP_CRACK = 0.8            # ...and anything that breaks rock by a share of it (charges, Vein Follower) manages only
                            # this much as much, metre on metre...
DEEP_ROCK_TO = 90           # ...until here: past it the rock only gets the usual harder, so the last few metres to
                            # 100 don't drag (deep enough to be an endgame, short enough to want another run)


def hp_scale(depth):
    return HP_GROWTH ** depth


def rock_scale(depth):
    """How tough a block is at this depth: the usual growth, and the endgame's deep rock past DEEP_ROCK_FROM."""
    return hp_scale(depth) * DEEP_ROCK ** deep_metres(depth)


def crack_share(depth):
    """Share of its usual bite a 'share of the block' hit keeps this deep (1 until DEEP_ROCK_FROM)."""
    return DEEP_CRACK ** deep_metres(depth)


def deep_metres(depth):
    """Metres of the endgame's deep rock above this depth (DEEP_ROCK_FROM to DEEP_ROCK_TO)."""
    return max(0, min(depth, DEEP_ROCK_TO) - DEEP_ROCK_FROM)


def value_scale(depth):
    return VALUE_GROWTH ** depth


class Block:
    __slots__ = ("kind", "hp", "max_hp", "value", "chest", "artifact", "bones")

    def __init__(self, kind, depth, hp=None, chest=False, artifact=False, bones=False):
        spec = BLOCKS[kind]
        self.kind = kind
        self.chest = chest   # Buried Treasure: bursts open with gold when the block breaks
        self.artifact = artifact   # hides an artifact (which one is decided when it breaks)
        self.bones = bones         # old bones in the rock: a little extra gold if you click it to pieces
        self.max_hp = spec["hp"] * rock_scale(depth)
        self.hp = self.max_hp if hp is None else hp
        self.value = spec["value"] * value_scale(depth)


def layer_value(layer):
    """Base value of every block in a layer (before upgrades)."""
    return sum(b.value for b in layer.values())


def ore_share(depth, boost=1.0):
    """Share of a layer at this depth that is ore."""
    base = ORE_SHARE_START + (ORE_SHARE_DEEP - ORE_SHARE_START) * min(1.0, max(0, depth) / ORE_SHARE_DEPTH)
    return min(ORE_SHARE_CAP, base * boost)


def ore_weights(depth, richness=1.0):
    """{ore: weight} for the ores reachable at this depth. Rarer ores get `richness` ** (tier / 2) on top."""
    weights = {}
    for tier, ore in enumerate(reversed(ORE_ORDER)):   # coal is tier 0, diamond the top
        mind, weight = BLOCKS[ore]["ore"]
        if depth >= mind:
            weights[ore] = weight * min(1.0, (depth - mind + 1) / ORE_RAMP) * richness ** (tier / 2)
    return weights


def generate_layer(depth, ore_boost=1.0, chest_chance=0.0, rng=random, richness=1.0):
    """A fresh layer: base rock with veins of ore through it. `ore_boost` raises the share of ore (capped),
    `richness` makes the rarer ores turn up more often (both from Prospector)."""
    base = "dirt" if depth < 4 else "stone"
    kinds = {(x, y): base for x in range(GRID) for y in range(GRID)}
    weights = ore_weights(depth, richness)
    left = round(GRID * GRID * ore_share(depth, ore_boost)) if weights else 0
    while left > 0:
        ore = rng.choices(list(weights), weights=list(weights.values()))[0]
        free = [c for c, k in kinds.items() if k == base]
        if not free:
            break
        vein = [rng.choice(free)]
        for _ in range(min(left, rng.choice(VEIN_SIZES)) - 1):   # grow the vein through neighbouring rock
            x, y = rng.choice(vein)
            around = [(x + dx, y + dy) for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1))
                      if kinds.get((x + dx, y + dy)) == base and (x + dx, y + dy) not in vein]
            if around:
                vein.append(rng.choice(around))
        for c in vein:
            kinds[c] = ore
        left -= len(vein)
    # bones go in plain rock only, so ore always wins the spot
    return {c: Block(k, depth, chest=rng.random() < chest_chance, bones=k == base and rng.random() < BONE_CHANCE)
            for c, k in kinds.items()}
