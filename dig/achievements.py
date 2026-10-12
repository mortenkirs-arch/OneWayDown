"""Achievements: milestones and feats, kept with the save for good (they survive every expedition).

Each achievement is data:
  name, desc      what it's called, and what it takes
  icon            a kind from icons.draw_icon
  tier            "hard" for real challenges, "legendary" for the ones that look impossible (each gets a section,
                  and a colour, of its own: TIERS); standard if left out
  check           (optional) World -> bool, checked about once a second; without one it's earned where it happens,
                  by World.achieve(key) (a jackpot, a boss falling, the end of an expedition...)

World.feats counts the things the record doesn't (jackpots, chests, clicks...), and World.run tracks how this
expedition is going for the ones that take a whole expedition (one miner, no clicks...): see World.expedition_won.
"""
from .artifacts import COMMON, TROPHY_OF
from .camp import CAMP_ROLES, HIRES, ITEMS
from .enemies import BOSSES
from .miners import MAX_LEVEL
from .upgrades import UPGRADES, is_maxed

# Upgrades that put another body on the dig (Protect Mr. President allows Hire Miner up to level 1, and none of these)
HIRE_UPGRADES = ("driller", "guard", "medic", "demolition", "foreman")
SPEED_DEMON_SECS = 30 * 60   # Speed Demon: an expedition beaten in under this long...
BLINK_SECS = 20 * 60         # ...and Blink and You'll Miss It, in under this
QUICK_KILL_SECS = 10.0       # Ten-Second Takedown: a boss beaten within this long of it rising


def _crew(w):
    return [m for m in w.miners if m.role not in CAMP_ROLES]


def _levels(w):
    return sum(w.levels.values())


