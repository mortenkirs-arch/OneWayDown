"""Sound: the volume settings, background music and sound effects.

Volumes are 0..1 and saved to settings.json (separate from the save game, so they hold for every save):
  master   scales everything
  music    the background music (heard at master x music)
  sfx      sound effects (heard at master x sfx)

Sound effects: drop a WAV into assets/sfx/ (or several takes, name_1.wav, name_2.wav, ...) and call
`audio.play("name")` - it's loaded once, played at the effects volume (times its SFX_GAIN), a random take
each time, and quietly skipped if the file isn't there or there's no audio device.
"""
import json
import os
import sys
import time
import random

import pygame

from . import storage, webaudio
from .config import AUDIO_EXT, DATA_DIR, RESOURCE_ROOT

SETTINGS_PATH = os.path.join(DATA_DIR, "settings.json")
SFX_DIR = os.path.join(RESOURCE_ROOT, "assets", "sfx")
DEFAULTS = {"master": 0.8, "music": 0.6, "sfx": 0.8}
CHANNELS = [("master", "Master volume"), ("music", "Music"), ("sfx", "Sound effects")]
# How loud each effect sits under the effects volume. Kept low for frequent sounds, so spam-clicking doesn't
# drown out the music. (Sounds themselves are made by tools/make_sfx.py.)
SFX_GAIN = {
    "click": 0.35, "hit": 0.35,   # your clicks on blocks / monsters: frequent, so soft
    "spawn": 1.0,                 # monsters arriving: loud on purpose - a wave is coming
    "grab": 0.6,                  # a crew member grabbed: an alert, but frequent deep down
    "chest": 0.4, "jackpot": 0.4,  # rare rewards: noticeable, not jarring
    "fuse": 0.35, "boom": 0.9,     # dynamite (a demolitionist's charges go off at CHARGE_BOOM of this)
    "victory": 0.9,               # a boss defeated
    "smash": 0.8,                 # your Charged Slam
    "windup": 0.6, "slam": 1.0,   # a boss slam: the growl while it winds up, then the impact
}


WEB = sys.platform == "emscripten"
WEB_SOUND_GAP = 0.05   # in a browser, the same sound starts at most this often (seconds)

class Audio:
    def __init__(self, path=SETTINGS_PATH):
        self.path = path
        self.volume = dict(DEFAULTS)
        self.sounds = {}
        self.playing = {}   # the channel each sound last played on (so it can be cut short; in a browser: its id)
        self.last_played = {}   # (in a browser: when each sound last started)
        self.next_id = 0
        self.load()
        if WEB:   # (decoded up front, so no sound waits for it the first time)
            for name in sorted(os.listdir(SFX_DIR)) if os.path.isdir(SFX_DIR) else ():
                webaudio.preload(os.path.join(SFX_DIR, name))

    # ----- settings -------------------------------------------------------
    def load(self):
        try:
            saved = json.loads(storage.read(self.path) or "{}")
            self.volume.update({k: min(1.0, max(0.0, float(v))) for k, v in saved.items() if k in DEFAULTS})
        except (ValueError, TypeError, AttributeError):
            pass   # no settings yet (or unreadable): the defaults

    def save(self):
        storage.write(self.path, json.dumps(self.volume, indent=2))

    def set(self, channel, value):
        self.volume[channel] = min(1.0, max(0.0, value))
        self.apply()

    def level(self, channel):
        """What a channel is actually heard at: its own volume times the master."""
        return self.volume["master"] * self.volume[channel]

    # ----- playback -------------------------------------------------------
    @staticmethod
    def ready():
        return webaudio.available() if WEB else bool(pygame.mixer.get_init())

    def apply(self):
        """Push the current volumes to what's playing."""
        if WEB:
            webaudio.music_volume(self.level("music"))
        elif self.ready():
            pygame.mixer.music.set_volume(self.level("music"))

    def play(self, name, vol=1.0):
        """Play sound effect `name` at the effects volume: assets/sfx/<name>.wav, or - if there are several
        takes, <name>_1.wav, <name>_2.wav, ... - one of them at random, so repeats don't sound identical.
        `vol` scales it further (e.g. a smaller version of a sound)."""
        if not self.ready():
            return
        takes = self.sounds.get(name)
        if takes is None:
            takes = self.sounds[name] = self._load(name)
        if not takes:
            return
        if WEB:   # (in a browser, a burst of the same sound - a dozen picks at once - just muddies the mix)
            now = time.time()
            if now - self.last_played.get(name, 0.0) < WEB_SOUND_GAP:
                return
            self.last_played[name] = now
        volume = min(1.0, self.level("sfx") * SFX_GAIN.get(name, 1.0) * vol)
        if WEB:   # (the browser plays it: see webaudio.py)
            self.next_id += 1
            webaudio.play(self.next_id, random.choice(takes), volume)
            self.playing[name] = self.next_id
            return
        channel = random.choice(takes).play()
        if channel is not None:   # (the volume on its channel: setting it on the sound would jump any copy still playing)
            channel.set_volume(volume)
        self.playing[name] = channel

    def stop(self, name, fade_ms=80):
        """Cut `name` short with a quick fade, if it's still playing (e.g. a wind-up that ended early)."""
        channel = self.playing.pop(name, None)
        if WEB:
            if channel is not None:
                webaudio.stop(channel, fade_ms)
        elif channel is not None and channel.get_busy():
            channel.fadeout(fade_ms)

    @staticmethod
    def _load(name):
        paths = [os.path.join(SFX_DIR, name + AUDIO_EXT)]
        k = 1
        while os.path.exists(os.path.join(SFX_DIR, f"{name}_{k}{AUDIO_EXT}")):
            paths.append(os.path.join(SFX_DIR, f"{name}_{k}{AUDIO_EXT}"))
            k += 1
        if WEB:   # (in a browser a take is just its path: the browser plays it)
            return [path for path in paths if os.path.exists(path)]
        takes = []
        for path in paths:
            if os.path.exists(path):
                try:
                    takes.append(pygame.mixer.Sound(path))
                except pygame.error:
                    pass
        return takes

