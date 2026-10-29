"""Project Routes Configuration"""
from pathlib import Path

class PathConfig:
    """Project routes description"""

    #: Base routes
    BASE_DIR = Path(__file__).resolve().parent.parent

    CONFIG_DIR = BASE_DIR / 'config'
    UTILS_DIR = BASE_DIR / 'utils'
    ASSETS_DIR = BASE_DIR / 'assets'
    LOCALS_DIR = BASE_DIR / 'locals'

    FONT_DIR = ASSETS_DIR / 'fonts'
    IMAGE_DIR = ASSETS_DIR / 'images'
    SOUND_DIR = ASSETS_DIR / 'sounds'

    #: Local files
    LANGUAGES_FILE = LOCALS_DIR / "i18n"
    SETTINGS_FILE = LOCALS_DIR / "settings.json"
    HIGHSCORES_FILE = LOCALS_DIR / "highscores.json"
    CREDITS_FILE = LOCALS_DIR / "credits.json"

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
    ICON_INFO = IMAGE_DIR / "icon" / "info.png"
    ICON_TROPHY = IMAGE_DIR / "icon" / "trophy.png"
    ICON_CREDITS = IMAGE_DIR / "icon" / "credits.png"
    ICON_SETTINGS = IMAGE_DIR / "icon" / "settings.png"

    #: Sound files
    MUSIC_PATH_MENU = SOUND_DIR / "menu" / "menu_song.ogg"
    MUSIC_PATH_CREDITS = SOUND_DIR / "menu" / "credits_song.ogg"
    MUSIC_PATH_GAME = SOUND_DIR / "menu" / "game_song.ogg"

    SOUND_PATH_HOVER = SOUND_DIR / "button" / "hover_button.mp3"
    SOUND_PATH_CLIC= SOUND_DIR / "button" / "clic_button.wav"

    SOUND_PATH_ERROR = SOUND_DIR / "game" / "error.mp3"
    SOUND_PATH_GOAL = SOUND_DIR / "game" / "error.mp3"

    SOUND_PATH_HIT_ENEMY_1 = SOUND_DIR / "game" / "hit_enemy_1.ogg"
    SOUND_PATH_HIT_ENEMY_2 = SOUND_DIR / "game" / "hit_enemy_2.ogg"
    SOUND_PATH_HIT_ENEMY_3 = SOUND_DIR / "game" / "hit_enemy_3.ogg"
    SOUND_PATH_HIT_ENEMY_4 = SOUND_DIR / "game" / "hit_enemy_4.ogg"

    SOUND_PATH_HIT = SOUND_DIR / "game" / "hit_enemy_2.ogg"

    SOUND_PATH_HIT_PLAYER = SOUND_DIR / "button" / "hover_button.mp3"
    SOUND_PATH_HIT_WALL = SOUND_DIR / "button" / "clic_button.wav"
    SOUND_PATH_HIT_OBSTACLE = SOUND_DIR / "game" / "hit_enemy_3.ogg"

    SOUND_PATH_CHIP = SOUND_DIR / "button" / "hover_button.mp3"