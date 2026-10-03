"""Base class for screens. Add a new screen by subclassing Scene and registering it in Game."""


class Scene:
    simulate = True   # whether the world keeps ticking while this scene is active

    def __init__(self, game):
        self.game = game

    @property
    def world(self):
        return self.game.world

    @property
    def fonts(self):
        return self.game.fonts

    def enter(self):
        """Called each time the scene becomes active."""

    def handle(self, event):
        pass

    def update(self, dt):
        pass

    def draw(self, surf):
        pass
