import pygame
from config import UI

class TextButton:
    """
    Botón de texto optimizado con efectos hover y configuración simplificada.
    """

    def __init__(self, pos, text, font_config, action,
                 base_color=UI.COLORS['GRAY'],
                 hover_color=UI.COLORS['WHITE'],
                 underline_on_hover=True,
                 hover_scale=1.1,
                 sonido=None):
        
        """
        Args:
            pos: Posición del botón (x, y)
            text: Texto del botón
            font_config: Tupla (font_path, font_size) o objeto font de pygame
            action: Función a ejecutar al hacer click
        """

        self.text = text
        self.action = action
        self.pos = pos
        self.base_color = base_color
        self.hover_color = hover_color
        self.underline_on_hover = underline_on_hover
        self.hover_scale = hover_scale
        self.sonido = sonido

        self.hovered = False
        self._setup_fonts(font_config)
        self._update_surface()

    def _setup_fonts(self, font_config):
        """Configura las fuentes normal y hover"""

        if isinstance(font_config, tuple):
            # Si es tupla: (font_path, font_size)
            font_path, font_size = font_config
            self.original_font = pygame.font.Font(font_path, font_size)
            self.hover_font = pygame.font.Font(font_path, int(font_size * self.hover_scale))
        else:
            # Si es un objeto font de pygame
            self.original_font = font_config
            self.hover_font = font_config  # Usar la misma fuente si no hay path/size

    def _update_surface(self):
        font = self.hover_font if self.hovered else self.original_font
        color = self.hover_color if self.hovered else self.base_color

        self.text_surface = font.render(self.text, True, color)
        self.rect = self.text_surface.get_rect(center=self.pos)

    def draw(self, surface):
        surface.blit(self.text_surface, self.rect)

        # if self.hovered and self.underline_on_hover:
        #     underline_rect = pygame.Rect(
        #         self.rect.left, self.rect.bottom - 12, self.rect.width, 1
        #     )
        #     pygame.draw.rect(surface, self.hover_color, underline_rect)

        #     overline_rect = pygame.Rect(
        #         self.rect.left, self.rect.top + 1, self.rect.width, 1
        #     )
        #     pygame.draw.rect(surface, self.hover_color, overline_rect)

    def update(self, mouse_pos, clicked):
        was_hovered = self.hovered
        self.hovered = self.rect.collidepoint(mouse_pos)

        if self.hovered != was_hovered:
            if self.sonido:
                self.sonido.play_hover()
            self._update_surface()

        if self.hovered and clicked:
            if self.sonido:
                self.sonido.play_click()
            self.action()

    def set_position(self, pos):
        """Cambia la posición del botón"""
        self.pos = pos
        self.update_surface()

    def set_text(self, text):
        """Cambia el texto del botón"""
        self.text = text
        self.update_surface()