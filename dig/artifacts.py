"""Artifacts: rare finds buried in the dig, each a permanent bonus.

Common artifacts turn up in ordinary blocks (a glinting block now and then). Trophies are only ever
dropped by the boss named in `boss` (see BOSSES in enemies.py), the first time it is beaten. Crew artifacts are
buried like the common ones, but only once the Base Camp hire named in `crew` is with you - one for each, making
them better at what they do.

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
    "ore": "mult", "xp": "mult", "enemy_hp": "mult", "grab_dmg": "mult", "enemy_speed": "mult",
    "slam_dmg": "mult",
    # (one Base Camp hire each:)
    "hero": "mult",         # Rocco digs, and strikes on a rescue, this much harder...
    "hero_reach": "add",    # ...and rescues from this many tiles further
    "rig": "mult",          # Grizzle's rigged picks blast this much harder, and stay rigged this much longer
    "tax": "mult",          # Mr. Pennyworth's dues
    "mitts": "mult",        # Mitts' slams
    "draw": "mult",         # Wren's time between arrows
    "femur": "add",         # Tyrant's Femur: seconds between bones thrown at a monster grabbing a crewmate (0 = none)
    # (Base Camp only:)
    "start_gold": "add",    # gold each expedition starts with
    "start_level": "add",   # levels new crew start up
    "boss_time": "add",     # seconds added to a boss's time limit
    "cost": "mult",         # upgrade prices
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
    "medal": dict(name="Veteran's Medal", icon="helmet", color=(205, 160, 255),
                  lore="Pinned on a miner who came back up. Twice.",
                  bonus="Crew gain experience 50% faster", effects={"xp": 1.5}),

    # ----- crew artifacts: buried once their hire is with you ---------------
    "oathhelm": dict(name="Rocco's Old Helm", icon="helmet", color=(250, 205, 70), crew="hero",
                     lore="Rocco's great-great-grandmother wore it down the very first shaft. It still knows the way.",
                     bonus="Rocco hits 50% harder, reaches further",
                     effects={"hero": 1.5, "hero_reach": 1.0}),
    "blastcap": dict(name="Lucky Blasting Cap", icon="tnt", color=(255, 150, 60), crew="engineer",
                     lore="Never once gone off when it should have. Never once failed to when it shouldn't.",
                     bonus="Grizzle's rigged picks blast 50% harder, and stay rigged 50% longer",
                     effects={"rig": 1.5}),
    "goldquill": dict(name="The Golden Quill", icon="scroll", color=(240, 200, 80), crew="taxman",
                      lore="It writes in gold ink. Mr. Pennyworth has never asked where the ink comes from.",
                      bonus="Mr. Pennyworth collects twice the dues", effects={"tax": 2.0}),
    "riverheart": dict(name="Riverheart Stone", icon="gem", color=(110, 200, 230), crew="claygolem",
                       lore="A smooth blue stone from the riverbed Mitts was dug from. Pressed into his chest, it beats.",
                       bonus="Mitts slams 50% harder", effects={"mitts": 1.5}),
    "bowstring": dict(name="Silver Bowstring", icon="target", color=(200, 225, 245), crew="archer",
                      lore="Spun from moonlight, said the elf who sold it. Wren paid in rabbits.",
                      bonus="Wren shoots arrows 2/3 faster", effects={"draw": 0.6}),

    # ----- trophies: dropped by bosses ------------------------------------
    "kingcrown": dict(name="Zombie King's Crown", icon="crown", color=(255, 205, 70), boss="zombieking",
                      lore="Heavy is the head. Heavier still, the rest of him.",
                      bonus="Monsters have 15% less health", effects={"enemy_hp": 0.85}),
    "broodsilk": dict(name="Broodmother's Silk", icon="vein", color=(220, 220, 235), boss="broodmother",
                      lore="Stronger than steel, and only slightly sticky.",
                      bonus="Grabbed crew take 30% less damage", effects={"grab_dmg": 0.7}),
    "batwing": dict(name="Fanged Behemoth's Wing", icon="wind", color=(150, 120, 190), boss="greatbat",
                    lore="Leathery, enormous, and it still twitches when something moves.",
                    bonus="Monsters move 15% slower", effects={"enemy_speed": 0.85}),
    "femur": dict(name="Tyrant's Femur", icon="bone", color=(235, 228, 205), boss="bonetyrant",
                  lore="Perfectly balanced for throwing. The Tyrant would know.",
                  bonus="Crew hurl a bone at a grabber every 3s",
                  effects={"femur": 3.0}),
    "slimecore": dict(name="Slime King's Core", icon="slam", color=(150, 230, 100), boss="slimeking",
                      lore="Wobbly, warm, and it soaks up a blow like nothing else.",
                      bonus="Crew take 25% less damage from slams", effects={"slam_dmg": 0.75}),
    "vampfang": dict(name="Vampire Lord's Fang", icon="burst", color=(200, 40, 60), boss="vampirelord",
                     lore="It still thirsts. Your crew no longer does.",
                     bonus="Crew heal twice as fast", effects={"regen": 2.0}),
    "phylactery": dict(name="Archlich's Phylactery", icon="spiritlamp", color=(150, 210, 255), boss="lich",
                       lore="A soul in a jar, bartering for its freedom in gold.",
                       bonus="+25% gold from everything", effects={"gold": 1.25}),
    "broclaw": dict(name="Brothers' Lucky Claw", icon="fist", color=(200, 150, 100), boss="burrowbros",
                    lore="Dig and Delve used to fight over it. Now the crew do.",
                      bonus="Monsters pay 50% bigger bounties", effects={"bounty": 1.5}),
    "heartstone": dict(name="Mountain's Heartstone", icon="gem", color=(150, 120, 255), boss="mountain",
                       lore="Still warm, still slow to anger. Your crew stand a little firmer near it.",
                       bonus="Crew have 30% more health", effects={"miner_hp": 1.3}),
    "voidpearl": dict(name="Void Pearl", icon="moon", color=(175, 120, 255), boss="voidmaw",
                      lore="It drinks the light around it - and the crew's weariness with it.",
                      bonus="Miners swing 15% faster", effects={"swing": 0.85}),
}
COMMON = [k for k, a in ARTIFACTS.items() if "boss" not in a and "crew" not in a]
CREW_ARTIFACTS = [k for k, a in ARTIFACTS.items() if "crew" in a]
TROPHY_OF = {a["boss"]: k for k, a in ARTIFACTS.items() if "boss" in a}

ARTIFACT_MIN_DEPTH = 3     # no artifacts in the first few metres
ARTIFACT_CHANCE = 0.12     # chance a new layer hides one (while undiscovered common artifacts remain)
FIRST_ARTIFACT_BY = 7      # the layer at this depth always hides one if none has been found yet
REVEAL_POP_SECS = 0.25     # the "artifact found" card pops in this fast (it stays until closed)
