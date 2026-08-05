from .paths import PathConfig
from .fonts import FontConfig
from .ui import UIConfig
from .game import GameConfig

# Crear instancias globales para fácil acceso
PATHS = PathConfig()
FONTS = FontConfig()
UI = UIConfig()
GAME = GameConfig()