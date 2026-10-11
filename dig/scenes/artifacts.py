"""Artifacts page: every artifact found so far, and silhouettes of the ones still out there."""
import pygame

from ..artifacts import ARTIFACTS, COMMON, CREW_ARTIFACTS
from ..camp import HIRES
from ..config import GOLD, H, MUTED, PANEL, PANEL_EDGE, TEXT, W
from ..enemies import BOSS_EVERY, BOSSES, ENEMY_TYPES
from ..icons import draw_icon
from ..ui import Button, draw_text
from ..util import shade
from .base import Scene

LEFT, RIGHT = 24, W - 24
GAP = 10
CARD_H = 66
COLS = 5
TROPHIES = [k for k, a in ARTIFACTS.items() if "boss" in a]


def wrap(fonts, text, size, width):
    """Split `text` into lines that fit `width` pixels."""
    lines, line = [], ""
    for word in text.split():
        trial = f"{line} {word}".strip()
        if line and fonts[size].size(trial)[0] > width:
            lines.append(line)
            line = word
        else:
            line = trial
    return lines + [line] if line else lines


class ArtifactScene(Scene):
    simulate = False   # like the upgrades and the crew page, browsing artifacts pauses the game

    def __init__(self, game):
        super().__init__(game)
        self.return_to = "play"
        self.back_button = Button((LEFT, H - 54, 130, 40), "< Back", self.close, size=26, color=(70, 64, 90))

    def close(self):
        self.world.new_artifacts.clear()   # they've been seen now
        self.game.switch(self.return_to)

    def handle(self, event):
        if self.back_button.handle(event):
            return
        if event.type == pygame.KEYDOWN and event.key in (pygame.K_ESCAPE, pygame.K_a):
            self.close()

    @staticmethod
    def card_rects(keys, top, cols):
        card_w = (RIGHT - LEFT - GAP * (cols - 1)) // cols
        return [(k, pygame.Rect(LEFT + (i % cols) * (card_w + GAP), top + (i // cols) * (CARD_H + GAP),
                                card_w, CARD_H)) for i, k in enumerate(keys)]

    def draw(self, s):
        f = self.fonts
        w = self.world
        mouse = pygame.mouse.get_pos()
        title = draw_text(s, f, "ARTIFACTS", 50, TEXT, (LEFT, 22))
        draw_text(s, f, f"{len(w.artifacts)} of {len(ARTIFACTS)} found  -  paused", 26, MUTED,
                  (title.right + 18, title.centery + 2), "midleft")

        top = 88
        draw_text(s, f, "Buried in the dig  -  watch for blocks with a violet glint", 24, GOLD, (LEFT, top))
        commons = self.card_rects(COMMON, top + 28, COLS)
        top = commons[-1][1].bottom + 14
        draw_text(s, f, f"Boss trophies  -  a boss guards every {BOSS_EVERY}th metre", 24, GOLD, (LEFT, top))
        trophies = self.card_rects(TROPHIES, top + 28, COLS)
        top = trophies[-1][1].bottom + 14
        draw_text(s, f, "Camp crew  -  each buried in the dig once its hire is with you", 24, GOLD, (LEFT, top))
        crew = self.card_rects(CREW_ARTIFACTS, top + 28, COLS)
        hovered = None
        for key, rect in commons + trophies + crew:
            self.draw_card(s, key, rect)
            if rect.collidepoint(mouse) and key in w.artifacts:
                hovered = key
        if hovered:
            draw_text(s, f, f"\"{ARTIFACTS[hovered]['lore']}\"", 22, ARTIFACTS[hovered]["color"],
                      (W // 2 + 60, H - 34), "center")
        self.back_button.draw(s, f, mouse)
        draw_text(s, f, "A / Esc: back", 20, MUTED, (RIGHT, H - 34), "midright")

    def draw_card(self, s, key, rect):
        f = self.fonts
        w = self.world
        art = ARTIFACTS[key]
        found = key in w.artifacts
        pygame.draw.rect(s, PANEL if found else (30, 26, 40), rect, border_radius=10)
        pygame.draw.rect(s, art["color"] if found else PANEL_EDGE, rect, 2, border_radius=10)
        ic = (rect.x + 38, rect.centery)
        if found:
            draw_icon(s, art["icon"], ic, 20, art["color"])
            size = next((n for n in (22, 20, 18) if f[n].size(art["name"])[0] <= rect.w - 80), 18)   # (long names shrink)
            draw_text(s, f, art["name"], size, art["color"], (rect.x + 72, rect.y + 14), "midleft")
            lines = wrap(f, art["bonus"], 20, rect.w - 84)
            for i, line in enumerate(lines[:2]):
                draw_text(s, f, line, 20, TEXT, (rect.x + 72, rect.y + 35 + i * 18), "midleft")
            if key in w.new_artifacts:
                tag = draw_text(s, f, "NEW", 18, GOLD, (rect.right - 12, rect.y + 14), "midright")
                pygame.draw.rect(s, GOLD, tag.inflate(8, 4), 1, border_radius=4)
        else:
            pygame.draw.circle(s, shade(PANEL_EDGE, 0.8), ic, 20, 2)
            draw_text(s, f, "?", 30, shade(PANEL_EDGE, 1.3), ic, "center")
            draw_text(s, f, "???", 22, MUTED, (rect.x + 72, rect.y + 14), "midleft")
            if "boss" in art:
                boss = art["boss"]
                depth = (BOSSES.index(boss) + 1) * BOSS_EVERY
                name = ENEMY_TYPES[boss]["name"]
                hint = f"Defeat {name if name.startswith('The ') else 'the ' + name} (first at {depth}m)"
            elif "crew" in art and art["crew"] not in w.camp:
                hint = f"Hire the {HIRES[art['crew']]['title']} at Base Camp"
            else:
                hint = "Still buried somewhere below"
            for i, line in enumerate(wrap(f, hint, 20, rect.w - 84)[:2]):
                draw_text(s, f, line, 20, MUTED, (rect.x + 72, rect.y + 35 + i * 18), "midleft")
