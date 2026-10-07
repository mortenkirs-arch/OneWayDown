# The Only Way Is Down

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
(Surveyor's Contract, Buried Treasure, Gold Vault) and Combat (Booby Traps, Ballista, and a Steam
Boiler in the corner that slowly builds up pressure: click it when it's full to scald every regular
monster off the board). Combat's fourth path, Holy Water (zombies and skeletons take more damage), fans
out into specialist counters for the regular monsters (bosses shrug them off): Spirit Lantern (ghosts and wisps), Torches
(spiders are singed as they land), Garlic Garlands (vampires drain less, bats are slower to turn) and
Rock Salt (slimes split into fewer slimelings, which shrivel). The Crew menu's middle path hires specialists: drillers (tough, slow, dig almost twice as
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
Fanged Behemoth (30m), the Bone Tyrant (40m), the Slime King (50m), the Vampire Lord (60m) and the
Archlich (70m), then round again, tougher each time. A boss stalks your
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
  nearby (Spirit Lantern weakens the burst). Each of his wisps shields him, so kill them first.

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
(set `THE_ONLY_WAY_IS_DOWN_RES=1280x720` to force a size). Depth milestones live in `UNLOCK_DEPTH`
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
