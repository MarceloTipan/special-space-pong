"""Project Routes Configuration"""
from pathlib import Path

class PathConfig:
    """Project routes description"""

    # Base routes
    BASE_DIR = Path(__file__).resolve().parent.parent
    ASSETS_DIR = BASE_DIR / 'assets'
    IMAGE_DIR = ASSETS_DIR / 'images'
    FONT_DIR = ASSETS_DIR / 'fonts'
    SOUND_DIR = ASSETS_DIR / 'sounds'
    CONFIG_DIR = BASE_DIR / 'config'

    # Specific source routes
    FONT_PATH_ARCADE = FONT_DIR / "PressStart2P-Regular.TTF"
    FONT_PATH_JOYSTIX = FONT_DIR / "joystix monospace.otf"

    IMAGE_PATH_MENU = IMAGE_DIR / "background" / "via_lactea.png"
    IMAGE_PATH_LOADING = IMAGE_DIR / "background" / "carga.png"
    IMAGE_PATH_CREDITS = IMAGE_DIR / "test.png"
    IMAGE_PATH_INSTRUCTIONS = IMAGE_DIR / "test.png"
    IMAGE_PATH_GAME = IMAGE_DIR / "game_background.png"
    IMAGE_PATH_HIGHSCORES = IMAGE_DIR / "test.png"

    IMAGE_PATH_ICON = IMAGE_DIR / "pelota.png"
    IMAGE_PATH_BALL = IMAGE_DIR / "pelota.png"
    IMAGE_PATH_PADDLE_TOP = IMAGE_DIR / "raqueta_0.png"
    IMAGE_PATH_PADDLE = IMAGE_DIR / "raqueta_0.png"

    IMAGE_PATH_HEART = IMAGE_DIR / "heart.png"
    IMAGE_PATH_HEART_EMPTY = IMAGE_DIR / "heart_empty.png"

    IMAGE_PATH_ASTEROID = IMAGE_DIR / "heart.png"

    #ICON_INFO = IMAGE_DIR / "icon" / "heart.png"
    #ICON_TROPHY = IMAGE_DIR / "icon" / "heart.png"
    #ICON_CREDITS = IMAGE_DIR / "icon" / "heart.png"
    #ICON_SETTINGS = IMAGE_DIR / "icon" / "heart.png"

    MUSIC_PATH_MENU = SOUND_DIR / "menu.ogg"
    MUSIC_PATH_GAME = SOUND_DIR / "menu.ogg"

    SOUND_PATH_ERROR = SOUND_DIR / "error.mp3"
    SOUND_PATH_HIT = SOUND_DIR / "golpe.mp3"
    SOUND_PATH_HOVER = SOUND_DIR / "button/hover_button.mp3"
    SOUND_PATH_CLIC= SOUND_DIR / "button" / "clic_button.wav"
    SOUND_PATH_HIT_ENEMY = SOUND_DIR / "golpe.mp3"
    SOUND_PATH_HIT_OBSTACLE = SOUND_DIR / "golpe.mp3"