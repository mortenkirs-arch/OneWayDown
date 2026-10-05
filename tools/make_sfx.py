"""Regenerate the game's sound effects: a tiny offline synthesiser (no samples, no downloads - all original).

    uv run tools/make_sfx.py

Writes assets/sfx/<name>_<n>.wav: a few slightly different takes of each sound. The game picks one at random
each time it plays (see dig/audio.py), so repeated sounds - like spam-clicking - don't sound machine-gunned.
  click    hitting a block: a crack of noise over a low thump
  hit      hitting a monster: a meaty thwack - a punchy body hit with a slap on top
  spawn    monsters arriving: a quick, rising jolt of rumbling ground
  chest    a treasure chest opening: its lid creaks on a dry hinge, onto a shimmering G-major chord
  jackpot  a golden block's jackpot: three quick rising chimes, D - G - B (always in tune with the music)
  grab     a monster grabbing one of the crew: two quick, small high alarm beeps
  fuse     a lit stick of dynamite: a steady sizzling hiss, as long as the fuse burns
  boom     dynamite going off: a full, round boom over a low thump
  victory  a boss defeated: a deep bell toll answered by bright rising bells (in tune with the music)
  windup   a boss winding up a slam: a low, rising, strained growl, as long as a wind-up
  slam     the slam landing: a deep, heavy thump into the ground with a short rumble
  smash    your Charged Slam: a deep thud and a crunch, then a crater's worth of rubble pattering down
"""
import array
import math
import os
import random
import wave

SR = 44100
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SFX_DIR = os.path.join(ROOT, "assets", "sfx")
PITCHES = (0.94, 0.98, 1.02, 1.06)
# Takes per sound (each given a pitch from PITCHES), and how close to full scale each sound is written. Their
# in-game loudness is set by SFX_GAIN in dig/audio.py.
TAKES = {"click": 4, "hit": 4, "spawn": 3, "chest": 2, "jackpot": 1, "grab": 2, "fuse": 2, "boom": 3, "victory": 1,
         "windup": 2, "slam": 3, "smash": 3}
PEAK = {"click": 0.6, "hit": 0.6, "spawn": 0.95, "chest": 0.9, "jackpot": 0.9, "grab": 0.8, "fuse": 0.7, "boom": 0.95,
        "victory": 0.95, "windup": 0.8, "slam": 0.95, "smash": 0.9}
WINDUP_SECS = 1.3   # (as long as a boss wind-up: BOSS_WINDUP in dig/enemies.py; shorter ones are faded early)
FUSE_SECS = 1.6   # (as long as a fuse burns in the game: FUSE_SECS in dig/dynamite.py)


def lowpass(xs, cutoff):
    a = 1 - math.exp(-2 * math.pi * cutoff / SR)
    y, out = 0.0, []
    for x in xs:
        y += a * (x - y)
        out.append(y)
    return out


def env(t, attack, decay):
    return (min(1.0, t / attack) if attack else 1.0) * math.exp(-t / decay)


def crack_hit(pitch, rng):
    """Clicking a block: a punchy impact - a crack of noise over a low thump."""
    n = int(0.15 * SR)
    crack = lowpass([rng.uniform(-1, 1) for _ in range(n)], 3500)
    out, phase = [], 0.0
    for i in range(n):
        t = i / SR
        phase += (70 + 180 * math.exp(-t / 0.015)) * pitch / SR   # the thump drops in pitch
        out.append(math.sin(2 * math.pi * phase) * env(t, 0.001, 0.05) * 0.85 + crack[i] * 1.6 * env(t, 0, 0.012))
    return out


def thwack(pitch, rng):
    """Clicking a monster: a meaty thwack - a body punch dropping fast in pitch, with a slap on top."""
    n = int(0.14 * SR)
    slap = lowpass([rng.uniform(-1, 1) for _ in range(n)], 2200)
    out, phase = [], 0.0
    for i in range(n):
        t = i / SR
        phase += (130 + 260 * math.exp(-t / 0.012)) * pitch / SR
        out.append(math.sin(2 * math.pi * phase) * env(t, 0.001, 0.035) + slap[i] * 2.0 * env(t, 0, 0.01))
    return out


