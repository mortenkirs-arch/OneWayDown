"""Reusable UI widgets and text helpers."""
import pygame

from .config import MUTED, PANEL, PANEL_EDGE, TEXT
from .util import shade


class Button:
    def __init__(self, rect, text, action, size=30, color=(86, 70, 130)):
        self.rect = pygame.Rect(rect)
        self.text, self.action, self.size, self.color = text, action, size, color
        self.enabled = True

    def draw(self, surf, fonts, mouse):
        hover = self.enabled and self.rect.collidepoint(mouse)
        base = self.color if self.enabled else (60, 56, 70)
        if hover:
            base = shade(base, 1.25)
        shadow = self.rect.move(0, 4)
        pygame.draw.rect(surf, shade(base, 0.5), shadow, border_radius=10)
        pygame.draw.rect(surf, base, self.rect, border_radius=10)
        pygame.draw.rect(surf, shade(base, 1.4), self.rect, 2, border_radius=10)
        label = fonts[self.size].render(self.text, True, TEXT if self.enabled else MUTED)
        surf.blit(label, label.get_rect(center=self.rect.center))

    def handle(self, event):
        if (self.enabled and event.type == pygame.MOUSEBUTTONDOWN and event.button == 1
                and self.rect.collidepoint(event.pos)):
            self.action()
            return True
        return False


class Fonts(dict):
    """Lazily-created default fonts keyed by pixel size: fonts[24]."""

    def __missing__(self, size):
        f = pygame.font.Font(None, size)
        self[size] = f
        return f


def draw_text(surf, fonts, text, size, color, pos, anchor="topleft"):
    img = fonts[size].render(text, True, color)
    rect = img.get_rect(**{anchor: pos})
    surf.blit(img, rect)
    return rect


def draw_panel(surf, rect, radius=12):
    pygame.draw.rect(surf, PANEL, rect, border_radius=radius)
    pygame.draw.rect(surf, PANEL_EDGE, rect, 2, border_radius=radius)


def wrap_text(font, text, width):
    lines, line = [], ""
    for word in text.split():
        trial = f"{line} {word}".strip()
        if font.size(trial)[0] <= width:
            line = trial
        else:
            lines.append(line)
            line = word
    if line:
        lines.append(line)
    return lines
