"""Regenerate the game's music: a tiny offline synthesiser (no samples, no downloads - the music is original).

    uv run tools/make_music.py

Writes, as seamless loops:
  assets/music/menu.wav   the main-menu theme: soft pads, a sine bass and a slow plucked arpeggio over
                          Am - F - C - G (the opening of the "Lantern Light" sketch)
  assets/music/game.wav   the in-game theme: a quick plucked arpeggio and a short sine bass over
                          Em - C - Am - B, a little tense (the "D3, E minor tense" sketch)
"""
import array
import math
import os
import wave

SR = 22050
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MUSIC_DIR = os.path.join(ROOT, "assets", "music")


def midi_hz(n):
    return 440.0 * 2 ** ((n - 69) / 12)


def osc(kind, phase):
    p = phase % 1.0
    if kind == "tri":
        return 4 * p - 1 if p < 0.5 else 3 - 4 * p
    return math.sin(2 * math.pi * p)


def chord(root, quality=""):
    """A triad: major, or minor with quality "m"."""
    return [root, root + (3 if quality == "m" else 4), root + 7]


class Mix:
    """A mono buffer that notes are added into."""

    def __init__(self, secs):
        self.n = int(secs * SR)
        self.buf = [0.0] * self.n

    def note(self, start, dur, midi, kind="tri", vol=0.2, attack=0.01, decay=0.1, sustain=0.7, release=0.08,
             pluck=False, detune=0.0):
        """One note (start and dur in seconds), with an ADSR envelope - or, plucked, just a decay."""
        f = midi_hz(midi)
        i0 = int(start * SR)
        for k in range(int((dur + release) * SR)):
            i = i0 + k
            if i >= self.n:
                break
            t = k / SR
            if pluck:
                env = math.exp(-t / max(0.02, decay)) * min(1.0, t / max(attack, 1e-4))
            elif t < attack:
                env = t / attack
            elif t < attack + decay:
                env = 1 - (1 - sustain) * (t - attack) / decay
            elif t < dur:
                env = sustain
            else:
                env = sustain * max(0.0, 1 - (t - dur) / release)
            s = osc(kind, f * t)
            if detune:   # a second, slightly detuned voice: a fuller, chorused sound
                s = 0.5 * (s + osc(kind, f * (1 + detune) * t))
            self.buf[i] += s * env * vol

    def echo(self, delay, feedback, mix):
        d = int(delay * SR)
        wet = self.buf[:]
        for i in range(d, self.n):
            wet[i] += wet[i - d] * feedback
        self.buf = [a * (1 - mix) + b * mix for a, b in zip(self.buf, wet)]


def write_wav(path, samples, peak=0.85):
    """16-bit mono, normalised to `peak`, through a gentle soft clip."""
    gain = peak / max(1e-6, max(abs(x) for x in samples))
    data = array.array("h", (int(max(-1.0, min(1.0, math.tanh(x * gain * 1.1))) * 32000) for x in samples))
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with wave.open(path, "wb") as f:
        f.setnchannels(1)
        f.setsampwidth(2)
        f.setframerate(SR)
        f.writeframes(data.tobytes())


def menu_theme(bpm=78):
    """The menu loop. Rendered three times over and only the middle pass kept: it carries the echoes and
    fading notes of the pass before it, so the end flows straight back into the start with no seam."""
    prog = [chord(57, "m"), chord(53), chord(48), chord(55)]   # Am F C G
    spb = 60 / bpm * 4                                        # seconds per bar
    unit = len(prog) * spb
    m = Mix(unit * 3 + 0.01)
    for rep in range(3):
        for b, ch in enumerate(prog):
            t0 = (rep * len(prog) + b) * spb
            for n in ch:   # soft pad
                m.note(t0, spb, n, "tri", vol=0.07, attack=0.5, decay=0.4, sustain=0.8, release=0.8, detune=0.004)
            m.note(t0, spb * 0.9, ch[0] - 12, "sine", vol=0.18, attack=0.05, release=0.3)   # bass
            tones = ch + [n + 12 for n in ch]
            arp = (0, 1, 2, 4, 2, 1)
            for k, idx in enumerate(arp):   # slow plucked arpeggio, an octave up
                m.note(t0 + k * spb / len(arp), spb / len(arp), tones[idx] + 12, "sine", vol=0.05, pluck=True,
                       decay=0.35)
    m.echo(0.33, 0.3, 0.25)
    return m.buf[int(unit * SR):int(2 * unit * SR)]


def game_theme(bpm=104):
    """The in-game loop: every chord spelled out as a fast plucked ripple, with a short bass note on beats
    1 and 3. Bars are a whole number of samples long, so the loop joins exactly."""
    prog = [chord(64, "m"), chord(60), chord(57, "m"), chord(59)]   # Em C Am B
    spb = round(60 / bpm * 4 * SR) / SR
    s16 = spb / 16
    unit = len(prog) * spb
    m = Mix(unit * 3 + 0.01)
    for rep in range(3):
        for b, ch in enumerate(prog):
            t0 = (rep * len(prog) + b) * spb
            ripple = [ch[0], ch[1], ch[2], ch[0] + 12, ch[2], ch[1], ch[0] + 12, ch[2]]
            for k, n in enumerate(ripple * 2):   # the arpeggio, in sixteenths
                m.note(t0 + k * s16, s16 * 2, n, "tri", vol=0.075, pluck=True, decay=0.18)
            m.note(t0, spb * 0.45, ch[0] - 12, "sine", vol=0.2, attack=0.01, release=0.1)            # bass on 1...
            m.note(t0 + spb / 2, spb * 0.45, ch[2] - 12, "sine", vol=0.17, attack=0.01, release=0.1)   # ...and 3
    m.echo(0.29, 0.25, 0.2)
    return m.buf[round(unit * SR):round(2 * unit * SR)]


if __name__ == "__main__":
    for name, theme in (("menu", menu_theme), ("game", game_theme)):
        path = os.path.join(MUSIC_DIR, name + ".wav")
        loop = theme()
        write_wav(path, loop)
        print(f"wrote {os.path.relpath(path, ROOT)} ({len(loop) / SR:.1f}s seamless loop)")