def ground_jolt(pitch, rng):
    """Monsters arriving: the ground lurches - a short rumble that rises fast and dies away."""
    secs, cutoff, sub, peak_at = 0.6, 330 * pitch, 48 * pitch, 0.25
    n = int(secs * SR)
    noise = lowpass(lowpass([rng.uniform(-1, 1) for _ in range(n)], cutoff), cutoff)
    out = []
    for i in range(n):
        t = i / SR
        q = t / secs
        if q < peak_at:   # a quick rise...
            swell = math.sin(math.pi * q / (2 * peak_at))
        else:             # ...and a slower fall
            swell = math.cos(math.pi / 2 * (q - peak_at) / (1 - peak_at))
        wobble = 1 + 0.35 * math.sin(2 * math.pi * 9 * t)   # the ground shuddering
        out.append((noise[i] * 9 + math.sin(2 * math.pi * sub * t) * 0.45) * swell * wobble)
    fade = int(0.08 * SR)   # ease the very end to silence
    return out[:-fade] + [x * (1 - i / fade) for i, x in enumerate(out[-fade:])]


def midi_hz(n):
    return 440 * 2 ** ((n - 69) / 12)


def bell(f, secs, decay, bright=0.4):
    """A struck bell: the fundamental plus two inharmonic partials that die away faster."""
    def at(t):
        return (math.sin(2 * math.pi * f * t)
                + bright * math.sin(2 * math.pi * f * 2.76 * t) * math.exp(-t / (decay * 0.3))
                + 0.2 * math.sin(2 * math.pi * f * 5.4 * t) * math.exp(-t / (decay * 0.15))) * env(t, 0.002, decay)
    return [at(i / SR) for i in range(int(secs * SR))]


def creak_and_shine(pitch, rng):
    """A treasure chest opening: the lid creaks open on a dry hinge, then a chord shimmers out."""
    out = [0.0] * int(1.8 * SR)
    secs, phase = 0.45 * pitch, 0.0
    creak = []
    for i in range(int(secs * SR)):
        t = i / SR
        phase += (180 + 120 * (t / secs) + 30 * math.sin(2 * math.pi * 17 * t)) / pitch / SR
        grit = 1 if math.sin(2 * math.pi * 55 * t) > 0.2 else 0.3   # the stick-slip of a dry hinge
        creak.append((2 * (phase % 1) - 1) * grit * math.sin(math.pi * t / secs) * 0.35)
    for i, x in enumerate(lowpass(creak, 1500)):
        out[i] += x * 0.9
    for k, note in enumerate((79, 83, 86, 91)):   # G B D G, rolled
        start = int((0.42 + k * 0.03) * SR)
        for i, x in enumerate(bell(midi_hz(note), 1.3, 0.6)):
            if start + i < len(out):
                out[start + i] += x * 0.32
    fade = int(0.08 * SR)
    return out[:-fade] + [x * (1 - i / fade) for i, x in enumerate(out[-fade:])]


def triple_ding(pitch, rng):
    """A golden block's jackpot: three quick rising chimes. Musical, so it ignores `pitch` and stays in key."""
    out = [0.0] * int(1.4 * SR)
    for k, note in enumerate((74, 79, 83)):   # D G B
        start = int(k * 0.09 * SR)
        f = midi_hz(note)
        for i in range(int(1.1 * SR)):
            t = i / SR
            x = (math.sin(2 * math.pi * f * t) * env(t, 0.002, 0.4)
                 + 0.35 * math.sin(2 * math.pi * f * 2.76 * t) * env(t, 0.002, 0.12)
                 + 0.15 * math.sin(2 * math.pi * f * 5.4 * t) * env(t, 0.002, 0.06))
            if start + i < len(out):
                out[start + i] += x * 0.75
    fade = int(0.08 * SR)
    return out[:-fade] + [x * (1 - i / fade) for i, x in enumerate(out[-fade:])]


