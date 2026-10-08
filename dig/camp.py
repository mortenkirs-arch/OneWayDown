"""Base Camp: what survives the end of an expedition.

Beating The Void Maw at the bottom of an expedition (every EXPEDITION_DEPTH metres) brings the shaft down: the
crew scramble up the last rope, the gear is buried, and the artifacts are set into the foundations of a camp at the
bottom. You build one thing there, then a new expedition starts below it - from scratch, but with the camp's bonuses
for good. The depth keeps counting (101m, 102m...) while blocks and monsters replay the 1-100m curve, CYCLE_GROWTH
times tougher (and richer) each expedition.

The camp is five core buildings, one per upgrade branch, each with items branching outward from it. Each node is data:
  name, branch, icon   what it's called, which branch's colour, and its picture (an icons.draw_icon kind)
  parent               the node it's built onto (None: a core building, buildable straight away)
  desc                 a line of flavour; bonus: what it does, in words
  effects              {stat: value}, combined with the artifacts' (see artifacts.STAT_KIND)
"""
EXPEDITION_DEPTH = 100   # an expedition ends at this many metres (The Void Maw)
CYCLE_GROWTH = 1.25      # every expedition's blocks and monsters are this much tougher, and pay this much more
COLLAPSE_DELAY = 3.0     # seconds after The Void Maw falls before the shaft comes down

