"""Fixed spots on the board and effect timings shared by the simulation (world) and the renderer."""
from .config import GRID

WHETSTONE_POS = (0.5, GRID - 0.5)        # the sharpening wheel sits on the board's left corner
BALLISTA_POS = (GRID - 0.5, GRID - 0.5)  # the ballista sits on the board's front corner
BOILER_POS = (GRID - 0.5, 0.5)           # the Steam Boiler sits on the board's right corner
STEAM_SECS = 1.6                         # the Steam Boiler's vent: steam rolling across the board
BOLT_SPEED = 14.0                        # a ballista bolt's speed (tiles a second)
ROCK_SECS = 0.45                         # a rock thrown at a boss: its flight time
MITTS_CLICKS = 6                         # the Clay Golem leaps in and slams every this many of your clicks
DIVINING_CHANCE = 0.35                   # Divining Rod: the chance a new layer hides an artifact (not the usual 12%)
BANNER_RADIUS, BANNER_BOOST = 2.5, 0.25  # Banner of the Deep: crew this close to it (tiles) swing this much faster...
FRINGE_RADIUS = 3.5                      # Gold Fringe: the banner reaches this far instead...
FRINGE_POWER, FRINGE_VALUE = 0.15, 0.25  # ...the crew under it hit this much harder, and what they break pays this more
HEIRLOOM_EVERY, HEIRLOOM_DEEP = 5, 2     # Heirloom Pickaxe: every this many of Rocco's blows, this many blocks beyond
                                         # the one he hits (in line) take the blow too
BLAST_ARROW_RADIUS = 1.6                 # Explosive Arrows: a fire arrow's blast reaches the monsters this close...
BLAST_ARROW_BLOCKS = 3.0                 # ...and hits the 3x3 of blocks round its target for this many of your clicks
GLAZE_SECS, GLAZE_BONUS = 6.0, 0.3       # Glazed Fists: blocks Mitts slams stay glazed this long, the crew hitting
                                         # them this much harder
WHEEL_LIFE, WHEEL_MAX = 2.0, 3           # Potter's Wheel: mudlings last this many times as long, this many at once
BANNER_REPLANT = 2.0                     # ...and Rocco moves it on once he's digging this far from it
CHOMP_EVERY = 17.0                       # the camp's Friendly Mimic gobbles a block this often...
PUP_EVERY, PUP_PAYOUT = 25.0, 1.5        # Mimic Pup: gobbles a block this often, coughing up this many times its worth
COLLAR_EVERY, COLLAR_BITE = 6.0, 0.5     # Spiked Collar: Chompers bites a monster that's grabbed someone this often,
COLLAR_SWALLOW = ("bat", "slimeling", "spider", "wisp", "eggsac")   # for this share of its health (these: gulped
                                         # down whole, for twice the bounty)
TAXES_SHARE, TAXES_HURT = 0.2, 0.1       # Death and Taxes: a monster pays this share of its bounty, and loses this share
TAXES_REACH = 3.0                        # of its health - any within this many tiles of Mr. Pennyworth
ROUNDING_OFF = 0.1                       # Rounding Errors: every upgrade costs this much less
CHOMP_SHOW = 0.5                         # Chompers' lid hangs open this long after it gobbles a block
FEMUR_SECS = 0.5                         # a bone the crew throw (Tyrant's Femur): its flight time
CHEST_FX_SECS = 2.4                      # treasure chest bursting open, its beam of light rising and fading
SPIKE_FX_SECS = 0.6                      # Booby Traps springing
