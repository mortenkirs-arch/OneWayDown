"""Window, main loop, persistence and scene switching."""
import json
import os
import random
import sys
import time

import pygame

from .biomes import BIOMES, biome_at
from .config import AUTOSAVE_SECS, FPS, GOLD, H, PANEL, SAVE_PATH, W
from .scenes import ArtifactScene, CrewScene, MenuScene, PlayScene, UpgradeScene
from .ui import Fonts
from .world import World


class Game:
    def __init__(self):
        pygame.init()
        pygame.display.set_caption("Keep Digging")
        self.screen = pygame.display.set_mode((W, H))
        self.clock = pygame.time.Clock()
        self.fonts = Fonts()
        self.backgrounds = {b["key"]: self.make_background(*b["bg"]) for b in BIOMES}
        self.bg_key, self.bg_prev, self.bg_fade = "topsoil", None, 1.0   # fading from bg_prev to bg_key
        self.world = None
        self.last_save = time.time()
        self.toast = None              # (text, time_left)
        self.load()
        if self.world:   # open on the saved depth's backdrop, not a fade from the surface
            self.bg_key = biome_at(self.world.depth)["key"]
        self.scenes = {
            "menu": MenuScene(self),
            "play": PlayScene(self),
            "upgrades": UpgradeScene(self),
            "crew": CrewScene(self),
            "artifacts": ArtifactScene(self),
        }
        self.scene = self.scenes["menu"]

    # ----- scene control --------------------------------------------------
    def switch(self, name):
        self.scene = self.scenes[name]
        self.scene.enter()

    def new_game(self):
        self.world = World()
        self.save()
        self.switch("play")

    def open_crew(self):
        if self.world:
            self.switch("crew")

    def open_artifacts(self):
        if self.world:
            self.switch("artifacts")

    def open_upgrades(self, came_from):
        if not self.world:
            self.world = World()
        self.scenes["upgrades"].return_to = came_from
        self.switch("upgrades")

    def to_menu(self):
        self.save()
        self.switch("menu")

    def quit(self):
        self.save()
        pygame.quit()
        sys.exit()

    # ----- persistence ----------------------------------------------------
    def load(self):
        if not os.path.exists(SAVE_PATH):
            return
        try:
            with open(SAVE_PATH) as f:
                data = json.load(f)
            self.world = World.from_dict(data)
        except (OSError, ValueError, KeyError, TypeError):
            self.world = None

    def save(self):
        if not self.world:
            return
        tmp = SAVE_PATH + ".tmp"
        with open(tmp, "w") as f:
            json.dump(self.world.to_dict(), f)
        os.replace(tmp, SAVE_PATH)
        self.last_save = time.time()

    # ----- main loop ------------------------------------------------------
    def run(self):
        while True:
            dt = min(0.05, self.clock.tick(FPS) / 1000)
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.quit()
                self.scene.handle(event)
            self.update(dt)
            self.draw()
            pygame.display.flip()

    def update(self, dt):
        if self.world and self.scene.simulate:
            self.world.update(dt, combat=self.scene.combat)
            if time.time() - self.last_save > AUTOSAVE_SECS:
                self.save()
        self.scene.update(dt)
        if self.toast:
            self.toast = (self.toast[0], self.toast[1] - dt) if self.toast[1] > dt else None
        self.bg_fade = min(1.0, self.bg_fade + dt / 2.5)

    def draw(self):
        key = biome_at(self.world.depth)["key"] if self.world else "topsoil"
        if key != self.bg_key:   # into a new biome: fade the backdrop across
            self.bg_prev, self.bg_key, self.bg_fade = self.bg_key, key, 0.0
        if self.bg_fade < 1.0 and self.bg_prev:
            self.screen.blit(self.backgrounds[self.bg_prev], (0, 0))
            layer = self.backgrounds[self.bg_key]
            layer.set_alpha(int(255 * self.bg_fade))
            self.screen.blit(layer, (0, 0))
            layer.set_alpha(None)
        else:
            self.screen.blit(self.backgrounds[self.bg_key], (0, 0))
        self.scene.draw(self.screen)
        if self.toast:
            img = self.fonts[26].render(self.toast[0], True, GOLD)
            rect = img.get_rect(midbottom=(W // 2, H - 24)).inflate(30, 18)
            pygame.draw.rect(self.screen, PANEL, rect, border_radius=8)
            pygame.draw.rect(self.screen, GOLD, rect, 2, border_radius=8)
            self.screen.blit(img, img.get_rect(center=rect.center))

    def make_background(self, top, bottom):
        bg = pygame.Surface((W, H))
        for y in range(H):
            t = y / H
            bg.fill(tuple(int(a + (b - a) * t) for a, b in zip(top, bottom)), (0, y, W, 1))
        rng = random.Random(7)
        for _ in range(90):
            x, y = rng.randrange(W), rng.randrange(H)
            pygame.draw.circle(bg, tuple(min(255, c + 22) for c in top), (x, y), rng.randint(1, 3))
        return bg
