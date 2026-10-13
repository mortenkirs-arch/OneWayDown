"""Window, main loop, persistence and scene switching."""
import json
import os
import random
import sys
import time

import pygame

from .biomes import BIOMES, biome_at
from .appicon import set_app_icon
from .audio import Audio
from . import storage, webaudio
from .config import AUDIO_EXT, AUTOSAVE_SECS, FPS, GOLD, H, MUSIC_DIR, PANEL, SAVE_SLOTS, W
from .scenes import AchievementScene, ArtifactScene, CampScene, CrewScene, MenuScene, PlayScene, SettingsScene, SlotScene, UpgradeScene
from .ui import Fonts
from .world import World

MUSIC_FADE_OUT_MS = 700    # changing tracks: the old one fades out over this...
MUSIC_FADE_IN_MS = 1500    # ...then the new one fades in over this


WEB = sys.platform == "emscripten"   # a browser build (pygbag)


def web_log(text):
    """A line in the browser's console (in a pygbag build; elsewhere, just printed)."""
    try:
        import platform
        platform.window.console.log(text)
    except Exception:
        print(text)


class Game:
    def __init__(self, save_path=None, world=None):
        """`save_path`: play just this one save file (a test game, or --save) instead of the save slots.
        `world`: start straight into this one on the dig site (a developer's test game) instead of loading
        the latest save and opening the menu."""
        self.slots = [save_path] if save_path else list(SAVE_SLOTS)
        self.save_path = self.latest_slot() or self.slots[0]   # (Continue: the save played most recently)
        pygame.init()
        if WEB:   # (in a browser the browser itself plays the sound - see webaudio.py - so pygame's mixer isn't needed)
            pygame.mixer.quit()
        pygame.display.set_caption("One Way Down")
        set_app_icon()   # (before the window opens, so the title bar and taskbar both pick it up)
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
            "achievements": AchievementScene(self),
            "settings": SettingsScene(self),
            "slots": SlotScene(self),
            "camp": CampScene(self),
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
        when opened from it), the game theme everywhere in the game - the dig site and its menus alike - and
        the boss theme instead while a boss is on the board (if there is one: assets/music/boss.wav)."""
        if self.scene is self.scenes["menu"] or getattr(self.scene, "return_to", None) == "menu":
            return "menu"
        if self.world and self.world.boss() and os.path.exists(os.path.join(MUSIC_DIR, "boss" + AUDIO_EXT)):
            return "boss"
        return "game"

    def update_music(self):
        """Move to the track the current screen wants: the old one fades out, then the new one fades in.
        Quietly does nothing without an audio device."""
        want = self.wanted_music()
        if want == self.music or not self.audio.ready():
            return
        self.music = want
        if WEB:   # (the browser fades one track into the next itself)
            webaudio.music(os.path.join(MUSIC_DIR, want + AUDIO_EXT), self.audio.level("music"),
                           MUSIC_FADE_OUT_MS, MUSIC_FADE_IN_MS)
            return
        if pygame.mixer.music.get_busy():   # let the old track fade before the new one starts
            pygame.mixer.music.fadeout(MUSIC_FADE_OUT_MS)
            self.music_start_at = time.time() + MUSIC_FADE_OUT_MS / 1000
        else:
            self.music_start_at = 0.0
            self.start_music()

    def start_music(self):
        path = os.path.join(MUSIC_DIR, self.music + AUDIO_EXT)
        try:
            pygame.mixer.music.load(path)
            pygame.mixer.music.set_volume(self.audio.level("music"))
            pygame.mixer.music.play(loops=-1, fade_ms=MUSIC_FADE_IN_MS)   # a seamless loop, repeated for ever
        except pygame.error:   # (missing file, or the device went away)
            self.music = None

    # ----- save slots -----------------------------------------------------
    def latest_slot(self):
        """The save written most recently, or None if there are none yet."""
        saved = [p for p in self.slots if storage.exists(p)]
        return max(saved, key=storage.saved_at) if saved else None

    def open_slots(self, mode):
        """The save slots screen: "load" a save, pick one for a "new" game, or pick the new game's "mode"."""
        self.scenes["slots"].mode = mode
        self.switch("slots")

    def continue_game(self):
        latest = self.latest_slot()
        if latest and (self.world is None or latest != self.save_path):
            self.play_slot(latest)
        elif self.world:
            self.switch("play")

    def play_slot(self, path):
        """Load the save in `path` and carry on with it (saving the game being left first)."""
        self.save()
        self.save_path, self.world = path, None
        self.load()
        if not self.world:
            self.toast = ("That save couldn't be read", 3.0)
            return
        self.bg_key, self.bg_prev, self.bg_fade = biome_at(self.world.depth)["key"], None, 1.0
        self.switch("play")

    def choose_mode(self, path):
        """Before a new game in the save slot `path`: pick Casual or Normal."""
        self.scenes["slots"].pending = path
        self.open_slots("mode")

    def new_game(self, path=None, casual=False):
        """A fresh game in the save slot `path` (replacing what's there; default: the current one), in Casual mode
        (fewer monsters, softer bosses, richer blocks) or Normal."""
        self.save()
        if path:
            self.save_path = path
        self.world = World(casual=casual)
        self.save()
        self.bg_key, self.bg_prev, self.bg_fade = "topsoil", None, 1.0
        self.switch("play")

    def open_crew(self):
        if self.world:
            self.switch("crew")

    def open_camp(self):
        """Base Camp from the dig: a look round between visits (or, before you've ever made camp, a locked teaser)."""
        if self.world:
            self.switch("camp")

    def open_achievements(self):
        if self.world:
            self.switch("achievements")

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
            upgrades.focus_branch("combat")
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
        text = storage.read(self.save_path)
        if text is None:
            return
        try:
            self.world = World.from_dict(json.loads(text))
        except (ValueError, KeyError, TypeError):
            self.world = None

    def save(self):
        if not self.world:
            return
        storage.write(self.save_path, json.dumps(self.world.to_dict()))
        self.last_save = time.time()

    # ----- main loop ------------------------------------------------------
    def run(self):
        while True:
            self.frame()

    async def run_async(self):
        """The main loop in a browser (pygbag): each frame hands control back to the page, or nothing would draw.
        Opened with #debug on the address, slow frames and any error are reported in the browser's console."""
        import asyncio
        debug = "debug" in sys.argv
        while True:
            try:
                started = time.perf_counter()
                self.frame(debug)
                if debug and time.perf_counter() - started > 0.25:
                    web_log(f"slow frame: {time.perf_counter() - started:.2f}s in {type(self.scene).__name__} "
                            f"({self.frame_parts})")
            except Exception:
                import traceback
                web_log(traceback.format_exc())
                raise
            await asyncio.sleep(0)

    def frame(self, timed=False):
        clock = time.perf_counter
        t0 = clock()
        dt = min(0.05, self.clock.tick(FPS) / 1000)
        t1 = clock()
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.quit()
            self.scene.handle(event)
        t2 = clock()
        self.update(dt)
        t3 = clock()
        self.draw()
        t4 = clock()
        pygame.display.flip()
        if timed:
            self.frame_parts = (f"tick {t1 - t0:.2f}, events {t2 - t1:.2f}, update {t3 - t2:.2f}, "
                                f"draw {t4 - t3:.2f}, flip {clock() - t4:.2f}")

    def update(self, dt):
        if self.music_start_at and time.time() >= self.music_start_at:   # the old track has faded: start the new
            self.music_start_at = 0.0
            self.start_music()
        if self.world and self.scene.simulate:
            self.world.update(dt, combat=self.scene.combat)
            for cue in self.world.cues:   # sounds the world asked for: a name, (name, volume), or "-name" to stop
                if isinstance(cue, tuple):
                    self.audio.play(*cue)
                elif cue.startswith("-"):
                    self.audio.stop(cue[1:])
                else:
                    self.audio.play(cue)
            self.world.cues.clear()
            if time.time() - self.last_save > AUTOSAVE_SECS:
                self.save()
        if self.world and self.world.camp_ready and self.scene is self.scenes["play"]:   # the shaft came down
            self.switch("camp")
        self.update_music()   # (a boss arriving or falling mid-game changes the track, not just a new screen)
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
