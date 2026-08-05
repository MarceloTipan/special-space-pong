#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""! @brief Configuración persistente del usuario (volumen, idioma, pantalla).

Se guarda en settings.json en la raíz del proyecto. Uso:

    from utils import settings

    settings.load()                    # una vez, al arrancar
    vol = settings.get("volume")       # leer
    settings.set("volume", 0.5)        # escribir (guarda automáticamente)
"""

import json
from pathlib import Path

## Archivo donde se persiste la configuración
SETTINGS_FILE = Path(__file__).resolve().parent.parent / "settings.json"

## Valores por defecto (también definen qué claves son válidas)
DEFAULTS = {
    "volume": 0.8,
    "language": "es",
    "fullscreen": False,
    "difficulty": "normal",
}

_data = dict(DEFAULTS)


def load():
    """! Carga settings.json; si no existe o está corrupto, usa defaults."""
    global _data
    _data = dict(DEFAULTS)
    try:
        with open(SETTINGS_FILE, encoding="utf-8") as f:
            stored = json.load(f)
        # Solo acepta claves conocidas (ignora basura de versiones viejas)
        _data.update({k: v for k, v in stored.items() if k in DEFAULTS})
    except (FileNotFoundError, json.JSONDecodeError):
        pass


def save():
    """! Escribe la configuración actual a disco."""
    with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
        json.dump(_data, f, indent=2)


def get(key):
    """! Devuelve el valor de una clave de configuración."""
    return _data[key]


def set(key, value):
    """! Cambia un valor y lo persiste inmediatamente.
        @param key    Clave (debe existir en DEFAULTS).
        @param value  Nuevo valor.
    """
    if key not in DEFAULTS:
        raise KeyError(f"Clave de configuración desconocida: {key}")
    _data[key] = value
    save()