CAMP = {
    # ----- Crew -----------------------------------------------------------------------------------------------
    "bunkhouse": dict(name="Bunkhouse", branch="crew", icon="team", parent=None,
                      desc="Bunks for a standing crew, waiting at the bottom of every new shaft.",
                      bonus="+1 miner every expedition, crew learn 25% faster", effects={"miners": 1, "xp": 1.25}),
    "messhall": dict(name="Mess Hall", branch="crew", icon="mug", parent="bunkhouse",
                     desc="Hot meals and strong coffee before every shift.",
                     bonus="Crew swing 10% faster", effects={"swing": 0.9}),
    "drillyard": dict(name="Drill Yard", branch="crew", icon="chevrons", parent="bunkhouse",
                      desc="Recruits train here before they're sent down.",
                      bonus="New crew start 2 levels up", effects={"start_level": 2}),
    "lodge": dict(name="Lodge", branch="crew", icon="crown", parent="messhall",
                  desc="A proper lodge: word gets round, and the best diggers come looking for work.",
                  bonus="+2 miners every expedition", effects={"miners": 2}),
    "memorial": dict(name="Memorial Wall", branch="crew", icon="grave", parent="drillyard",
                     desc="Every name from the graveyard, carved in stone. The crew dig a little braver for it.",
                     bonus="Crew have 25% more health and heal 50% faster", effects={"miner_hp": 1.25, "regen": 1.5}),
    # ----- Tools ----------------------------------------------------------------------------------------------
    "forge": dict(name="Forge", branch="tools", icon="anvil", parent=None,
                  desc="A camp forge: every pick sent down is a good one.",
                  bonus="Miners hit 30% harder", effects={"miner_dmg": 1.3}),
    "grindstone": dict(name="Grindstone Mill", branch="tools", icon="whetstone", parent="forge",
                       desc="A water-driven wheel that puts a wicked edge on everything.",
                       bonus="+5% miner crit chance", effects={"crit": 0.05}),
    "toolshed": dict(name="Tool Shed", branch="tools", icon="boot", parent="forge",
                     desc="Every tool hung in its place, every boot laced and ready.",
                     bonus="Crew move 30% faster", effects={"walk": 1.3}),
    "masterforge": dict(name="Master Forge", branch="tools", icon="boulder", parent="grindstone",
                        desc="Picks forged in the heat of the deep itself.",
                        bonus="Miners hit 60% harder", effects={"miner_dmg": 1.6}),
    "oreworks": dict(name="Ore Works", branch="tools", icon="gem", parent="toolshed",
                     desc="Prospectors' charts of every seam the camp has ever found.",
                     bonus="Layers hold 30% more ore", effects={"ore": 1.3}),
    # ----- Hands ----------------------------------------------------------------------------------------------
    "traininghall": dict(name="Training Hall", branch="hands", icon="hand", parent=None,
                         desc="Where the boss keeps their arm in between expeditions.",
                         bonus="Your clicks hit blocks 50% harder", effects={"click_dmg": 1.5}),
    "sparring": dict(name="Sparring Ring", branch="hands", icon="fist", parent="traininghall",
                     desc="A ring of rope and sawdust. Monsters hit back; so do you, now.",
                     bonus="Your clicks hit monsters 40% harder", effects={"monster_dmg": 1.4}),
    "glovesmith": dict(name="Glovesmith", branch="hands", icon="touch", parent="traininghall",
                       desc="Gloves stitched to fit, knuckles plated in deep-iron.",
                       bonus="Your clicks hit blocks 50% harder", effects={"click_dmg": 1.5}),
    "strongman": dict(name="Strongman's Bell", branch="hands", icon="slam", parent="sparring",
                      desc="Ring it every morning. The bosses down below can hear it.",
                      bonus="Bosses take 25% more damage", effects={"boss_dmg": 1.25}),
    "champion": dict(name="Champion's Statue", branch="hands", icon="star", parent="glovesmith",
                     desc="Your likeness in stone, fist raised. Something to live up to.",
                     bonus="Your clicks hit blocks twice as hard", effects={"click_dmg": 2.0}),
    # ----- Fortune --------------------------------------------------------------------------------------------
    "countinghouse": dict(name="Counting House", branch="fortune", icon="coin", parent=None,
                          desc="Ledgers, scales and a clerk who never sleeps.",
                          bonus="+20% gold from everything", effects={"gold": 1.2}),
    "strongroom": dict(name="Strongroom", branch="fortune", icon="vault", parent="countinghouse",
                       desc="Something put by for the next expedition, safe from any collapse.",
                       bonus="Each expedition starts with 2,500 gold", effects={"start_gold": 2500}),
    "surveyoffice": dict(name="Survey Office", branch="fortune", icon="scroll", parent="countinghouse",
                         desc="Every layer measured and valued before the first swing.",
                         bonus="Layer-clear bonuses pay 50% more", effects={"clear": 1.5}),
    "treasury": dict(name="Treasury", branch="fortune", icon="coins", parent="strongroom",
                     desc="Gold piled to the rafters, and a guard on the door.",
                     bonus="+30% gold from everything", effects={"gold": 1.3}),
    "tradingpost": dict(name="Trading Post", branch="fortune", icon="bag", parent="surveyoffice",
                        desc="Traders come down the shaft now. They give a fair price - to regulars.",
                        bonus="Upgrades cost 15% less", effects={"cost": 0.85}),
    # ----- Combat ---------------------------------------------------------------------------------------------
    "watchtower": dict(name="Watchtower", branch="combat", icon="lantern", parent=None,
                       desc="A lookout over the camp. Nothing climbs out of the dark unseen.",
                       bonus="Your clicks hit monsters 30% harder", effects={"monster_dmg": 1.3}),
    "infirmary": dict(name="Infirmary", branch="combat", icon="cross", parent="watchtower",
                      desc="Clean bandages and a steady hand.",
                      bonus="Crew have 30% more health and heal 30% faster", effects={"miner_hp": 1.3, "regen": 1.3}),
    "palisade": dict(name="Palisade", branch="combat", icon="spikes", parent="watchtower",
                     desc="Sharpened stakes round the shaft-head. Monsters come in slower, and warier.",
                     bonus="Monsters move 15% slower", effects={"enemy_speed": 0.85}),
    "armoury": dict(name="Armoury", branch="combat", icon="helmet", parent="infirmary",
                    desc="Padded jackets and steel collars. Harder to get a grip on.",
                    bonus="Grabbed crew take 25% less damage", effects={"grab_dmg": 0.75}),
    "warroom": dict(name="War Room", branch="combat", icon="sword", parent="palisade",
                    desc="Maps of every boss's lair, pinned and annotated.",
                    bonus="+30s to beat a boss, and bosses take 20% more damage",
                    effects={"boss_time": 30, "boss_dmg": 1.2}),
}
CORES = [k for k, c in CAMP.items() if c["parent"] is None]


def buildable(built):
    """Camp nodes that can be built next: any core not yet built, or a node on something already built."""
    return [k for k, c in CAMP.items() if k not in built and (c["parent"] is None or c["parent"] in built)]