def alarm_blips(pitch, rng):
    """A monster grabbing one of the crew: two quick, small high beeps."""
    out = [0.0] * int(0.32 * SR)
    for k in range(2):
        start = int(k * 0.12 * SR)
        for i in range(int(0.1 * SR)):
            t = i / SR
            out[start + i] += math.sin(2 * math.pi * 1760 * pitch * t) * env(t, 0.002, 0.03) * 0.6
    return out


def hissing_fuse(pitch, rng):
    """A lit fuse: bright noise with the lows taken out, wavering a little as it sizzles."""
    n = int(FUSE_SECS * SR)
    hiss = lowpass([rng.uniform(-1, 1) for _ in range(n)], 7000 * pitch)
    lows = lowpass(hiss, 2500 * pitch)
    out = []
    for i in range(n):
        t = i / SR
        out.append((hiss[i] - lows[i]) * (0.6 + 0.15 * math.sin(2 * math.pi * 13 * t)) * min(1.0, t / 0.05))
    fade = int(0.05 * SR)
    return out[:-fade] + [x * (1 - i / fade) for i, x in enumerate(out[-fade:])]


def classic_boom(pitch, rng):
    """Dynamite going off: noise through a low-pass that closes as it dies (crack -> rumble), over a thump."""
    secs, decay = 1.2, 0.35
    n = int(secs * SR)
    out, lp, phase = [], 0.0, 0.0
    for i in range(n):
        t = i / SR
        cut = (250 + (5000 - 250) * math.exp(-t / (decay * 0.5))) * pitch
        a = 1 - math.exp(-2 * math.pi * cut / SR)
        lp += a * (rng.uniform(-1, 1) - lp)
        phase += (40 + 90 * math.exp(-t / 0.03)) * pitch / SR   # the low thump
        thump = math.sin(2 * math.pi * phase) * env(t, 0.002, 0.18) if t < 0.6 else 0.0
        out.append(lp * env(t, 0.002, decay) * 3.5 + thump)
    out = [math.tanh(x * 1.1) for x in out]   # a touch of saturation suits a blast
    fade = int(0.15 * SR)
    return out[:-fade] + [x * (1 - i / fade) for i, x in enumerate(out[-fade:])]


def bell_toll_victory(pitch, rng):
    """A boss defeated: a deep G bell tolls, then bright bells ring out above it. Musical, so it ignores
    `pitch` and stays in key."""
    out = [0.0] * int(3.0 * SR)

    def ring(start, note, secs, decay, vol, bright=0.4):
        i0 = int(start * SR)
        for i, x in enumerate(bell(midi_hz(note), secs, decay, bright)):
            if i0 + i < len(out):
                out[i0 + i] += x * vol

    ring(0.0, 43, 2.6, 1.2, 0.9, bright=0.6)   # the low G toll...
    ring(0.0, 55, 2.4, 1.0, 0.5)               # ...an octave above it...
    for k, note in enumerate((79, 83, 86, 91)):   # ...and bright bells answering: G B D G
        ring(0.7 + k * 0.12, note, 1.6, 0.55, 0.3)
    fade = int(0.2 * SR)
    return out[:-fade] + [x * (1 - i / fade) for i, x in enumerate(out[-fade:])]


def strained_growl(pitch, rng):
    """A boss winding up a slam: a low, buzzing growl that rises and swells as it strains."""
    n = int(WINDUP_SECS * SR)
    out, phase = [], 0.0
    for i in range(n):
        t = i / SR
        q = t / WINDUP_SECS
        phase += (55 + 45 * q + 6 * math.sin(2 * math.pi * 21 * t)) * pitch / SR
        out.append((2 * (phase % 1) - 1) * q ** 1.2 * 0.55)
    return lowpass(lowpass(out, 1600), 1200)


