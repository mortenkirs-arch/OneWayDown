"""Fixed spots on the board and effect timings shared by the simulation (world) and the renderer."""
from .config import GRID

WHETSTONE_POS = (0.5, GRID - 0.5)        # the sharpening wheel sits on the board's left corner
BALLISTA_POS = (GRID - 0.5, GRID - 0.5)  # the ballista sits on the board's front corner
BOILER_POS = (GRID - 0.5, 0.5)           # the Steam Boiler sits on the board's right corner
STEAM_SECS = 1.6                         # the Steam Boiler's vent: steam rolling across the board
BOLT_SECS = 0.3                          # a ballista bolt's flight time
ROCK_SECS = 0.45                         # a rock thrown at a boss: its flight time
MITTS_CLICKS = 6                         # the Clay Golem leaps in and slams every this many of your clicks
CHOMP_EVERY = 17.0                       # the camp's Friendly Mimic gobbles a block this often...
CHOMP_SHOW = 0.5                         # Chompers' lid hangs open this long after it gobbles a block
FEMUR_SECS = 0.5                         # a bone the crew throw (Tyrant's Femur): its flight time
CHEST_FX_SECS = 2.4                      # treasure chest bursting open, its beam of light rising and fading
SPIKE_FX_SECS = 0.6                      # Booby Traps springing
