"""Window, main loop, persistence and scene switching."""
import json
import os
import random
import sys
import time

import pygame

from .config import (AUTOSAVE_SECS, BG_BOTTOM, BG_TOP, FPS, GOLD, H, OFFLINE_CAP_SECS, PANEL,
                     SAVE_PATH, W)
from .scenes import MenuScene, PlayScene, UpgradeScene
from .ui import Fonts
from .util import fmt
from .world import World


class Game:
    def __init__(self):
        pygame.init()
        pygame.display.set_caption("Keep Digging")
        self.screen = pygame.display.set_mode((W, H))
        self.clock = pygame.time.Clock()
        self.fonts = Fonts()
        self.background = self.make_background()
        self.world = None
        self.last_save = time.time()
        self.toast = None              # (text, time_left)
        self.load()
        self.scenes = {
            "menu": MenuScene(self),
            "play": PlayScene(self),
            "upgrades": UpgradeScene(self),
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
            away = min(OFFLINE_CAP_SECS, max(0, time.time() - data.get("saved_at", time.time())))
            earned = data.get("gps", 0.0) * away * 0.5
            if earned >= 1 and away > 60:
                self.world.gold += earned
                self.toast = (f"While you were away ({int(away // 60)} min) your miners earned ${fmt(earned)}", 6.0)
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
            self.world.update(dt)
            if time.time() - self.last_save > AUTOSAVE_SECS:
                self.save()
        self.scene.update(dt)
        if self.toast:
            self.toast = (self.toast[0], self.toast[1] - dt) if self.toast[1] > dt else None

    def draw(self):
        self.screen.blit(self.background, (0, 0))
        self.scene.draw(self.screen)
        if self.toast:
            img = self.fonts[26].render(self.toast[0], True, GOLD)
            rect = img.get_rect(midbottom=(W // 2, H - 24)).inflate(30, 18)
            pygame.draw.rect(self.screen, PANEL, rect, border_radius=8)
            pygame.draw.rect(self.screen, GOLD, rect, 2, border_radius=8)
            self.screen.blit(img, img.get_rect(center=rect.center))

    def make_background(self):
        bg = pygame.Surface((W, H))
        for y in range(H):
            t = y / H
            bg.fill(tuple(int(a + (b - a) * t) for a, b in zip(BG_TOP, BG_BOTTOM)), (0, y, W, 1))
        rng = random.Random(7)
        for _ in range(90):
            x, y = rng.randrange(W), rng.randrange(H)
            pygame.draw.circle(bg, (50, 42, 66), (x, y), rng.randint(1, 3))
        return bg
