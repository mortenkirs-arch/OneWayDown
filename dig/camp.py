"""Base Camp: what survives the end of an expedition.

Beating The Void Maw at the bottom of an expedition (every EXPEDITION_DEPTH metres) brings the shaft down: the
crew scramble up the last rope, the gear is buried, and the artifacts are set into the foundations of a camp at the
bottom. You take on one hire there, then a new expedition starts below it - from scratch, but with the camp's people
for good. The depth keeps counting (101m, 102m...) while blocks and monsters replay the 1-100m curve exactly as
before - no tougher, no richer: with the camp's people along, every run should go easier than the last.

The camp is five tents on a board, one per upgrade branch. A tent's first upgrade is a hire: a permanent character
who digs, fights or earns in every expedition after (see HIRES; the scene is scenes/camp.py).
"""
from .world_layout import (BANNER_BOOST, BANNER_RADIUS, CHOMP_EVERY, COLLAR_EVERY, DIVINING_CHANCE, FRINGE_POWER,
                           FRINGE_RADIUS, FRINGE_VALUE, HEIRLOOM_DEEP, HEIRLOOM_EVERY, MITTS_CLICKS,
                           BLAST_ARROW_BLOCKS, GLAZE_BONUS, GLAZE_SECS, WHEEL_LIFE, WHEEL_MAX,
                           PUP_EVERY, PUP_PAYOUT, ROUNDING_OFF, TAXES_HURT, TAXES_SHARE)

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
              "hero": "steady", "engineer": "spin", "archer": "swing", "taxman": "hauled", "claygolem": "hauled"}

