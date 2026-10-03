# Keep Digging

An isometric incremental mining game built with pygame (pygame-ce).

Your miners dig down through a 10x10 board, layer by layer. Break blocks for gold,
spend it across five upgrade menus (Crew, Tools, Hands, Fortune and Combat), and go deeper
for richer ore. Prices climb steeply the more you own, so pick what to push, and most upgrades
only unlock once you've dug deep enough - the HUD shows the next depth milestone.

From depth 1, enemies invade in waves and go after your miners: zombies claw out of
the ground (depth 1+), bats swoop in (depth 3+), cave spiders drop from the ceiling
(depth 6+), fast wisps flicker in (depth 9+) and slow ghosts materialise (depth 15+).
From depth 12, a bat left flying for 3 seconds turns into a vampire, which heals itself
as it drains a miner - so swat bats fast. Ghosts phase out and can't be clicked for a
moment every few seconds, so time your clicks. A grabbed miner is choked until you click the enemy to death;
if you are too slow the miner dies - for good. They're buried in the graveyard and a new
recruit takes their place 15 seconds later. The Combat menu lets your miners fight back,
survive longer and get replaced sooner.

The Foreman upgrade hires a foreman who walks the site barking orders: the crew swings
faster while they're alive (and faster still near them), but monsters can kill them too.

The Crew page (`C`) tracks every miner's blocks mined, gold earned, monsters fought off,
times saved and time on the job, and its Graveyard tab remembers the fallen. Enemies only act
while you are on the dig site.

Waves arrive every 35s at depth 1, speeding up steadily to every 20s by depth 10 (and
staying at 20s after that). Each wave tops the board up to the enemy cap - 1 enemy at
depth 1, +1 every 3 levels, up to 8 - so enemies you leave alive count toward the next
wave. Tuning lives at the top of `dig/enemies.py`.

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
