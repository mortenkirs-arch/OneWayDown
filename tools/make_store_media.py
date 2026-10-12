"""Store-page images for itch.io: a 630x500 cover (the game's logo) and 1280x720 screenshots of the menu,
the dig early and late, a boss, Base Camp, the upgrades map and the artifacts page.

Run (from the project folder):
    uv run tools/make_store_media.py

Out: dist/store/cover.png and dist/store/screenshot_*.png
"""
import os
import random
import sys

os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"
os.environ["ONE_WAY_DOWN_RES"] = "1280x720"
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

import pygame  # noqa: E402

from dig.camp import HIRES, ITEMS  # noqa: E402
from dig.game import Game  # noqa: E402
from dig.testsaves import test_world  # noqa: E402
from dig.title import Title  # noqa: E402
from dig.upgrades import UPGRADE_BY_KEY, star_pos  # noqa: E402

OUT = os.path.join(ROOT, "dist", "store")
SCRATCH = os.path.join(ROOT, "build", "store_saves")   # (the games set up here save here, never over yours)


def game_with(world, name):
    g = Game(save_path=os.path.join(SCRATCH, f"{name}.json"), world=world)
    g.save = lambda: None
    return g


def play(g, secs, clicks=0.0, seed=1):
    """Run the game a while, clicking blocks now and then (as a player would)."""
    random.seed(seed)
    w, tally = g.world, 0.0
    for _ in range(int(secs / 0.05)):
        tally += clicks * 0.05
        while tally >= 1 and w.current:
            tally -= 1
            w.player_hit(random.choice(list(w.current)), manual=True)
        w.update(0.05)
        g.scene.update(0.05)
        w.reveals.clear()


def shot(g, name):
    g.draw()
    pygame.image.save(g.screen, os.path.join(OUT, f"screenshot_{name}.png"))
    print("  ", name)


def full_camp(world):
    world.camp, world.camp_items, world.expedition = list(HIRES), list(ITEMS), 4
    world.sync_miners()
    return world


def busy_late_game():
    w = full_camp(test_world(72, seed=5))
    g = game_with(w, "late")
    g.switch("play")
    w.enemy_timer = 0.0
    play(g, 14, clicks=5, seed=4)
    return g


def main():
    os.makedirs(OUT, exist_ok=True)
    os.makedirs(SCRATCH, exist_ok=True)
    print("screenshots:")
    g = game_with(None, "menu")   # (no saves here: a fresh menu)
    g.switch("menu")
    for _ in range(10):
        g.scene.update(0.05)
    shot(g, "1_menu")

    w = test_world(9, seed=3)
    g = game_with(w, "early")
    g.switch("play")
    play(g, 8, clicks=4)
    shot(g, "2_dig")

    g = busy_late_game()
    shot(g, "3_late_game")

    w = full_camp(test_world(59, seed=2))
    g = game_with(w, "boss")
    g.switch("play")
    w.depth, w.boss_done = 60, 59
    w.current, w.next = w.new_layer(60), w.new_layer(61)
    w.spawn_boss()
    play(g, 9, clicks=4, seed=2)
    shot(g, "4_boss")

    w = full_camp(test_world(100, seed=1))
    w.camp_ready = True
    g = game_with(w, "camp")
    g.switch("camp")
    play_camp = g.scene
    play_camp.selected = "crew"
    for _ in range(10):
        play_camp.update(0.05)
    shot(g, "5_base_camp")

    w = test_world(55, seed=4)
    g = game_with(w, "upgrades")
    g.open_upgrades("play")
    up = g.scene
    up.select("masterwork")
    up.cam = list(star_pos(UPGRADE_BY_KEY["masterwork"]))
    up.cam[0] -= 140
    for _ in range(30):
        up.update(0.05)
    shot(g, "6_upgrades")

    w = test_world(75, seed=6)
    g = game_with(w, "artifacts")
    g.switch("artifacts")
    shot(g, "7_artifacts")

    print("cover:")
    cover()


def cover():
    """630x500: just the game's logo - "ONE WAY" over the stone DOWN, its skeleton leaning on the N - on the menu's
    starry backdrop. The logo is drawn at the game's size, scaled up to fill the frame, then the whole cover scaled
    down from twice the size (smoother edges)."""
    W2, H2 = 1260, 1000
    g = game_with(None, "cover")
    canvas = pygame.transform.smoothscale(g.backgrounds["topsoil"], (W2, H2))
    logo = pygame.Surface((1280, 520), pygame.SRCALPHA)
    Title(1280).draw(logo, 640, 20, 1.0)
    logo = logo.subsurface(logo.get_bounding_rect()).copy()
    k = 1080 / logo.get_width()
    logo = pygame.transform.smoothscale(logo, (round(logo.get_width() * k), round(logo.get_height() * k)))
    canvas.blit(logo, logo.get_rect(center=(W2 // 2, H2 // 2)))
    pygame.image.save(pygame.transform.smoothscale(canvas, (630, 500)), os.path.join(OUT, "cover.png"))
    print("   cover")

if __name__ == "__main__":
    main()
