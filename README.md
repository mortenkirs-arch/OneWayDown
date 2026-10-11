# One Way Down

An isometric incremental mining game built with pygame (pygame-ce).

Your miners dig down through a 10x10 board, layer by layer. Break blocks for gold,
spend it on a star map of upgrades in five branches (Crew, Tools, Hands, Fortune and Combat),
whose paths cross where the branches meet, and go deeper for richer ore. Clearing a layer pays a
bonus of a quarter of everything it held, doubled on every 5th metre. Prices climb steeply the
more you own, so pick what to push, and most upgrades only unlock once you've dug deep enough -
the HUD shows the next depth milestone.

From depth 1, enemies invade in waves and go after your miners - the first one arrives
the moment you get there. Zombies claw out of the ground (depth 1+), bats swoop in (depth 3+),
cave spiders drop from the ceiling (depth 6+), skeletons rattle out of the rock (depth 9+), fast
wisps flicker in (depth 13+) and slow ghosts materialise (depth 19+).
From 45m Burrowers tunnel in unseen - just a mound of earth ploughing along - and burst up under a
miner to grab them (click the mound to dig one out first). Deeper down: Mimics (60m+) sit on a block disguised as a treasure chest and bite whoever digs it - click
a chest that's just sitting there to flush one out; Rock Golems (70m+) wear stone armour that shrugs off
blows until a Charged Slam or a blast cracks it; and Abyssal Shades (85m+) never grab, but drift to where
the crew are thickest and smother them in darkness that slows every swing. Past 70m the waves grow again
(up to 16 monsters by 94m) and more of them are elite.
Past 70m is the endgame: down to 90m the rock gets 15% harder still with every metre (it pays no more for it),
and even a demolitionist's charge or Vein Follower only cracks deep rock rather than shattering it.
Your own hands keep up with the dig: past 50m your Power Gloves toughen with the rock, 12% harder every
metre (and with each expedition), so clicks, slams, dynamite and the Auto-Tapper still bite deep down.
From depth 16, a bat left flying for 3 seconds turns into a vampire, which heals itself
as it drains a miner - so swat bats fast. Ghosts phase out and can't be clicked for a
moment every few seconds, so time your clicks. A grabbed miner is choked until you click the enemy to death;
if you are too slow the miner dies - for good. They're buried in the graveyard and a new
recruit takes their place 15 seconds later. The Combat menu lets your miners fight back
and survive longer.

The Foreman upgrade hires a foreman who walks the site barking orders: the crew swings
faster while they're alive (and faster still near them), but monsters can kill them too.

Every menu has a middle path of its own: Tools (Hot Streak, Vein Follower, Whetstone),
Hands (Combo Clicks, Golden Blocks, Charged Slam - hold the mouse anywhere on the dig - and, at the
top, Phantom Slam, where the Auto-Tapper's ghostly hand charges up and slams on its own), Fortune
(Surveyor's Contract, Buried Treasure, Gold Vault) and Combat (Booby Traps, a Ballista whose bolts pierce
every monster in line, and a Steam
Boiler in the corner that slowly builds up pressure: click it when it's full to scald every regular
monster off the board). Combat's fourth path, Holy Water (zombies and skeletons take more damage), fans
out into specialist counters for the regular monsters (bosses shrug them off): Spirit Lantern (ghosts can't
fade), Torches (spiders are singed as they land), Garlic Garlands (vampires drain less, bats are slower to
turn) and Rock Salt (slimes split into fewer slimelings, which shrivel). One ring further out, the deep's
monsters get theirs: Tremor Bells (Burrowers are flushed out before they reach anyone), Ten-Foot Poles
(Mimics are found out without biting), Acid Edge (any four hits eat through a Rock Golem's armour) and
Flares (shades slow the crew far less, and burn). Past Cleave, Cut Down to Size shrinks a badly hurt elite
back to an ordinary monster - one that still pays an elite's bounty. And very deep, past the Steam Boiler,
Volatile Remains makes every monster burst as it dies, blasting the rock beneath it as hard as it was tough. The Crew menu's middle path hires specialists: drillers (tough, slow, dig almost twice as
fast), guards (patrol and fight monsters on their own) and a demolitionist (charges that level
a whole 3x3 of blocks wherever they are thickest). Next to Combat, a single medic runs to whoever is
hurt - anyone being grabbed first - and patches them up. Now and then a Coffee Break sends a
digger swinging faster for a few seconds. At the top of the Crew branch, Veterans
brings new crew in already trained, and the Graveyard Shift raises fallen crew from the graveyard
as ghosts that dig on at the level they died at, beyond the reach of any monster.

Your crew get better the longer they survive. Every crew member earns experience doing their
job - diggers by breaking blocks, guards (and miners fighting back) by hitting monsters, the
demolitionist through what their charges destroy, the foreman by barking orders, the medic by
healing - and levels
up to a master at level 10, by which point they're twice as good at it (diggers hit twice as
hard, guards strike twice as hard, the demolitionist sets charges twice as often, the foreman's
pep talk is twice as strong). The first levels come within a few minutes; the last take the
best part of an hour. A replacement starts over (from level 1, or higher with Veterans), so keeping
your best crew alive pays.

