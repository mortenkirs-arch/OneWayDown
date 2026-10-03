# Keep Digging

An isometric incremental mining game built with pygame (pygame-ce).

Your miners dig down through an 8x8 board, layer by layer. Break blocks for gold,
spend it in a branching upgrade tree, and go deeper for richer ore.

From depth 1, zombies (and cave spiders from depth 6) crawl out of the rock and go
after your miners. A grabbed miner is choked until you click the enemy to death; if
you are too slow the miner goes down and respawns 15 seconds later. Enemies only act
while you are on the dig site.

## Run

Requires [uv](https://docs.astral.sh/uv/):

```
uv run main.py
```

## Controls

| Input | Action |
| --- | --- |
| Left-click a block (top or side) | Mine it yourself |
| Left-click an enemy | Attack it (uses click damage) |
| `U` | Open / close the upgrade tree |
| Right-click / `Enter` in the tree | Buy the selected upgrade |
| `Esc` | Back / main menu |

Progress auto-saves to `savegame.json` every 10 seconds and on exit.

## Project layout

```
main.py              entry point
dig/
  config.py          window, grid, colours, save path
  util.py            number formatting, colour shading
  iso.py             isometric projection, cube drawing, hit-testing
  blocks.py          block types and layer generation
  upgrades.py        upgrade tree definitions and stat formulas
  effects.py         particles and floating text
  miners.py          miner state: health, grabbed/down, respawn
  enemies.py         enemy types, spawning, hunt/grab AI
  world.py           simulation: mining rules, combat, save data
  render.py          board drawing and block picking
  sprites.py         miner/enemy/gravestone sprites, enemy picking
  ui.py, icons.py    widgets, text helpers, procedural icons
  game.py            window, main loop, save/load, scene switching
  scenes/            one module per screen (menu, play, upgrades)
```

To add a screen, subclass `dig.scenes.base.Scene` and register it in `Game.scenes`.
To add an upgrade, append an entry to `UPGRADES` in `dig/upgrades.py` and read its
level via `world.lv("key")` wherever it takes effect.
