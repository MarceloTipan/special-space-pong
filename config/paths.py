"""Project Routes Configuration"""
from pathlib import Path

class PathConfig:
    """Project routes description"""

    #: Base routes
    BASE_DIR = Path(__file__).resolve().parent.parent

    CONFIG_DIR = BASE_DIR / 'config'
    UTILS_DIR = BASE_DIR / 'utils'
    ASSETS_DIR = BASE_DIR / 'assets'

    FONT_DIR = ASSETS_DIR / 'fonts'
    IMAGE_DIR = ASSETS_DIR / 'images'
    SOUND_DIR = ASSETS_DIR / 'sounds'

    LOCALS_DIR = UTILS_DIR / 'locals'

    #: Local files
    SETTINGS_FILE = BASE_DIR / "settings.json"
    HIGHSCORES_FILE = BASE_DIR / "highscores.json"

    #: Font files
    FONT_PATH_ARCADE = FONT_DIR / "PressStart2P-Regular.TTF"
    FONT_PATH_JOYSTIX = FONT_DIR / "joystix monospace.otf"

    #: Image files
    IMAGE_PATH_MENU = IMAGE_DIR / "background" / "via_lactea.png"
    IMAGE_PATH_LOADING = IMAGE_DIR / "background" / "carga.png"

    IMAGE_PATH_GAME = IMAGE_DIR / "background" / "game_background.png"
    IMAGE_PATH_CREDITS = IMAGE_DIR / "background" / "black_background.png"
    IMAGE_PATH_INSTRUCTIONS = IMAGE_DIR / "background" / "black_background.png"
    IMAGE_PATH_HIGHSCORES = IMAGE_DIR / "background" / "black_background.png"

    IMAGE_PATH_ICON = IMAGE_DIR / "game" / "pelota.png"
    IMAGE_PATH_BALL = IMAGE_DIR / "game" / "pelota.png"
    IMAGE_PATH_PADDLE_TOP = IMAGE_DIR / "game" / "raqueta_0.png"
    IMAGE_PATH_PADDLE = IMAGE_DIR / "game" / "raqueta_0.png"
    IMAGE_PATH_ASTEROID = IMAGE_DIR / "game" / "asteroid.png"

    IMAGE_PATH_HEART = IMAGE_DIR / "HUD" / "heart.png"
    IMAGE_PATH_HEART_EMPTY = IMAGE_DIR / "HUD" / "heart_empty.png"

    #: Icon files
    ICON_INFO = IMAGE_DIR / "icon" / "icon.png"
    ICON_TROPHY = IMAGE_DIR / "icon" / "icon.png"
    ICON_CREDITS = IMAGE_DIR / "icon" / "icon.png"
    ICON_SETTINGS = IMAGE_DIR / "icon" / "icon.png"

    #: Sound files
    MUSIC_PATH_MENU = SOUND_DIR / "menu" / "menu.ogg"
    MUSIC_PATH_GAME = SOUND_DIR / "menu" / "menu.ogg"

    SOUND_PATH_HOVER = SOUND_DIR / "button" / "hover_button.mp3"
    SOUND_PATH_CLIC= SOUND_DIR / "button" / "clic_button.wav"

    SOUND_PATH_ERROR = SOUND_DIR / "game" / "error.mp3"
    SOUND_PATH_HIT = SOUND_DIR / "game" / "golpe.mp3"
    SOUND_PATH_HIT_ENEMY = SOUND_DIR / "game" / "golpe.mp3"
    SOUND_PATH_HIT_OBSTACLE = SOUND_DIR / "game" / "golpe.mp3"