The Crew page (`C`) tracks every miner's level and experience, blocks mined, gold earned,
monsters fought off, times saved and time on the job, and its Graveyard tab remembers the
fallen. Enemies only act while you are on the dig site.

Waves arrive every 15s at depth 1 - small and frequent, to get things going - easing to every 20s by
depth 10 (and staying at 20s after that, as the waves themselves grow). Each wave tops the board up to
the enemy cap - 1 enemy at depth 1, +1 every 3 levels up to 8 at 21m, then +1 every 6 metres up to 12 -
so enemies you leave alive count toward the next wave. From 25m some arrive as elites: bigger, much
tougher and harder-gripping, worth a bigger bounty. Tuning lives at the top of `dig/enemies.py`.

The mine changes as you go down: every 10 metres you break into a new biome - the Topsoil, the
Stone Caverns, the Crystal Grotto, the Magma Depths, the Ancient Ruins and finally the Abyss - each
with its own rock, backdrop and drifting embers, sparkles or dust (purely cosmetic; see
`dig/biomes.py`).

Every 10th metre is guarded by a boss: the Zombie King (10m), the Broodmother (20m), the
Fanged Behemoth (30m), the Bone Tyrant (40m), the Slime King (50m), the Vampire Lord (60m), the
Archlich (70m), the Burrow Brothers (80m), The Mountain (90m) and The Void Maw (100m), then round again on
every expedition. A boss stalks your
crew, winds up and slams the ground around it (get your miners out of the red), and calls in
minions; ordinary waves pause while it's on the board. Each has a trick of its own:

- **Zombie King** rallies the zombies near him (faster, and they take half damage), so pick
  them off away from him; below half health he rages and slams far more often.
- **Broodmother** lays egg sacs (with a spider to guard them) that hatch into spiders unless you
  break them, and her slams leave webs that slow your crew.
- **Fanged Behemoth** flies: instead of slamming, it marks a crew member's spot and dive-bombs it, and
  its screech stuns the crew nearby for a moment.
- **Bone Tyrant** never stands still for long: after each slam it strides off and hurls a volley of
  bones at your crew, then marches back in. It won't stay down either: its first "death" leaves a
  bone pile you have a few seconds to smash before it pulls itself back together.
- **Slime King** bursts into 8 chunks at half health, and every chunk creeps up and slams on its
  own (smaller slams, but lots of them). Beat every chunk to win. Ordinary slimes (from 34m) split
  in two at half health as well.
- **Vampire Lord** scatters into a swarm of bats (nothing can hit him), flies to a crew member
  and feeds on them to heal - hit him hard to make him let go.
- **Archlich** curses a crew member: click them to lift it before it bursts and hurts everyone
  nearby. Each of his wisps shields him, so kill them first.
- **The Burrow Brothers**, Dig and Delve, share one health bar: one fights above ground while the other
  tunnels towards the crew as a mound of earth, and every few seconds they swap - the mound bursting up
  in a slam (a red ring warns where). Only the one above ground can be hurt; when one falls, the other
  fights on alone.
