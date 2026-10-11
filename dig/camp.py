"""Base Camp: what survives the end of an expedition.

Beating The Void Maw at the bottom of an expedition (every EXPEDITION_DEPTH metres) brings the shaft down: the
crew scramble up the last rope, the gear is buried, and the artifacts are set into the foundations of a camp at the
bottom. You take on one hire there, then a new expedition starts below it - from scratch, but with the camp's people
for good. The depth keeps counting (101m, 102m...) while blocks and monsters replay the 1-100m curve exactly as
before - no tougher, no richer: with the camp's people along, every run should go easier than the last.

The camp is five tents on a board, one per upgrade branch. A tent's first upgrade is a hire: a permanent character
who digs, fights or earns in every expedition after (see HIRES; the scene is scenes/camp.py).
"""
from .world_layout import CHOMP_EVERY, MITTS_CLICKS

EXPEDITION_DEPTH = 100   # an expedition ends at this many metres (The Void Maw)
# The collapse when The Void Maw falls (seconds from its death): the floor caves in from its hole outwards while
# ropes come down and the crew climb out, then a fade to the camp
CRUMBLE_FROM = 2.2       # the floor starts to go, at the hole in the middle...
CRUMBLE_SPREAD = 0.5     # ...then outwards this many seconds a tile (a little ragged)
CRUMBLE_FALL = 30.0      # a cell drops this fast (block heights a second, squared)
ROPE_DROP = 0.5          # a rope takes this long to come down
COLLAPSE_FADE = 1.6      # the fade to black at the end...
COLLAPSE_SECS = 10.5     # ...which is over by now: on to the camp
CLIMB_STYLES = ("steady", "scramble", "struggle", "swing", "hauled", "spin", "waver")   # (how each crew member goes)
ROLE_CLIMB = {"foreman": "waver", "driller": "hauled", "demolitionist": "scramble", "medic": "swing",
              "hero": "steady", "blacksmith": "spin", "archer": "swing", "taxman": "hauled", "claygolem": "hauled"}

# The camp's five tents, one per upgrade branch. Each starts as a plain white tent; its first upgrade is a hire: a
# character who joins every expedition from then on, for good (the camp's own people are knocked out, never killed).
# pos: where the tent stands on the camp board (grid units, like a mine layer)
TENTS = {
    "crew":    dict(name="Crew Tent", hire="hero", pos=(2.4, 2.2)),
    "tools":   dict(name="Tools Tent", hire="blacksmith", pos=(6.2, 1.7)),
    "hands":   dict(name="Hands Tent", hire="claygolem", pos=(8.3, 4.0)),
    "fortune": dict(name="Fortune Tent", hire="taxman", pos=(1.9, 6.1)),
    "combat":  dict(name="Combat Tent", hire="archer", pos=(4.6, 8.2)),
}
HIRES = {
    "hero": dict(title="Hero Miner", tent="crew",
                 blurb="A legend of the deep: digs like four miners, and drops everything to rescue anyone nearby a "
                       "monster gets hold of - with blows heavy enough to crack a golem's armour.",
                 does=["Digs as hard as four miners", "Charges to free crew grabbed nearby",
                       "No monster can get a grip on them"]),
    "blacksmith": dict(title="Goblin Blacksmith", tent="tools",
                       blurb="Trots from digger to digger with a hammer, a portable anvil and a pouch of blasting "
                             "powder, reforging picks on the spot. A reforged pick goes off with every blow.",
                       does=["Reforges one digger's pick at a time", "Every hit blasts the 3x3 round it for 40s",
                             "...and cracks the blocks underneath", "Bigger blasts as the goblin levels up"]),
    "taxman": dict(title="Tax Collector", tent="fortune",
                   blurb="Does the rounds of the dig with a ledger, walking from one crew member to the next and "
                         "collecting the Crown's dues - which, somehow, end up with you.",
                   does=["Each crew member pays a few blocks' worth", "Dues keep step with the depth",
                         "About a fifth on top of your income", "More as he levels up"]),
    "claygolem": dict(title="Clay Golem", tent="hands",
                      blurb="A lumbering lump of river clay with fists like anvils. Mitts watches your every click, "
                            "and when you've clicked enough, leaps to where you're clicking and slams the ground like "
                            "a fully charged Charged Slam - no upgrade needed.",
                      does=[f"Leaps in and slams every {MITTS_CLICKS} of your clicks",
                            "...right behind your Charged Slams, too",
                            "...or now and then on his own, if you're not clicking", "Flattens the block he lands on",
                            "...and cracks the eight round it", "Harder as he levels up, and with your slam upgrades",
                            "Knocks back monsters caught in it"]),
    "archer": dict(title="Archer", tent="combat",
                   blurb="Keeps the crew covered from a distance, loosing arrows at whatever's grabbing someone "
                         "first, then the nearest monster.",
                   does=["Two arrows a second", "Each hits like one of your clicks on a monster",
                         "Grows with your Combat upgrades", "Up to twice as hard as they level up"]),
}
CAMP_ROLES = tuple(HIRES)   # (their roles in the crew are their keys)

