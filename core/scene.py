# -*- encoding: utf-8 -*-

"""! @brief La clase Scene gestiona las escenas y controla los eventos de teclado."""

##
# @file scene.py
#
# @brief Define la clase Scene.
#
# @section description_scene Descripción
# Clase padre que ayuda a la gestión de las escenas mostradas en la aplicación
# - Scene (clase)
#
# @section notes_scene Notas
# - Una escena es una parte visible del juego, como una pantalla
#   de presentación o menú de opciones. Permite instanciar cada
#   pantalla que se muestra al usuario.
#
# @section author_scene Autores
# - Marcelo Tipán
#
# Copyright (c) 2021 Proyecto_Pong.  All rights reserved.

class Scene:
    """Representa un escena abstracta del videojuego.

    Una escena es una parte visible del juego, como una pantalla
    de presentación o menú de opciones. Tiene que crear un objeto
    derivado de esta clase para crear una escena utilizable."""

    def __init__(self, director):
        """! Inicializa un objeto de la clase Director.
            @param director  Objeto de la clase Director.
        """
        self.director = director

    def on_enter(self):
        """! Se llama cuando la escena pasa a estar activa, con la ventana
             ya configurada. Aquí se cargan texturas y recursos que
             dependen del contexto OpenGL."""
        pass
    
    def on_update(self):
        """!Actualización lógica que se llama automáticamente desde el director."""
        pass

    def on_event(self, event):
        """!Se llama cuando llega un evento especifico al bucle."""
        pass

    def on_draw(self, screen):
        """!Se llama cuando se quiere dibujar la pantalla."""
        pass