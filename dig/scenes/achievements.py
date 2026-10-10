"""Achievements page: every achievement - the ones earned lit up, the rest dimmed but readable, so you know what to
aim for - and, in a section of their own, the legendary ones that look impossible."""
import pygame

from ..achievements import ACHIEVEMENTS, LEGENDARY, STANDARD
from ..config import GOLD, H, MUTED, PANEL, PANEL_EDGE, TEXT, W
from ..icons import draw_icon, draw_padlock
from ..ui import Button, draw_text
from ..util import shade
from .artifacts import wrap
from .base import Scene

LEFT, RIGHT = 24, W - 24
TOP, BOTTOM = 96, H - 70          # the scrolling list sits between these
GAP = 10
CARD_H = 66
COLS = 4
EARNED = (120, 200, 255)          # an earned achievement's colour...
LEGEND = (255, 196, 70)           # ...and a legendary one's


class AchievementScene(Scene):
    simulate = False   # like the other pages, looking through them pauses the game

    def __init__(self, game):
        super().__init__(game)
        self.scroll = 0
        self.back_button = Button((LEFT, H - 54, 130, 40), "< Back", self.close, size=26, color=(70, 64, 90))

    def enter(self):
        self.scroll = 0

    def close(self):
        self.game.switch("play")

    def handle(self, event):
        if self.back_button.handle(event):
            return
        if event.type == pygame.MOUSEWHEEL:
            self.scroll = max(0, min(self.max_scroll(), self.scroll - event.y * 50))
        elif event.type == pygame.KEYDOWN and event.key in (pygame.K_ESCAPE, pygame.K_h):
            self.close()

    def layout(self):
        """[(heading, y)], [(key, rect)] for everything on the page, before scrolling."""
        y, headings, cards = TOP, [], []
        for heading, keys, cols in ((None, STANDARD, COLS), ("Legendary  -  the ones that look impossible", LEGENDARY, 2)):
            card_w = (RIGHT - LEFT - GAP * (cols - 1)) // cols   # (the legendary ones have more to say: wider)
            if heading:
                headings.append((heading, y + 8))
                y += 40
            for i, key in enumerate(keys):
                cards.append((key, pygame.Rect(LEFT + (i % cols) * (card_w + GAP),
                                               y + (i // cols) * (CARD_H + GAP), card_w, CARD_H)))
            y += ((len(keys) + cols - 1) // cols) * (CARD_H + GAP) + 10
        return headings, cards, y

    def max_scroll(self):
        return max(0, self.layout()[2] - BOTTOM)

    def draw(self, s):
        f = self.fonts
        w = self.world
        mouse = pygame.mouse.get_pos()
        title = draw_text(s, f, "ACHIEVEMENTS", 50, TEXT, (LEFT, 22))
        got = sum(1 for k in ACHIEVEMENTS if k in w.achievements)
        draw_text(s, f, f"{got} of {len(ACHIEVEMENTS)} earned  -  paused", 26, MUTED,
                  (title.right + 18, title.centery + 2), "midleft")
        legends = sum(1 for k in LEGENDARY if k in w.achievements)
        draw_text(s, f, f"Legendary: {legends} of {len(LEGENDARY)}", 24, LEGEND, (RIGHT, title.centery + 2), "midright")
        headings, cards, _ = self.layout()
        clip = s.get_clip()
        s.set_clip(pygame.Rect(0, TOP, W, BOTTOM - TOP))
        for text, y in headings:
            draw_text(s, f, text, 26, LEGEND, (LEFT, y - self.scroll))
        for key, rect in cards:
            rect = rect.move(0, -self.scroll)
            if rect.bottom > TOP and rect.top < BOTTOM:
                self.draw_card(s, key, rect)
        s.set_clip(clip)
        if self.scroll < self.max_scroll():
            draw_text(s, f, "Scroll for more", 20, MUTED, (W // 2, BOTTOM + 12), "midtop")
        self.back_button.draw(s, f, mouse)
        draw_text(s, f, "H / Esc: back", 20, MUTED, (RIGHT, H - 34), "midright")

    def draw_card(self, s, key, rect):
        f = self.fonts
        a = ACHIEVEMENTS[key]
        earned = key in self.world.achievements
        legendary = a.get("legendary", False)
        color = LEGEND if legendary else EARNED
        pygame.draw.rect(s, PANEL if earned else (30, 26, 40), rect, border_radius=10)
        edge = color if earned else (shade(LEGEND, 0.55) if legendary else PANEL_EDGE)
        pygame.draw.rect(s, edge, rect, 2 if earned or legendary else 1, border_radius=10)
        ic = (rect.x + 32, rect.centery)
        if earned:
            pygame.draw.circle(s, shade(color, 0.3), ic, 22)
            draw_icon(s, a["icon"], ic, 16, color)
        else:
            pygame.draw.circle(s, (40, 36, 52), ic, 22)
            draw_icon(s, a["icon"], ic, 16, (78, 72, 92))
            draw_padlock(s, (ic[0] + 14, ic[1] + 13), 6, (150, 140, 120))
        draw_text(s, f, a["name"], 22, color if earned else (170, 164, 184), (rect.x + 62, rect.y + 16), "midleft")
        for i, line in enumerate(wrap(f, a["desc"], 18, rect.w - 72)[:2]):
            draw_text(s, f, line, 18, TEXT if earned else MUTED, (rect.x + 62, rect.y + 36 + i * 16), "midleft")