# The camp's five tents, one per upgrade branch. Each starts as a plain white tent; its first upgrade is a hire: a
# character who joins every expedition from then on, for good (the camp's own people are knocked out, never killed).
# pos: where the tent stands on the camp board (grid units, like a mine layer)
TENTS = {
    "crew":    dict(name="Crew Tent", hire="hero", pos=(2.4, 2.2)),
    "tools":   dict(name="Tools Tent", hire="engineer", pos=(6.2, 1.7)),
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
    "engineer": dict(title="Goblin Engineer", tent="tools",
                     blurb="Trots from digger to digger with a toolbelt, a hammer and a pouch of blasting powder, "
                           "rigging picks on the spot. A rigged pick goes off with every blow.",
                     does=["Rigs one digger's pick at a time", "Every hit blasts the 3x3 round it for 40s",
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
    "divining": dict(name="Divining Rod", tent="crew", pos=(2.6, 3.75),
                     blurb="A forked hazel twig, worn smooth by a hundred expeditions. Rocco swears by it - and it "
                           "twitches like mad whenever there's something old buried close by.",
                     does=[f"Artifacts turn up about {DIVINING_CHANCE / 0.12:.0f}x as often",
                           "Rocco heads straight for one when it does...", "...and digs it out first",
                           "Once you've found them all: ancient hoards instead"]),
    "banner": dict(name="Banner of the Deep", tent="crew", pos=(1.5, 3.3),
                   blurb="Rocco's own standard: deep blue, gold-fringed and older than anyone can remember. Wherever "
                         "he digs, he plants it - and nobody wants to be seen slacking under it.",
                   does=["Rocco plants it where he's digging", f"Crew within {BANNER_RADIUS:g} tiles of it swing "
                         f"{round(100 * BANNER_BOOST)}% faster", "He takes it along as he moves on"]),
    "heirloom": dict(name="Heirloom Pickaxe", tent="crew", pos=(2.6, 3.75), requires="divining",   # (in its stump)
                     blurb="Rocco's grandfather's pick, and his grandmother's before that: a gold head on a handle worn "
                           "black. He keeps it driven into the stump by the rod - and takes it down every shaft.",
                     does=[f"Every {HEIRLOOM_EVERY}th blow of Rocco's splits the rock", f"...the {HEIRLOOM_DEEP} blocks "
                           "in line behind the one he hits take it too", "He still digs out the artifacts first"]),
    "fringe": dict(name="Gold Fringe", tent="crew", pos=(1.5, 3.3), requires="banner",   # (sewn on the banner)
                   blurb="The banner, re-stitched in gold thread, with a pennant flying over it. Nobody slacks under it "
                         "now - and what they dig there seems to be worth more.",
                   does=[f"The banner reaches {FRINGE_RADIUS:g} tiles (not {BANNER_RADIUS:g})",
                         f"Crew under it hit {round(100 * FRINGE_POWER)}% harder...",
                         f"...and the blocks they break pay {round(100 * FRINGE_VALUE)}% more"]),
    "chompers": dict(name="Friendly Mimic", tent="fortune", pos=(1.6, 7.6),
                     blurb="It looks like a treasure chest. It followed the Tax Collector home one night, and it's been "
                           "fed ever since. Chompers comes down every shaft with you - and it has expensive tastes.",
                     does=[f"Every {CHOMP_EVERY:.0f}s it hops to the richest block in the layer...", "...and gobbles it whole",
                           "Coughs up twice what the block was worth", "Won't touch plain rock if there's ore about"]),
    "ledger": dict(name="Crooked Ledger", tent="fortune", pos=(3.7, 6.1),
                   blurb="The Tax Collector's private books: two columns, neither of them honest. Now and then an "
                         "upgrade you buy just never makes it onto the page.",
                   does=["1 in 6 upgrades you buy turn out free", "...the gold comes straight back to you",
                         "Nobody asks where it went"]),
    "pup": dict(name="Mimic Pup", tent="fortune", pos=(1.6, 7.6), requires="chompers",   # (riding on Chompers)
                blurb="Chompers has had a little one. Nobody's sure how. It trots after its parent everywhere, and it's "
                      "already developing expensive tastes of its own.",
                does=[f"Every {PUP_EVERY:.0f}s it gobbles a block too", f"...and coughs up {PUP_PAYOUT:g}x its worth",
                      "Never the one Chompers is after"]),
    "collar": dict(name="Spiked Collar", tent="fortune", pos=(0.6, 6.45), requires="chompers",
                   blurb="A studded leather collar and a bowl with its name on. Chompers has decided the crew are its "
                         "people - and woe betide anything that lays a claw on them.",
                   does=["When a monster grabs someone, Chompers bites it", "...knocking it loose, and hard",
                         "Bats, spiders, wisps and slimelings: swallowed whole, for twice the bounty",
                         f"Once every {COLLAR_EVERY:.0f}s - bosses are too big"]),
    "taxes": dict(name="Death and Taxes", tent="fortune", pos=(3.3, 6.95), requires="ledger",
                  blurb="An iron strongbox and a borrowed scythe. Mr. Pennyworth has noticed that the monsters have "
                        "never paid a penny in tax - and he means to put that right.",
                  does=["On his rounds, he taxes the monsters too", f"Each pays {round(100 * TAXES_SHARE)}% of its "
                        f"bounty", f"...and loses {round(100 * TAXES_HURT)}% of its health in sheer indignation",
                        "Bosses have very good lawyers"]),
    "rounding": dict(name="Rounding Errors", tent="fortune", pos=(3.7, 6.1), requires="ledger",   # (on its desk)
                     blurb="An abacus with a bead that sticks. Mr. Pennyworth rounds every price down - always in your "
                           "favour, and always by rather more than you'd expect.",
                     does=[f"Every upgrade costs {round(100 * ROUNDING_OFF)}% less",
                           "...on top of the Crooked Ledger's free ones"]),
    "dummy": dict(name="Target Dummy", tent="combat", pos=(2.3, 9.45),
                  blurb="Straw, sackcloth and a painted target - and a fair bit of blasting powder in the stuffing. "
                        "Wren plants one now and then, and monsters can't leave it alone.",
                  does=["Wren plants a dummy every 20s", "Monsters close by go for it, not the crew",
                        "It blows up when one grabs it...", "...hurting them, and breaking up the rock beneath"]),
    "rod": dict(name="Lightning Rod", tent="tools", pos=(6.35, 1.7),   # (up on the tent: see scenes/camp.py)
                blurb="A copper spike, a coil of wire and a jar of something that hums. Grizzle swears it's perfectly "
                      "safe. It is not perfectly safe.",
                does=["Grizzle plants a lightning rod every 25s", "For 20s it arcs at whatever's near it...",
                      "...cracking blocks and zapping monsters", "Twice a second, at random"]),
    "toolkit": dict(name="Clockwork Toolkit", tent="tools", pos=(5.85, 3.0),
                    blurb="Spring-loaded spanners, a self-winding hammer and a lot of tiny gears. Every pick Grizzle "
                          "rigs now gets wound up while he's at it.",
                    does=["Rigged picks swing 40% faster", "...as long as they stay rigged",
                          "Opens the way to the Pocket Watch and Clockwork Gears"]),
    "watch": dict(name="Pocket Watch", tent="tools", pos=(7.05, 1.7), requires="toolkit",   # (hung off it)
                  blurb="A brass pocket watch that runs a little too well. Every so often, it simply stops time - for "
                        "everyone but your crew.",
                  does=["Every 30s, time stops for 3s", "Every monster freezes - bosses too",
                        "Your crew and your clicks keep going"]),
    "gears": dict(name="Clockwork Gears", tent="tools", pos=(5.85, 3.0), requires="toolkit",   # (fitted to it)
                  blurb="Grizzle has been fitting gears to everything that ticks, and a few things that didn't. "
                        "Now it all comes round sooner.",
                  does=["Every timed thing comes round 25% sooner:", "Dynamite, Phantom Slam, Golden Blocks,",
                        "Coffee Breaks, the Ballista, charges -", "Mitts, Wren, Chompers, the rods..."]),
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
    "glaze": dict(name="Glazed Fists", tent="hands", pos=(6.95, 4.95), requires="kiln",   # (by the kiln)
                  blurb="A second firing, in a glaze of deep blue. Mitts' fists came out of the kiln shining like "
                        "bells - and whatever they land on comes away glazed too, brittle as pottery.",
                  does=["Mitts' slams glaze the blocks they land on", f"...for {GLAZE_SECS:.0f}s, the crew hitting "
                        f"them {round(100 * GLAZE_BONUS)}% harder", "The nine blocks round where he lands, all of them"]),
    "wheel": dict(name="Potter's Wheel", tent="hands", pos=(8.5, 5.45), requires="claypit",   # (by the pit)
                  blurb="A kick-wheel by the clay pit. Mitts has taken to throwing his mudlings properly: helmets, "
                        "arms, the lot. Proper little clay soldiers - and they hold together far longer.",
                  does=[f"Mudlings last {WHEEL_LIFE:g}x as long", f"Up to {WHEEL_MAX} of them at once (not 2)",
                        "...in little clay helmets"]),
    "brazier": dict(name="Fire Arrows", tent="combat", pos=(5.6, 7.68),   # (by the tent's door)
                    blurb="A brazier by the tent and a bundle of pitch-soaked arrows. Wren lights every few before "
                          "she looses them.",
                    does=["Every 4th arrow is a fire arrow", "It bursts where it lands...",
                          "...hitting the monsters round its target too"]),
    "explosive": dict(name="Explosive Arrows", tent="combat", pos=(5.6, 7.68), requires="brazier",   # (by the brazier)
                      blurb="A keg of black powder by the brazier, and a clay bulb of it tied behind every fire arrow's "
                            "head. Wren says it's for the big ones. Wren says that about everything.",
                      does=["Her fire arrows blow up where they land", "Every monster round the target takes the "
                            "full hit", f"...and the blocks round it take {BLAST_ARROW_BLOCKS:g} of your clicks",
                            "Hard enough to crack a golem's armour"]),
}


def open_items(camp, items):
    """Items you could take now: their tent's hire is in, anything they build on is yours, and they aren't yet."""
    return [k for k, it in ITEMS.items() if TENTS[it["tent"]]["hire"] in camp and k not in items
            and it.get("requires", k) in list(items) + [k]]


def hireable(camp):
    """Hires not yet taken on, in tent order."""
    return [t["hire"] for t in TENTS.values() if t["hire"] and t["hire"] not in camp]
