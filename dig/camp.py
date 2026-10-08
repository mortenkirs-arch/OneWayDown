"""Base Camp: what survives the end of an expedition.

Beating The Void Maw at the bottom of an expedition (every EXPEDITION_DEPTH metres) brings the shaft down: the
crew scramble up the last rope, the gear is buried, and the artifacts are set into the foundations of a camp at the
bottom. You take on one hire there, then a new expedition starts below it - from scratch, but with the camp's people
for good. The depth keeps counting (101m, 102m...) while blocks and monsters replay the 1-100m curve exactly as
before - no tougher, no richer: with the camp's people along, every run should go easier than the last.

The camp is five tents on a board, one per upgrade branch. A tent's first upgrade is a hire: a permanent character
who digs, fights or earns in every expedition after (see HIRES; the scene is scenes/camp.py).
"""
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
                       blurb="Trots from digger to digger with a hammer and a portable anvil, reforging picks on "
                             "the spot. A reforged pick bites harder for a good while.",
                       does=["Reforges one digger's pick at a time", "Reforged picks hit 25% harder for 40s",
                             "More as the goblin levels up"]),
    "taxman": dict(title="Tax Collector", tent="fortune",
                   blurb="Does the rounds of the dig with a ledger, walking from one crew member to the next and "
                         "collecting the Crown's dues - which, somehow, end up with you.",
                   does=["Each crew member pays a few blocks' worth", "Dues keep step with the depth",
                         "About a fifth on top of your income", "More as he levels up"]),
    "claygolem": dict(title="Clay Golem", tent="hands",
                      blurb="A lumbering lump of river clay with fists like anvils. Mitts plods to wherever the blocks "
                            "are thickest and slams the ground like a fully charged Charged Slam - no upgrade needed.",
                      does=["A full Charged Slam every few seconds", "Grows with your click damage and slam upgrades",
                            "Knocks back monsters caught in it"]),
    "archer": dict(title="Archer", tent="combat",
                   blurb="Keeps the crew covered from a distance, loosing arrows at whatever's grabbing someone "
                         "first, then the nearest monster.",
                   does=["An arrow a second", "Each takes 10% of a monster's health", "Harder as they level up"]),
}
CAMP_ROLES = tuple(HIRES)   # (their roles in the crew are their keys)


def hireable(camp):
    """Hires not yet taken on, in tent order."""
    return [t["hire"] for t in TENTS.values() if t["hire"] and t["hire"] not in camp]
