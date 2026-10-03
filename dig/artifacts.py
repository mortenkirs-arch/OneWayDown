"""Artifacts: rare finds buried in the dig, each a permanent bonus.

Common artifacts turn up in ordinary blocks (a glinting block now and then). Trophies are only ever
dropped by the boss named in `boss` (see BOSSES in enemies.py), the first time it is beaten.

Each artifact is data:
  name, icon, color   how it looks (icon is a kind from icons.draw_icon)
  lore                a line of flavour on the reveal card and the Artifacts page
  bonus               what it does, in words
  effects             {stat: value}; World.art_mult(stat) multiplies "mult" stats together and
                      World.art_add(stat) sums "add" stats (see STAT_KIND)
"""

STAT_KIND = {
    "miners": "add",        # extra diggers
    "crit": "add",          # added to the miners' crit chance
    "miner_dmg": "mult", "swing": "mult", "walk": "mult", "miner_hp": "mult", "regen": "mult",
    "click_dmg": "mult", "monster_dmg": "mult", "gold": "mult", "bounty": "mult", "clear": "mult",
    "ore": "mult", "wave": "mult", "enemy_hp": "mult", "grab_dmg": "mult",
}

ARTIFACTS = {
    # ----- common: found in blocks ------------------------------------------
    "lantern": dict(name="Old Miner's Lantern", icon="lantern", color=(255, 200, 90),
                    lore="Still warm. Someone down here wants company.",
                    bonus="+1 miner joins the crew", effects={"miners": 1}),
    "pickhead": dict(name="Dwarven Pick Head", icon="pick", color=(150, 220, 240),
                     lore="Forged by hands that never saw the sun.",
                     bonus="Miners deal +25% damage", effects={"miner_dmg": 1.25}),
    "hourglass": dict(name="Cracked Hourglass", icon="clock", color=(230, 200, 140),
                      lore="The sand runs a little faster than it should.",
                      bonus="Miners swing 10% faster", effects={"swing": 0.9}),
    "boots": dict(name="Seven-League Boots", icon="boot", color=(180, 130, 90),
                  lore="One size fits all, somehow.",
                  bonus="The crew walks 30% faster", effects={"walk": 1.3}),
    "amulet": dict(name="Bone Amulet", icon="shield", color=(225, 220, 200),
                   lore="It hums when danger is near. It hums a lot.",
                   bonus="Crew have +50% health", effects={"miner_hp": 1.5}),
    "gauntlet": dict(name="Stone Gauntlet", icon="fist", color=(170, 170, 185),
                     lore="Heavy enough to punch through bedrock.",
                     bonus="Your clicks on blocks deal +30% damage", effects={"click_dmg": 1.3}),
    "claw": dict(name="Fossilised Claw", icon="slash", color=(235, 120, 100),
                 lore="Whatever it belonged to, it was bigger than the zombies.",
                 bonus="Your clicks on monsters deal +30% damage", effects={"monster_dmg": 1.3}),
    "compass": dict(name="Prospector's Compass", icon="map", color=(240, 190, 80),
                    lore="The needle points at money, not north.",
                    bonus="Ore is 30% more common in new layers", effects={"ore": 1.3}),
    "horseshoe": dict(name="Lucky Horseshoe", icon="star", color=(255, 230, 120),
                      lore="Nailed above a door that no longer exists.",
                      bonus="Miners have +5% crit chance", effects={"crit": 0.05}),
    "goblincrown": dict(name="Goblin Crown", icon="crown", color=(200, 220, 90),
                        lore="Tiny, tarnished and very pleased with itself.",
                        bonus="Monster bounties x2", effects={"bounty": 2.0}),
    "heart": dict(name="Heart of the Mountain", icon="gem", color=(240, 90, 120),
                  lore="It beats once a minute, deep and slow.",
                  bonus="Layer clear bonuses x2", effects={"clear": 2.0}),
    "idol": dict(name="Cursed Idol", icon="skull", color=(170, 120, 230),
                 lore="It promised riches. It didn't mention the company.",
                 bonus="+50% gold from everything, but waves come 25% sooner",
                 effects={"gold": 1.5, "wave": 0.75}),

    # ----- trophies: dropped by bosses ------------------------------------
    "kingcrown": dict(name="Zombie King's Crown", icon="crown", color=(255, 205, 70), boss="zombieking",
                      lore="Heavy is the head. Heavier still, the rest of him.",
                      bonus="Monsters have 15% less health", effects={"enemy_hp": 0.85}),
    "broodsilk": dict(name="Broodmother's Silk", icon="vein", color=(220, 220, 235), boss="broodmother",
                      lore="Stronger than steel, and only slightly sticky.",
                      bonus="Grabbed crew take 30% less damage", effects={"grab_dmg": 0.7}),
    "vampfang": dict(name="Vampire Lord's Fang", icon="burst", color=(200, 40, 60), boss="vampirelord",
                     lore="It still thirsts. Your crew no longer does.",
                     bonus="Crew heal twice as fast", effects={"regen": 2.0}),
    "phylactery": dict(name="Lich's Phylactery", icon="spiritlamp", color=(150, 210, 255), boss="lich",
                       lore="A soul in a jar, bartering for its freedom in gold.",
                       bonus="+25% gold from everything", effects={"gold": 1.25}),
}
COMMON = [k for k, a in ARTIFACTS.items() if "boss" not in a]
TROPHY_OF = {a["boss"]: k for k, a in ARTIFACTS.items() if "boss" in a}

ARTIFACT_MIN_DEPTH = 3     # no artifacts in the first few metres
ARTIFACT_CHANCE = 0.12     # chance a new layer hides one (while undiscovered common artifacts remain)
REVEAL_POP_SECS = 0.25     # the "artifact found" card pops in this fast (it stays until closed)
