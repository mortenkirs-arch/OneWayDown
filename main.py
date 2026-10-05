"""The Only Way Is Down - an isometric incremental mining game.

Run with:  uv run main.py

Testing (a fresh game set up as a player would have it at that depth, saved under saves/ so your own
savegame.json is never touched; a boss guarding that depth rises straight away):
    uv run main.py --depth 39          start at 39m
    uv run main.py --boss bonetyrant   start at a boss (also: zombie, brood, bat, bone, vampire, lich...)
    uv run main.py --list              list the bosses and their depths
    uv run main.py --save saves/depth_39.json   carry on a test game (or use any other save slot)
"""
import argparse
import os
import sys

from dig.config import PROJECT_ROOT, SAVE_PATH


def parse_args():
    parser = argparse.ArgumentParser(description="The Only Way Is Down", epilog="With no options, plays your own save.")
    start = parser.add_mutually_exclusive_group()
    start.add_argument("--depth", type=int, metavar="N", help="start a fresh test game at depth N")
    start.add_argument("--boss", metavar="NAME", help="start a fresh test game at a boss (see --list)")
    start.add_argument("--list", action="store_true", help="list the bosses and their depths, then exit")
    parser.add_argument("--gold", type=float, metavar="G", help="with --depth/--boss: start with this much gold")
    parser.add_argument("--save", metavar="PATH", help="save file to use (test games default to saves/)")
    return parser.parse_args()


def main():
    args = parse_args()
    from dig.enemies import ENEMY_TYPES
    from dig.testsaves import TEST_SAVE_DIR, boss_aliases, boss_depth
    if args.list:
        aliases = boss_aliases()
        for key in dict.fromkeys(aliases.values()):
            names = ", ".join(a for a, k in aliases.items() if k == key)
            print(f"{boss_depth(key):3d}m  {ENEMY_TYPES[key]['name']:14s} --boss {names}")
        return
    depth = args.depth
    if args.boss:
        typed = args.boss.lower().replace(" ", "").replace("-", "").replace("_", "")
        aliases = boss_aliases()
        key = aliases.get(typed)
        if not key:   # or any unambiguous start of a name: brood, vamp, ...
            matches = {k for a, k in aliases.items() if a.startswith(typed)}
            key = matches.pop() if len(matches) == 1 else None
        if not key:
            sys.exit(f"No boss called '{args.boss}'. Try --list.")
        depth = boss_depth(key)
    if depth is not None and depth < 0:
        sys.exit("--depth must be 0 or more")

    from dig.game import Game
    from dig.testsaves import test_world
    if depth is not None:   # a test game: fresh each time, in its own save file
        path = args.save or os.path.join(PROJECT_ROOT, TEST_SAVE_DIR, f"depth_{depth}.json")
        print(f"Test game at {depth}m, saving to {os.path.relpath(path, PROJECT_ROOT)}")
        Game(save_path=path, world=test_world(depth, gold=args.gold)).run()
    else:
        Game(save_path=args.save or SAVE_PATH).run()


if __name__ == "__main__":
    main()