- **The Mountain** wears four stone plates: blows barely land until heavy hits (Charged Slam, Phantom
  Slam, dynamite, a demolitionist's charge) knock them off one by one. Its stomps heave up new blocks.
- **The Void Maw** only really feels a click on its one open eye (the eyes take turns, blinking shut
  between); everything else glances off. Pools of darkness spread under the crew, slowing every swing
  and eating at whoever stands in them - click a pool to drive it back. Every so often it inhales, dragging
  the crew close by into its maw to bite them hard: strike the open eye mid-breath to choke it.

**Base Camp.** The Void Maw at 100m ends an *expedition*. When it falls, its death-throes bring the shaft
down there and then, however many blocks are left: the floor caves in from its hole outwards, ropes drop to
the crew just ahead of it and every one of them climbs out in their own way (hand over hand, scrambling,
slipping, swinging, spinning, hauled up clinging on, or waving on the rest), while the monsters go down with
the floor. They climb out to Base Camp: a board like a mine layer - grass, dirt paths, a pond with a dock -
with five tents round a campfire, one per upgrade branch. Every tent starts plain white; its first upgrade is a
hire, and you can take on one per visit. A hire is a character who joins every expedition from then on, levels
up with you, and is only ever knocked out (back on their feet after 25 seconds), never killed - and their tent
takes on their colours:
- **Rocco the Hero Miner** (Crew) digs as hard as four miners, drops everything to rescue anyone grabbed nearby
  (heavy blows that crack a golem's armour), and no monster can get a grip on him.
- **Grizzle the Goblin Blacksmith** (Tools) trots from digger to digger reforging their picks on the spot: a
  reforged pick glows and hits 25% harder for 40 seconds (more as the goblin levels up).
- **Mr. Pennyworth the Tax Collector** (Fortune) does the rounds with a ledger, walking from one crew member
  to the next: each pays a few of the layer's average blocks' worth (more the deeper you are), paid to you -
  about a fifth on top of your income all the way down.
- **Wren the Archer** (Combat) shoots whatever's grabbing someone first, then the nearest monster: an arrow a
  second, each taking 10% of its health.
- **Mitts the Clay Golem** (Hands) plods to wherever the blocks are thickest and slams the ground every few
  seconds: a full Charged Slam of its own (your click damage times the slam), with or without the upgrade.

You can look round the camp from the dig at any time (Base Camp, or B) - before you've ever reached it,
it's there too, locked: the cavern in shadow, five silhouettes waiting in its tents.

Then a new expedition starts beneath the camp at 101m with nothing else: no gold, no upgrades, no artifacts,
no crew but the camp's people (the graveyard and your lifetime record survive too). Upgrades unlock again at
their usual depth +100 (Mining Boots at 102m...), the bosses come round again, and blocks and monsters replay
the 1-100m climb exactly as before - no tougher, no richer - so with the camp's people along, each run goes
easier than the last. No monsters come for you until you've hired your first miner. If The Void Maw retreats instead of falling, it rises again 30 seconds later:
there's no way on but through it.

You can't dig past a boss's layer until it falls, but if it isn't beaten within 150 seconds it
retreats and the dig goes on. If your diggers clear the layer first, they don't stand idle: they
keep their distance, darting clear of its slams, and pelt it with rocks. Bosses shrug off most "share of max health" damage, so clicking
them is what counts.

Artifacts are rare finds, each a permanent bonus. Now and then a new layer hides one in a block
with a violet glint (anyone breaking it finds it for you), and each boss drops its own trophy
the first time it's beaten. The Artifacts page (`A`) shows what you've found and what's still
out there; the list lives in `dig/artifacts.py`.

## Run

Requires [uv](https://docs.astral.sh/uv/):

```
uv run main.py
```

## Music

The main menu plays `assets/music/menu.wav` and the game itself (the dig site and its menus) plays
`assets/music/game.wav`, crossfading between them. Both are original seamless loops made by a small
synthesiser in `tools/make_music.py` (no samples or downloads). Regenerate it with `uv run tools/make_music.py`.

Volumes (master, music, sound effects) are set from **Settings** on the main menu and saved to
`settings.json`. Sound effects go through `dig/audio.py`: drop a WAV into `assets/sfx/` (or several takes,
`name_1.wav`, `name_2.wav`... - one is picked at random each time) and call `game.audio.play("name")`;
`SFX_GAIN` there sets how loud each sits. The click when you hit a block or a monster is made by
`tools/make_sfx.py` (`uv run tools/make_sfx.py`).

## Testing

Jump straight to any depth or boss with a fresh test game, set up about how a player would have it by
then (upgrades, crew experience, earlier bosses' trophies, a few artifacts and some gold). Test games
save under `saves/`, so your own `savegame.json` is never touched; a boss guarding that depth rises
straight away.

```
uv run main.py --depth 39            # start at 39m
uv run main.py --boss bonetyrant     # start at a boss (any unambiguous start works: bone, vamp, lich...)
uv run main.py --list                # the bosses and their depths
uv run main.py --boss bat --gold 1e9 # ...with plenty of gold to try upgrades
uv run main.py --save saves/depth_39.json   # carry on a test game later (plays just that file, not the slots)
```

## Controls

| Input | Action |
| --- | --- |
| Left-click a block (top or side) | Mine it yourself |
| Left-click an enemy | Attack it (uses monster damage from the Combat menu) |
| `U` | Open / close the upgrades (pauses the game) |
| `C` | Open / close the Crew page and graveyard (pauses the game) |
| `A` | Open / close the Artifacts page (pauses the game) |
| Drag (either button) / `WASD` / arrows in upgrades | Move about the star map |
| Wheel / `Q` `E` / `+` `-` in upgrades | Zoom in and out (`H` or `Home`: back to the middle) |
| `1`-`5` / `Tab` in upgrades | Fly to a branch |
| Click / right-click / `Enter` in upgrades | Select a star / buy it / buy the selected one |
| `Esc` | Back / main menu |

There are three save slots (`savegame.json`, `savegame_2.json` and `savegame_3.json`). **Continue**
carries on with whichever was played last, **Load Game** picks one, and **New Game** asks which slot
to start in (replacing a save takes a second click). Progress auto-saves every 10 seconds and on exit.

The window opens at the largest of 1600x900, 1440x810 or 1280x720 that fits your screen
(set `ONE_WAY_DOWN_RES=1280x720` to force a size). Depth milestones live in `UNLOCK_DEPTH`
in `dig/upgrades.py`.

## Project layout

```
main.py              entry point
dig/
  config.py          window, grid, colours, save path
  util.py            number formatting, colour shading
  iso.py             isometric projection, cube drawing, hit-testing
  blocks.py          block types and layer generation
  upgrades.py        the upgrade star map's branches and stars, stat formulas and pricing
  effects.py         particles and floating text
  miners.py          miner state: health, grabbed/down, respawn
  enemies.py         enemy types, spawning, hunt/grab AI
  world.py           simulation: mining rules, combat, save data
  render.py          board drawing and block picking
  sprites.py         miner/enemy/gravestone sprites, enemy picking
  ui.py, icons.py    widgets, text helpers, procedural icons
  game.py            window, main loop, save/load, scene switching
  scenes/            one module per screen (menu, play, upgrades, crew)
```

To add a screen, subclass `dig.scenes.base.Scene` and register it in `Game.scenes`.
To add an upgrade, append an entry to `UPGRADES` in `dig/upgrades.py` (its `branch` picks
the sector of the star map, `pos` its angle and ring there) and read its
level via `world.lv("key")` wherever it takes effect.

## License

Copyright (C) 2026 Morten

One Way Down is free software: you can redistribute it and/or modify it under the terms of the
GNU General Public License as published by the Free Software Foundation, either version 3 of the License,
or (at your option) any later version.

It is distributed in the hope that it will be fun, but WITHOUT ANY WARRANTY; without even the implied
warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for
more details.

The full terms are in [COPYING](COPYING). If you distribute a modified version of the game, or anything
built from its code, it has to be under this same license, with its source code.
