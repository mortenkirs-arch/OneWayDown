"""Biomes: every BIOME_EVERY metres the dig breaks into a new kind of ground, with its own look.

Purely cosmetic. Each biome is data:
  name, accent   what the arrival banner and the HUD call it, and in what colour
  rock           base colour of the rock (and of ore blocks, under their flecks); dirt keeps its own colour
  earth          colour of the earth slab under the board
  bg             (top, bottom) colours of the background gradient behind everything
  ambient        drifting effect drawn behind the board: drips, sparkles, embers, dust, motes (or None)
  deco           extra detail on the blocks being dug: crystals, lava, glyphs, glow (or None)
"""
from .blocks import BLOCKS

BIOME_EVERY = 10   # (the same metres the bosses guard: each boss stands at the way into a new biome)

BIOMES = [
    dict(key="topsoil", name="The Topsoil", accent=(200, 170, 120), rock=(122, 122, 132), earth=(74, 56, 46),
         bg=((28, 22, 40), (10, 8, 16)), ambient=None, deco=None),
    dict(key="caverns", name="Stone Caverns", accent=(150, 180, 220), rock=(96, 110, 142), earth=(52, 62, 86),
         bg=((20, 26, 42), (6, 9, 18)), ambient="drips", deco=None),
    dict(key="crystal", name="Crystal Grotto", accent=(200, 150, 255), rock=(106, 92, 142), earth=(58, 46, 88),
         bg=((36, 20, 58), (10, 6, 24)), ambient="sparkles", deco="crystals"),
    dict(key="magma", name="Magma Depths", accent=(255, 130, 60), rock=(78, 64, 64), earth=(66, 32, 26),
         bg=((52, 16, 12), (14, 5, 6)), ambient="embers", deco="lava"),
    dict(key="ruins", name="Ancient Ruins", accent=(230, 200, 130), rock=(170, 146, 106), earth=(104, 84, 56),
         bg=((18, 34, 38), (5, 11, 14)), ambient="dust", deco="glyphs"),
    dict(key="abyss", name="The Abyss", accent=(120, 170, 255), rock=(54, 58, 78), earth=(26, 28, 44),
         bg=((8, 10, 24), (2, 2, 7)), ambient="motes", deco="glow"),
]


def biome_at(depth):
    """The biome a layer at this depth belongs to (the last one carries on for ever)."""
    return BIOMES[min(len(BIOMES) - 1, max(0, depth) // BIOME_EVERY)]


def block_color(kind, depth):
    """A block's base colour in its biome: dirt is always dirt, rock and ore take the biome's rock."""
    return BLOCKS[kind]["color"] if kind == "dirt" else biome_at(depth)["rock"]
