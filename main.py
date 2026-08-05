#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""! @brief Clase principal."""

##
# @mainpage Proyecto_Pong
#
# @section description_main Descripción
# Aplicación que crea el clásico juego Pong, diseñado para un solo jugador y basa el movimiento de la
# raqueta en la detección del movimiento de la mano mediante una cámara.
# Contiene cuatro pantallas que muestran el menú principal, las instrucciones, los créditos, y la pantalla de juego.
#
# @section notes_main Notas
# - El juego cuenta con eventos de ratón para navegar por los diferentes menús.
# - El juego cuenta con detección de movimiento, lo que permite al usuario controlar la raqueta dentro del juego.
# - En la pantalla de juego se puede ver el puntaje, número de vidas, tiempo y nivel de dificultad.
#
# @section author_inicio Autores
# - Marcelo Tipán
#
# Copyright (c) 2021 Proyecto_Pong.  All rights reserved

##
# @file inicio.py
#
# @brief Clase principal.
#
# @section description_inicio Descripción
# Clase principal encargada de iniciar la aplicación y llamar a las demas clases.
#
# @section libraries_inicio Librerias/Modulos
# - Pygame (https://www.pygame.org/news)
#  - Acceso a la función init.
# - Modulo director (local)
#   - Acceso a la clase Director.
# - Modulo menu (local)
#   - Accesso a la clase Menu.
#
# @section author_inicio Autores
# - Marcelo Tipán
#
# Copyright (c) 2021 Proyecto Pong.  All rights reserved.

# Importar Módulos
import pygame
from core import director
from scenes import menu
from utils import settings
from utils.i18n import set_language

def main():
    """! Se inicializa el programa"""
    
    settings.load()
    set_language(settings.get("language"))

    ##Inicializa el programa
    pygame.init()
    ##Inicializa la clase Director
    app = director.Director()
    ##Inicializa la clase Menu
    scene = menu.Menu(app)
    ##Funciones de la clase Director
    app.change_scene(scene)
    app.loop()

if __name__ == '__main__':
    main()