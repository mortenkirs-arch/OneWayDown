# Keep Digging

An isometric incremental mining game built with pygame (pygame-ce).

Your miners dig down through an 8x8 board, layer by layer. Break blocks for gold,
spend it in a branching upgrade tree, and go deeper for richer ore.

## Run

Requires [uv](https://docs.astral.sh/uv/):

```
uv run main.py
```

## Controls

| Input | Action |
| --- | --- |
| Left-click a block (top or side) | Mine it yourself |
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
  world.py           simulation: miners, mining rules, save data
  render.py          board/miner drawing and block picking
  ui.py, icons.py    widgets, text helpers, procedural icons
  game.py            window, main loop, save/load, scene switching
  scenes/            one module per screen (menu, play, upgrades)
```

To add a screen, subclass `dig.scenes.base.Scene` and register it in `Game.scenes`.
To add an upgrade, append an entry to `UPGRADES` in `dig/upgrades.py` and read its
level via `world.lv("key")` wherever it takes effect.
