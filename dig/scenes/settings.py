"""Settings: volume sliders for the master volume, the music and the sound effects."""
import pygame

from ..audio import CHANNELS
from ..config import GOLD, H, MUTED, PANEL, PANEL_EDGE, TEXT, W
from ..ui import Button, draw_text
from ..util import shade
from .base import Scene

SLIDER_W, ROW_H = 520, 96
KNOB_R = 14


class SettingsScene(Scene):
    simulate = False   # the game waits while you're here

    def __init__(self, game):
        super().__init__(game)
        self.return_to = "menu"
        self.dragging = None   # the channel whose slider is being dragged
        top = H // 2 - ROW_H * len(CHANNELS) // 2
        self.tracks = {key: pygame.Rect(W // 2 - SLIDER_W // 2 + 60, top + i * ROW_H + 40, SLIDER_W, 10)
                       for i, (key, _) in enumerate(CHANNELS)}
        self.back_button = Button((W // 2 - 80, top + ROW_H * len(CHANNELS) + 40, 160, 50), "< Back", self.close,
                                  size=28, color=(70, 64, 90))

    @property
    def audio(self):
        return self.game.audio

    def close(self):
        self.audio.save()
        self.game.switch(self.return_to)

    def slide(self, key, x):
        track = self.tracks[key]
        self.audio.set(key, (x - track.x) / track.w)

    def handle(self, event):
        if self.back_button.handle(event):
            return
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            for key, track in self.tracks.items():
                if track.inflate(KNOB_R * 2, KNOB_R * 3).collidepoint(event.pos):
                    self.dragging = key
                    self.slide(key, event.pos[0])
        elif event.type == pygame.MOUSEMOTION and self.dragging:
            self.slide(self.dragging, event.pos[0])
        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1 and self.dragging:
            if self.dragging in ("sfx", "master"):   # a blip, so you can hear the new effects level
                self.audio.play("tick")
            self.dragging = None
        elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self.close()

    def draw(self, s):
        f = self.fonts
        mouse = pygame.mouse.get_pos()
        draw_text(s, f, "SETTINGS", 60, TEXT, (W // 2, H // 2 - ROW_H * len(CHANNELS) // 2 - 80), "center")
        for key, label in CHANNELS:
            track = self.tracks[key]
            value = self.audio.volume[key]
            draw_text(s, f, label, 30, TEXT, (track.x - 30, track.centery), "midright")
            pygame.draw.rect(s, (24, 20, 32), track.inflate(4, 4), border_radius=6)
            pygame.draw.rect(s, PANEL_EDGE, track, 1, border_radius=5)
            fill = track.copy()
            fill.w = int(track.w * value)
            if fill.w:
                pygame.draw.rect(s, GOLD, fill, border_radius=5)
            knob = (track.x + int(track.w * value), track.centery)
            hot = self.dragging == key or pygame.Rect(knob[0] - KNOB_R, knob[1] - KNOB_R, KNOB_R * 2,
                                                      KNOB_R * 2).collidepoint(mouse)
            pygame.draw.circle(s, shade(GOLD, 1.15) if hot else TEXT, knob, KNOB_R)
            pygame.draw.circle(s, PANEL, knob, KNOB_R, 3)
            draw_text(s, f, f"{round(value * 100)}%", 28, GOLD if value else MUTED, (track.right + 24, track.centery),
                      "midleft")
            if key != "master":
                heard = self.audio.level(key)
                draw_text(s, f, f"heard at {round(heard * 100)}%", 20, MUTED, (track.x, track.bottom + 18), "midleft")
        self.back_button.draw(s, f, mouse)
        draw_text(s, f, "Drag a slider to change it   Esc: back", 20, MUTED, (W - 20, H - 20), "bottomright")
