"""Sound: the volume settings, background music and sound effects.

Volumes are 0..1 and saved to settings.json (separate from the save game, so they hold for every save):
  master   scales everything
  music    the background music (heard at master x music)
  sfx      sound effects (heard at master x sfx)

Sound effects: drop a WAV into assets/sfx/ and call `audio.play("name")` - it's loaded once, played at the
effects volume, and quietly skipped if the file isn't there or there's no audio device.
"""
import array
import json
import math
import os

import pygame

from .config import PROJECT_ROOT

SETTINGS_PATH = os.path.join(PROJECT_ROOT, "settings.json")
SFX_DIR = os.path.join(PROJECT_ROOT, "assets", "sfx")
DEFAULTS = {"master": 0.8, "music": 0.6, "sfx": 0.8}
CHANNELS = [("master", "Master volume"), ("music", "Music"), ("sfx", "Sound effects")]


class Audio:
    def __init__(self, path=SETTINGS_PATH):
        self.path = path
        self.volume = dict(DEFAULTS)
        self.sounds = {}
        self.load()

    # ----- settings -------------------------------------------------------
    def load(self):
        try:
            with open(self.path) as f:
                saved = json.load(f)
            self.volume.update({k: min(1.0, max(0.0, float(v))) for k, v in saved.items() if k in DEFAULTS})
        except (OSError, ValueError, TypeError, AttributeError):
            pass   # no settings yet (or unreadable): the defaults

    def save(self):
        try:
            with open(self.path, "w") as f:
                json.dump(self.volume, f, indent=2)
        except OSError:
            pass

    def set(self, channel, value):
        self.volume[channel] = min(1.0, max(0.0, value))
        self.apply()

    def level(self, channel):
        """What a channel is actually heard at: its own volume times the master."""
        return self.volume["master"] * self.volume[channel]

    # ----- playback -------------------------------------------------------
    @staticmethod
    def ready():
        return bool(pygame.mixer.get_init())

    def apply(self):
        """Push the current volumes to what's playing."""
        if self.ready():
            pygame.mixer.music.set_volume(self.level("music"))

    def play(self, name):
        """Play sound effect `name` (assets/sfx/<name>.wav) at the effects volume."""
        if not self.ready():
            return
        sound = self.sounds.get(name)
        if sound is None:
            path = os.path.join(SFX_DIR, name + ".wav")
            if name == "tick":
                sound = _tick()
            elif os.path.exists(path):
                try:
                    sound = pygame.mixer.Sound(path)
                except pygame.error:
                    return
            else:
                return
            self.sounds[name] = sound
        sound.set_volume(self.level("sfx"))
        sound.play()


def _tick():
    """A short soft blip, made on the spot: lets the effects slider be heard before there are real effects."""
    rate, size, channels = pygame.mixer.get_init()
    samples = array.array("h")
    n = int(rate * 0.07)
    for i in range(n):
        t = i / rate
        v = math.sin(2 * math.pi * 880 * t) * math.exp(-t / 0.018) * 0.6
        samples.extend([int(v * 32000)] * channels)
    return pygame.mixer.Sound(buffer=samples.tobytes())
