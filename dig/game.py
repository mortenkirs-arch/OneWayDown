"""Window, main loop, persistence and scene switching."""
import json
import os
import random
import sys
import time

import pygame

from .biomes import BIOMES, biome_at
from .audio import Audio
from .config import AUTOSAVE_SECS, FPS, GOLD, H, MUSIC_DIR, PANEL, SAVE_PATH, W
from .scenes import ArtifactScene, CrewScene, MenuScene, PlayScene, SettingsScene, UpgradeScene
from .ui import Fonts
from .world import World

MUSIC_FADE_OUT_MS = 700    # changing tracks: the old one fades out over this...
MUSIC_FADE_IN_MS = 1500    # ...then the new one fades in over this


class Game:
    def __init__(self, save_path=SAVE_PATH, world=None):
        """`save_path`: where to load and save. `world`: start straight into this one on the dig site
        (a developer's test game) instead of loading the save and opening the menu."""
        self.save_path = save_path
        pygame.init()
        pygame.display.set_caption("The Only Way Is Down")
        self.audio = Audio()   # volume settings, music and sound effects
        self.screen = pygame.display.set_mode((W, H))
        self.clock = pygame.time.Clock()
        self.fonts = Fonts()
        self.backgrounds = {b["key"]: self.make_background(*b["bg"]) for b in BIOMES}
        self.bg_key, self.bg_prev, self.bg_fade = "topsoil", None, 1.0   # fading from bg_prev to bg_key
        self.world = None
        self.last_save = time.time()
        self.toast = None              # (text, time_left)
        if world:
            self.world = world
            self.save()
        else:
            self.load()
        if self.world:   # open on the saved depth's backdrop, not a fade from the surface
            self.bg_key = biome_at(self.world.depth)["key"]
        self.scenes = {
            "menu": MenuScene(self),
            "play": PlayScene(self),
            "upgrades": UpgradeScene(self),
            "crew": CrewScene(self),
            "artifacts": ArtifactScene(self),
            "settings": SettingsScene(self),
        }
        self.scene = self.scenes["play" if world else "menu"]
        self.music = None   # which track is playing (None = silence)
        self.music_start_at = 0.0   # when a track waiting for the last one to fade out should start
        self.update_music()

    # ----- scene control --------------------------------------------------
    def switch(self, name):
        self.scene = self.scenes[name]
        self.scene.enter()
        self.update_music()

    # ----- music ----------------------------------------------------------
    def wanted_music(self):
        """The track for the current screen: the menu theme on the main menu (and on the upgrades or settings
        when opened from it), the game theme everywhere in the game - the dig site and its menus alike."""
        if self.scene is self.scenes["menu"] or getattr(self.scene, "return_to", None) == "menu":
            return "menu"
        return "game"

    def update_music(self):
        """Move to the track the current screen wants: the old one fades out, then the new one fades in.
        Quietly does nothing without an audio device."""
        want = self.wanted_music()
        if want == self.music or not pygame.mixer.get_init():
            return
        self.music = want
        if pygame.mixer.music.get_busy():   # let the old track fade before the new one starts
            pygame.mixer.music.fadeout(MUSIC_FADE_OUT_MS)
            self.music_start_at = time.time() + MUSIC_FADE_OUT_MS / 1000
        else:
            self.music_start_at = 0.0
            self.start_music()

    def start_music(self):
        try:
            pygame.mixer.music.load(os.path.join(MUSIC_DIR, self.music + ".wav"))
            pygame.mixer.music.set_volume(self.audio.level("music"))
            pygame.mixer.music.play(loops=-1, fade_ms=MUSIC_FADE_IN_MS)   # a seamless loop, repeated for ever
        except pygame.error:   # (missing file, or the device went away)
            self.music = None

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

    def open_settings(self, came_from="menu"):
        self.scenes["settings"].return_to = came_from
        self.switch("settings")

    def open_upgrades(self, came_from):
        if not self.world:
            self.world = World()
        upgrades = self.scenes["upgrades"]
        upgrades.return_to = came_from
        if came_from == "play" and self.world.combat_tip():   # pointed here by the first boss's tip: Combat
            upgrades.switch_tab("combat")
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
        if not os.path.exists(self.save_path):
            return
        try:
            with open(self.save_path) as f:
                data = json.load(f)
            self.world = World.from_dict(data)
        except (OSError, ValueError, KeyError, TypeError):
            self.world = None

    def save(self):
        if not self.world:
            return
        os.makedirs(os.path.dirname(os.path.abspath(self.save_path)), exist_ok=True)   # (e.g. saves/ for tests)
        tmp = self.save_path + ".tmp"
        with open(tmp, "w") as f:
            json.dump(self.world.to_dict(), f)
        os.replace(tmp, self.save_path)
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
        if self.music_start_at and time.time() >= self.music_start_at:   # the old track has faded: start the new
            self.music_start_at = 0.0
            self.start_music()
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