def ground_pound(pitch, rng):
    """A boss slam landing: a deep thump into the ground over a short, low rumble."""
    n = int(0.9 * SR)
    rumble = lowpass(lowpass([rng.uniform(-1, 1) for _ in range(n)], 300 * pitch), 300 * pitch)
    out, phase = [], 0.0
    for i in range(n):
        t = i / SR
        phase += (34 + 110 * math.exp(-t / 0.03)) * pitch / SR
        thump = math.sin(2 * math.pi * phase) * env(t, 0.002, 0.16) * 1.1 if t < 0.7 else 0.0
        out.append(thump + rumble[i] * 9 * env(t, 0.003, 0.22))
    out = [math.tanh(x * 1.1) for x in out]
    fade = int(0.15 * SR)
    return out[:-fade] + [x * (1 - i / fade) for i, x in enumerate(out[-fade:])]


def crater(pitch, rng):
    """Your Charged Slam: a deep sub thud and a dry crunch on impact, then loose rubble pattering down."""
    out = [0.0] * int(1.1 * SR)

    def add(start, sig, vol):
        i0 = int(start * SR)
        for i, x in enumerate(sig[:len(out) - i0]):
            out[i0 + i] += x * vol
    phase = 0.0
    for i in range(int(0.7 * SR)):   # the thud: a sine dropping fast from a kick to a low 34Hz
        t = i / SR
        phase += (34 + 120 * math.exp(-t / 0.03)) * pitch / SR
        out[i] += math.sin(2 * math.pi * phase) * env(t, 0.002, 0.18) * 1.2
    crunch = lowpass([rng.uniform(-1, 1) for _ in range(int(0.08 * SR))], 1800 * pitch)
    add(0, [x * env(i / SR, 0, 0.02) for i, x in enumerate(crunch)], 1.4)
    count = 40
    for k in range(count):   # rubble: little grains, bunched up early and thinning out
        t0 = 0.03 + rng.uniform(0, 1.1 - 0.03 - 0.1) * (k / count) ** 0.6
        grain = lowpass([rng.uniform(-1, 1) for _ in range(int(0.015 * SR))], rng.uniform(1000, 3500) * pitch)
        add(t0, [x * env(i / SR, 0, 0.005) for i, x in enumerate(grain)], 1.0 - k / count * 0.7)
    fade = int(0.1 * SR)
    return out[:-fade] + [x * (1 - i / fade) for i, x in enumerate(out[-fade:])]


SOUNDS = {"click": crack_hit, "hit": thwack, "spawn": ground_jolt, "chest": creak_and_shine,
          "jackpot": triple_ding, "grab": alarm_blips, "fuse": hissing_fuse, "boom": classic_boom,
          "victory": bell_toll_victory, "windup": strained_growl, "slam": ground_pound,
          "smash": crater}


def write_wav(path, samples, peak):
    gain = peak / max(1e-6, max(abs(x) for x in samples))
    data = array.array("h", (int(max(-1.0, min(1.0, x * gain)) * 32000) for x in samples))
    with wave.open(path, "wb") as f:
        f.setnchannels(1)
        f.setsampwidth(2)
        f.setframerate(SR)
        f.writeframes(data.tobytes())


if __name__ == "__main__":
    os.makedirs(SFX_DIR, exist_ok=True)
    for name, make in SOUNDS.items():
        takes = TAKES[name]
        for k in range(1, takes + 1):
            pitch = PITCHES[(k - 1) * len(PITCHES) // takes]
            write_wav(os.path.join(SFX_DIR, f"{name}_{k}.wav"), make(pitch, random.Random(k)), PEAK[name])
        print(f"wrote assets/sfx/{name}_1..{takes}.wav")
