"""General Game Configuration"""

class GameConfig:
    """Main game settings"""
    
    # Display settings
    SCREEN_WIDTH =  1280 #|1280 # 1280* 1024 480**
    SCREEN_HEIGHT =  1000 #|663 # 663* 720 768 800**
    SCREEN_SIZE = (SCREEN_WIDTH, SCREEN_HEIGHT)
    FPS = 60
        
    # Director's statuses
    STATUS_MENU = 0
    STATUS_INSTRUCTIONS = 1
    STATUS_CREDITS = 2
    STATUS_LOADING = 3
    STATUS_GAME = 4
    STATUS_SETTINGS = 5
    STATUS_HIGHSCORES = 6
    STATUS_NAME_ENTRY = 7
    
    