# Once a tent's hire has moved in, it branches out: things of theirs that can be taken on a visit instead of a new
# hire (one pick per visit, whichever it is), each with a quirk of its own for every expedition after.
# pos: where it sits on the camp board, beside its tent (grid units)
ITEMS = {
    "chompers": dict(name="Friendly Mimic", tent="fortune", pos=(1.35, 7.45),
                     blurb="It looks like a treasure chest. It followed the Tax Collector home one night, and it's been "
                           "fed ever since. Chompers comes down every shaft with you - and it has expensive tastes.",
                     does=[f"Every {CHOMP_EVERY:.0f}s it hops to the richest block in the layer...", "...and gobbles it whole",
                           "Coughs up twice what the block was worth", "Won't touch plain rock if there's ore about"]),
    "ledger": dict(name="Crooked Ledger", tent="fortune", pos=(3.4, 5.15),
                   blurb="The Tax Collector's private books: two columns, neither of them honest. Now and then an "
                         "upgrade you buy just never makes it onto the page.",
                   does=["1 in 6 upgrades you buy turn out free", "...the gold comes straight back to you",
                         "Nobody asks where it went"]),
    "dummy": dict(name="Target Dummy", tent="combat", pos=(2.3, 9.45),
                  blurb="Straw, sackcloth and a painted target - and a fair bit of blasting powder in the stuffing. "
                        "Wren plants one now and then, and monsters can't leave it alone.",
                  does=["Wren plants a dummy every 20s", "Monsters close by go for it, not the crew",
                        "It blows up when one grabs it...", "...hurting them, and breaking up the rock beneath"]),
    "kiln": dict(name="Kiln", tent="hands", pos=(6.95, 4.95),
                 blurb="A squat brick kiln, roaring day and night. Mitts sat in it for a week and came out glazed, "
                       "hard as a bell - and in a mood to shove.",
                 does=["No monster can get a grip on Mitts", "His landings shove monsters back...",
                       "...and break the grip of any that had hold of the crew"]),
    "claypit": dict(name="Clay Pit", tent="hands", pos=(8.5, 5.45),
                    blurb="A bubbling pit of wet river clay. Every time Mitts slams, a little of it comes along for "
                          "the ride - and gets up and starts digging.",
                    does=["Every slam throws up a mudling (two at most)", "Mudlings dig at the nearest block...",
                          "...hard, for about 10 seconds", "Then they crumble back into mud"]),
    "brazier": dict(name="Fire Arrows", tent="combat", pos=(6.2, 7.3),
                    blurb="A brazier by the tent and a bundle of pitch-soaked arrows. Wren lights every few before "
                          "she looses them.",
                    does=["Every 4th arrow is a fire arrow", "It bursts where it lands...",
                          "...hitting the monsters round its target too"]),
}


def open_items(camp, items):
    """Items you could take now: their tent's hire is in, and they aren't yours yet."""
    return [k for k, it in ITEMS.items() if TENTS[it["tent"]]["hire"] in camp and k not in items]


def hireable(camp):
    """Hires not yet taken on, in tent order."""
    return [t["hire"] for t in TENTS.values() if t["hire"] and t["hire"] not in camp]
