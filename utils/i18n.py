#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""! @brief Módulo i18n: centraliza todos los textos del juego y permite traducirlos.

Uso:
    from i18n import t, set_language

    set_language("es")          # se llama una vez al iniciar el juego
    texto = t("menu.start")     # -> "JUGAR"
    texto = t("menu.exit")      # -> "SALIR"

Los textos viven en archivos JSON dentro de la carpeta locales/:
    locales/es.json
    locales/en.json

Para agregar un idioma nuevo basta con crear otro JSON (ej. locales/pt.json),
sin tocar una sola línea de código.
"""

import json
from pathlib import Path

## Carpeta donde viven los archivos de traducción
LOCALES_DIR = Path(__file__).parent / "locals"

## Idioma por defecto si falta una clave o un archivo
DEFAULT_LANGUAGE = "es"

_translations: dict = {}
_fallback: dict = {}
_current_language: str = DEFAULT_LANGUAGE


def _load_file(lang: str) -> dict:
    """! Carga el JSON de un idioma. Devuelve {} si no existe."""
    path = LOCALES_DIR / f"{lang}.json"
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"[i18n] Advertencia: no existe {path}")
        return {}


def set_language(lang: str) -> None:
    """! Establece el idioma activo del juego.
        @param lang  Código del idioma ("es", "en", ...).
    """
    global _translations, _fallback, _current_language
    _current_language = lang
    _translations = _load_file(lang)
    # El idioma por defecto actúa como respaldo si falta una clave
    _fallback = _translations if lang == DEFAULT_LANGUAGE else _load_file(DEFAULT_LANGUAGE)


def get_language() -> str:
    """! Devuelve el código del idioma activo."""
    return _current_language


def available_languages() -> list:
    """! Lista los idiomas disponibles según los JSON en locales/."""
    return sorted(p.stem for p in LOCALES_DIR.glob("*.json"))


def t(key: str, **kwargs) -> str:
    """! Devuelve el texto traducido asociado a una clave.
        @param key     Clave con notación de punto, ej. "menu.start".
        @param kwargs  Valores para interpolar, ej. t("game.score", points=10)
                       con "score": "Puntos: {points}" en el JSON.
        @return El texto traducido, o la clave misma si no se encuentra
                (así el error es visible en pantalla y fácil de detectar).
    """
    for source in (_translations, _fallback):
        node = source
        for part in key.split("."):
            if isinstance(node, dict) and part in node:
                node = node[part]
            else:
                node = None
                break
        if isinstance(node, str):
            return node.format(**kwargs) if kwargs else node
    return key  # clave no encontrada: se muestra tal cual para depurar


# Carga inicial con el idioma por defecto
set_language(DEFAULT_LANGUAGE)