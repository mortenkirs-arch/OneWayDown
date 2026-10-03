# Keep Digging

An isometric incremental mining game built with pygame (pygame-ce).

Your miners dig down through a 10x10 board, layer by layer. Break blocks for gold,
spend it across five upgrade menus (Crew, Tools, Hands, Fortune and Combat), and go deeper
for richer ore. Clearing a layer pays a bonus of a quarter of everything it held, doubled on
every 5th metre. Prices climb steeply the more you own, so pick what to push, and most upgrades
only unlock once you've dug deep enough - the HUD shows the next depth milestone.

From depth 1, enemies invade in waves and go after your miners - the first one arrives
the moment you get there. Zombies claw out of the ground (depth 1+), bats swoop in (depth 3+), cave spiders drop from the ceiling
(depth 6+), fast wisps flicker in (depth 9+) and slow ghosts materialise (depth 15+).
From depth 12, a bat left flying for 3 seconds turns into a vampire, which heals itself
as it drains a miner - so swat bats fast. Ghosts phase out and can't be clicked for a
moment every few seconds, so time your clicks. A grabbed miner is choked until you click the enemy to death;
if you are too slow the miner dies - for good. They're buried in the graveyard and a new
recruit takes their place 15 seconds later. The Combat menu lets your miners fight back,
survive longer and get replaced sooner.

The Foreman upgrade hires a foreman who walks the site barking orders: the crew swings
faster while they're alive (and faster still near them), but monsters can kill them too.

Every menu has a middle path of its own: Tools (Hot Streak, Vein Follower, Whetstone),
Hands (Combo Clicks, Golden Blocks, Charged Slam - hold the mouse anywhere on the dig), Fortune
(Surveyor's Contract, Buried Treasure, Gold Vault) and Combat (Spirit Lantern, Booby Traps,
Ballista). The Crew menu's middle path hires specialists: drillers (tough, slow, dig almost twice as
fast), guards (patrol and fight monsters on their own) and a demolitionist (plants charges
on the toughest blocks).

Your crew get better the longer they survive. Every crew member earns experience doing their
job - diggers by breaking blocks, guards (and miners fighting back) by hitting monsters, the
demolitionist through what their charges destroy, the foreman by barking orders - and levels
up to a master at level 10, by which point they're twice as good at it (diggers hit twice as
hard, guards strike twice as hard, the demolitionist sets charges twice as often, the foreman's
pep talk is twice as strong). The first levels come within a few minutes; the last take the
best part of an hour. A replacement starts over, so keeping veterans alive pays.

The Crew page (`C`) tracks every miner's level and experience, blocks mined, gold earned,
monsters fought off, times saved and time on the job, and its Graveyard tab remembers the
fallen. Enemies only act while you are on the dig site.

Waves arrive every 35s at depth 1, speeding up steadily to every 20s by depth 10 (and
staying at 20s after that). Each wave tops the board up to the enemy cap - 1 enemy at
depth 1, +1 every 3 levels, up to 8 - so enemies you leave alive count toward the next
wave. Tuning lives at the top of `dig/enemies.py`.

Every 10th metre is guarded by a boss: the Zombie King (10m), the Broodmother (20m), the
Vampire Lord (30m) and the Lich (40m), then round again, tougher each time. A boss stalks your
crew, winds up and slams the ground around it (get your miners out of the red), and calls in
minions; ordinary waves pause while it's on the board. Each has a trick of its own:

- **Zombie King** rallies the zombies near him (faster, and they take half damage), so pick
  them off away from him; below half health he rages and slams far more often.
- **Broodmother** lays egg sacs that hatch into spiders unless you break them, and her slams
  leave webs that slow your crew.
- **Vampire Lord** scatters into a swarm of bats (nothing can hit him), flies to a crew member
  and feeds on them to heal - hit him hard to make him let go.
- **Lich** curses a crew member: click them to lift it before it bursts and hurts everyone
  nearby (Spirit Lantern weakens the burst). Each of his wisps shields him, so kill them first.

You can't dig past a boss's layer until it falls, but if it isn't beaten within 150 seconds it
retreats and the dig goes on. Bosses shrug off most "share of max health" damage, so clicking
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

## Controls

| Input | Action |
| --- | --- |
| Left-click a block (top or side) | Mine it yourself |
| Left-click an enemy | Attack it (uses monster damage from the Combat menu) |
| `U` | Open / close the upgrades (pauses the game) |
| `C` | Open / close the Crew page and graveyard (pauses the game) |
| `A` | Open / close the Artifacts page (pauses the game) |
| `1`-`5` / `Tab` in upgrades | Switch upgrade menu |
| Right-click / `Enter` in upgrades | Buy the selected upgrade |
| `Esc` | Back / main menu |

Progress auto-saves to `savegame.json` every 10 seconds and on exit.

The window opens at the largest of 1600x900, 1440x810 or 1280x720 that fits your screen
(set `KEEP_DIGGING_RES=1280x720` to force a size). Depth milestones live in `UNLOCK_DEPTH`
in `dig/upgrades.py`.

## Project layout

```
main.py              entry point
dig/
  config.py          window, grid, colours, save path
  util.py            number formatting, colour shading
  iso.py             isometric projection, cube drawing, hit-testing
  blocks.py          block types and layer generation
  upgrades.py        the five upgrade menus, stat formulas and pricing
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
the menu, `pos` its spot in that menu's tree) and read its
level via `world.lv("key")` wherever it takes effect.
