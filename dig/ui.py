"""Reusable UI widgets and text helpers."""
import pygame

from .config import MUTED, PANEL, PANEL_EDGE, TEXT
from .util import shade


COIN, COIN_EDGE, COIN_SHINE = (255, 205, 70), (185, 130, 35), (255, 242, 180)


def draw_coin(surf, center, r):
    """A little gold coin: thick edge, raised inner ring and a glint."""
    x, y = int(center[0]), int(center[1])
    r = max(3, int(r))
    pygame.draw.circle(surf, COIN_EDGE, (x, y + max(1, r // 5)), r)          # coin thickness
    pygame.draw.circle(surf, COIN, (x, y), r)
    pygame.draw.circle(surf, COIN_EDGE, (x, y), max(2, int(r * 0.66)), max(1, r // 6))
    pygame.draw.circle(surf, COIN_SHINE, (x - int(r * 0.35), y - int(r * 0.35)), max(1, r // 4))


def gold_label(fonts, text, size, color):
    """A coin followed by `text`, as one surface (so it can fade like other text)."""
    img = fonts[size].render(text, True, color)
    r = max(3, int(size * 0.3))
    gap = max(3, size // 7)
    w, h = 2 * r + gap + img.get_width(), max(img.get_height(), 2 * r + 3)
    label = pygame.Surface((w, h), pygame.SRCALPHA)
    draw_coin(label, (r, h // 2 - 1), r)
    label.blit(img, img.get_rect(midleft=(2 * r + gap, h // 2)))
    return label


def draw_gold(surf, fonts, text, size, color, pos, anchor="topleft"):
    """Draw a gold amount with its coin icon; returns the bounding rect."""
    label = gold_label(fonts, text, size, color)
    rect = label.get_rect(**{anchor: pos})
    surf.blit(label, rect)
    return rect


class Button:
    def __init__(self, rect, text, action, size=30, color=(86, 70, 130)):
        self.rect = pygame.Rect(rect)
        self.text, self.action, self.size, self.color = text, action, size, color
        self.enabled = True
        self.gold = None   # optional price shown as "<text>  (coin) <gold>"

    def draw(self, surf, fonts, mouse):
        hover = self.enabled and self.rect.collidepoint(mouse)
        base = self.color if self.enabled else (60, 56, 70)
        if hover:
            base = shade(base, 1.25)
        shadow = self.rect.move(0, 4)
        pygame.draw.rect(surf, shade(base, 0.5), shadow, border_radius=10)
        pygame.draw.rect(surf, base, self.rect, border_radius=10)
        pygame.draw.rect(surf, shade(base, 1.4), self.rect, 2, border_radius=10)
        color = TEXT if self.enabled else MUTED
        label = fonts[self.size].render(self.text, True, color)
        if self.gold is None:
            surf.blit(label, label.get_rect(center=self.rect.center))
            return
        price = gold_label(fonts, self.gold, self.size, color)
        gap = self.size // 2
        x = self.rect.centerx - (label.get_width() + gap + price.get_width()) // 2
        surf.blit(label, label.get_rect(midleft=(x, self.rect.centery)))
        surf.blit(price, price.get_rect(midleft=(x + label.get_width() + gap, self.rect.centery)))

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
