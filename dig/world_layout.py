"""Fixed spots on the board and effect timings shared by the simulation (world) and the renderer."""
from .config import GRID

WHETSTONE_POS = (0.5, GRID - 0.5)        # the sharpening wheel sits on the board's left corner
BALLISTA_POS = (GRID - 0.5, GRID - 0.5)  # the ballista sits on the board's front corner
BOLT_SECS = 0.3                          # a ballista bolt's flight time
CHEST_FX_SECS = 1.0                      # treasure chest bursting open
SPIKE_FX_SECS = 0.6                      # Booby Traps springing