ACHIEVEMENTS = {
    # ----- digging ---------------------------------------------------------------------------------------------
    "first_block": dict(name="First Swing", icon="pick", desc="Break your first block",
                        check=lambda w: w.lifetime["blocks"] >= 1),
    "blocks_1k": dict(name="Groundbreaker", icon="pick", desc="Break 1,000 blocks",
                      check=lambda w: w.lifetime["blocks"] >= 1_000),
    "blocks_10k": dict(name="Earthmover", icon="pick", desc="Break 10,000 blocks",
                       check=lambda w: w.lifetime["blocks"] >= 10_000),
    "blocks_100k": dict(name="Continental Drift", icon="pick", desc="Break 100,000 blocks",
                        check=lambda w: w.lifetime["blocks"] >= 100_000),
    # ----- depth -----------------------------------------------------------------------------------------------
    "depth_10": dict(name="Below the Grass", icon="map", desc="Dig down to 10m",
                     check=lambda w: w.display_depth >= 10),
    "depth_25": dict(name="Into the Dark", icon="map", desc="Dig down to 25m",
                     check=lambda w: w.display_depth >= 25),
    "depth_50": dict(name="Halfway Down", icon="map", desc="Dig down to 50m",
                     check=lambda w: w.display_depth >= 50),
    "depth_75": dict(name="Feeling the Heat", icon="flame", desc="Dig down to 75m",
                     check=lambda w: w.display_depth >= 75),
    "depth_100": dict(name="Rock Bottom", icon="map", desc="Dig down to 100m",
                      check=lambda w: w.display_depth >= 100),
    "depth_250": dict(name="Deeper Than Deep", icon="map", desc="Dig down to 250m",
                      check=lambda w: w.display_depth >= 250),
    "depth_500": dict(name="Journey to the Centre", icon="sun", desc="Dig down to 500m",
                      check=lambda w: w.display_depth >= 500),
    # ----- gold ------------------------------------------------------------------------------------------------
    "gold_1k": dict(name="Pocket Money", icon="coins", desc="Earn 1,000 gold in all",
                    check=lambda w: w.lifetime["gold"] >= 1e3),
    "gold_1m": dict(name="Millionaire", icon="coins", desc="Earn a million gold in all",
                    check=lambda w: w.lifetime["gold"] >= 1e6),
    "gold_1b": dict(name="Billionaire", icon="coins", desc="Earn a billion gold in all",
                    check=lambda w: w.lifetime["gold"] >= 1e9),
    "gold_1t": dict(name="Trillionaire", icon="vault", desc="Earn a trillion gold in all",
                    check=lambda w: w.lifetime["gold"] >= 1e12),
    "gold_1qa": dict(name="Dragon's Hoard", icon="vault", desc="Earn a quadrillion gold in all",
                     check=lambda w: w.lifetime["gold"] >= 1e15),
    # ----- monsters --------------------------------------------------------------------------------------------
    "monster_1": dict(name="Self Defence", icon="sword", desc="Defeat your first monster",
                      check=lambda w: w.lifetime["monsters"] >= 1),
    "monsters_100": dict(name="Exterminator", icon="sword", desc="Defeat 100 monsters",
                         check=lambda w: w.lifetime["monsters"] >= 100),
    "monsters_1k": dict(name="Monster Mash", icon="axe", desc="Defeat 1,000 monsters",
                        check=lambda w: w.lifetime["monsters"] >= 1_000),
    "monsters_10k": dict(name="Extinction Event", icon="skull", desc="Defeat 10,000 monsters",
                         check=lambda w: w.lifetime["monsters"] >= 10_000),
    "elite": dict(name="Big Game Hunter", icon="target", desc="Defeat an elite monster"),
    "mimic": dict(name="It Was a Trap!", icon="chest", desc="Dig into a chest that turns out to be a Mimic"),
    # ----- bosses ----------------------------------------------------------------------------------------------
    "boss_1": dict(name="Long Live the King", icon="crown", desc="Defeat your first boss",
                   check=lambda w: w.lifetime["bosses"] >= 1),
    "boss_all": dict(name="Boss Rush", icon="trophy", desc=f"Defeat every one of the {len(BOSSES)} bosses",
                     check=lambda w: len(w.feats["bosses"]) >= len(BOSSES)),
    "voidmaw": dict(name="Into the Void", icon="moon", desc="Defeat The Void Maw at the bottom of an expedition"),
    "boss_fled": dict(name="Not Today", icon="clock", desc="Let a boss run out the clock and get away"),
    # ----- the camp --------------------------------------------------------------------------------------------
    "camp": dict(name="Home Sweet Home", icon="flame", desc="Make camp at the bottom of the shaft",
                 check=lambda w: w.camp_ready or w.expedition >= 1),
    "expeditions_5": dict(name="Old Hand", icon="map", desc="Finish 5 expeditions",
                          check=lambda w: w.expedition + (1 if w.camp_ready else 0) >= 5),
    "hire_all": dict(name="Full House", icon="team", desc=f"Fill all {len(HIRES)} tents at Base Camp",
                     check=lambda w: len(w.camp) >= len(HIRES)),
    "item_1": dict(name="Souvenir", icon="scroll", desc="Take one of the camp's items",
                   check=lambda w: len(w.camp_items) >= 1),
    "items_all": dict(name="The Full Camp", icon="chest", tier="legendary",
                      desc=f"Complete Base Camp: fill all {len(HIRES)} tents and take all {len(ITEMS)} of the camp's items",
                      check=lambda w: len(w.camp) >= len(HIRES) and len(w.camp_items) >= len(ITEMS)),
    # ----- the crew --------------------------------------------------------------------------------------------
    "crew_10": dict(name="Small Business", icon="team", desc="Have 10 crew on the dig at once",
                    check=lambda w: len(_crew(w)) >= 10),
    "crew_20": dict(name="Union Rep", icon="team", desc="Have 20 crew on the dig at once",
                    check=lambda w: len(_crew(w)) >= 20),
    "master": dict(name="Master Craftsman", icon="chevrons", desc=f"Get a crew member to level {MAX_LEVEL}",
                   check=lambda w: any(m.level >= MAX_LEVEL for m in w.miners)),
    "fallen_1": dict(name="Rest in Peace", icon="grave", desc="Lose a crew member",
                     check=lambda w: len(w.graveyard) >= 1),
    "fallen_50": dict(name="Gravedigger", icon="grave", desc="Lose 50 crew members, all told",
                      check=lambda w: len(w.graveyard) >= 50),
    # ----- upgrades & artifacts --------------------------------------------------------------------------------
    "upgrades_50": dict(name="Shopaholic", icon="bag", desc="Own 50 upgrade levels at once",
                        check=lambda w: _levels(w) >= 50),
    "maxed": dict(name="Maxed Out", icon="star", desc="Buy an upgrade's last level",
                  check=lambda w: any(u["max"] and is_maxed(u, w.levels) for u in UPGRADES)),
    "all_upgrades": dict(name="Completionist", icon="star", desc="Own every upgrade at once",
                         check=lambda w: all(w.levels[u["key"]] >= 1 for u in UPGRADES)),
    "artifact_1": dict(name="Finders Keepers", icon="gem", desc="Find an artifact",
                       check=lambda w: len(w.artifacts) >= 1),
    "artifacts_common": dict(name="Curator", icon="gem", desc="Find every buried artifact in one expedition",
                             check=lambda w: set(COMMON) <= set(w.artifacts)),
    "trophies": dict(name="Trophy Cabinet", icon="trophy", desc="Hold every boss trophy in one expedition",
                     check=lambda w: set(TROPHY_OF.values()) <= set(w.artifacts)),
    # ----- fortune and your own two hands -------------------------------------------------------------------------
    "jackpot": dict(name="Jackpot!", icon="goldblock", desc="Claim a golden block's jackpot",
                    check=lambda w: w.feats["jackpots"] >= 1),
    "jackpot_50": dict(name="High Roller", icon="goldblock", desc="Claim 50 jackpots",
                       check=lambda w: w.feats["jackpots"] >= 50),
    "chests_25": dict(name="Treasure Hunter", icon="chest", desc="Break open 25 buried treasure chests",
                      check=lambda w: w.feats["chests"] >= 25),
    "ledger": dict(name="Creative Accounting", icon="scroll", desc="Have the Crooked Ledger lose a receipt",
                   check=lambda w: w.feats["ledger"] >= 1),
    "chomps_100": dict(name="Well Fed", icon="chest", desc="Have the Friendly Mimic gobble 100 blocks",
                       check=lambda w: w.feats["chomps"] >= 100),
    "full_slam": dict(name="Hulk Smash", icon="slam", desc="Land a fully charged Charged Slam"),
    "combo_max": dict(name="Combo King", icon="combo", desc="Build a full 20-click combo"),
    "clicks_10k": dict(name="Clickety-Clack", icon="cursor", desc="Click 10,000 times",
                       check=lambda w: w.feats["clicks"] >= 10_000),
    "boiler": dict(name="Letting Off Steam", icon="boiler", desc="Vent the Steam Boiler"),

    # ----- hard and legendary: real challenges, and the ones that look impossible -------------------------------------
    "president": dict(name="Protect Mr. President", icon="miner", tier="legendary",
                      desc="Beat an expedition with a single miner - Hire Miner never past level 1, no other hires - "
                           "and nobody ever falls"),
    "hands_off": dict(name="Look, No Hands", icon="hand", tier="legendary",
                      desc="Beat an expedition without clicking a single block or monster yourself"),
    "no_fortune": dict(name="Money Isn't Everything", icon="coins", tier="hard",
                       desc="Beat an expedition without buying a single Fortune upgrade"),
    "flawless": dict(name="Not One Lost", icon="cross", tier="legendary",
                     desc="Beat an expedition without losing a single crew member"),
    "speed_demon": dict(name="Speed Demon", icon="clock", tier="hard",
                        desc=f"Beat an expedition in under {SPEED_DEMON_SECS // 60} minutes"),
    "blink": dict(name="Blink and You'll Miss It", icon="clock", tier="legendary",
                  desc=f"Beat an expedition in under {BLINK_SECS // 60} minutes"),
    "quick_kill": dict(name="Ten-Second Takedown", icon="bolt", tier="hard",
                       desc=f"Defeat a boss within {QUICK_KILL_SECS:.0f} seconds of it rising"),
    "untouchable": dict(name="Untouchable", icon="shield", tier="hard",
                        desc="Defeat a boss without a single one of your crew taking a scratch"),
    "hold_beer": dict(name="Hold My Beer", icon="mug", tier="hard",
                      desc="Defeat a boss without owning a single Combat upgrade"),
    "lucky": dict(name="Against All Odds", icon="star", tier="hard",
                  desc="Have the Crooked Ledger lose three receipts in a row"),
}
# The tiers, easiest first: how each looks, its heading on the Achievements page, and its banner on the dig
TIERS = {
    "standard": dict(color=(120, 200, 255), heading=None, banner="ACHIEVEMENT UNLOCKED"),
    "hard": dict(color=(245, 120, 90), heading="Hard  -  for those who like a challenge", banner="HARD ACHIEVEMENT!"),
    "legendary": dict(color=(255, 196, 70), heading="Legendary  -  the ones that look impossible",
                      banner="LEGENDARY ACHIEVEMENT!"),
}


def tier(key):
    return ACHIEVEMENTS[key].get("tier", "standard")


BY_TIER = {t: [k for k in ACHIEVEMENTS if tier(k) == t] for t in TIERS}
CHECKED = [k for k, a in ACHIEVEMENTS.items() if "check" in a]


def new_run(clock):
    """How this expedition is going, for the achievements that take a whole one. `clean`: tracked from its very start (an
    expedition already under way in a save from before achievements can't count)."""
    return dict(start=clock, clean=True, one_miner=True, no_deaths=True, no_block_clicks=True,
                no_monster_clicks=True)


def new_feats():
    return dict(jackpots=0, chests=0, ledger=0, ledger_streak=0, chomps=0, clicks=0, bosses=[])
