#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""! @brief Tabla de mejores puntajes, persistida en highscores.json.

Uso:
    from utils import highscores

    if highscores.qualifies(puntos):
        posicion = highscores.add("MTP", puntos, nivel)
    tabla = highscores.get_all()
"""

import json
from datetime import date
from pathlib import Path

## Archivo de persistencia (junto a settings.json)
SCORES_FILE = Path(__file__).resolve().parent.parent / "highscores.json"

## Cantidad máxima de entradas en la tabla
MAX_ENTRIES = 5

_scores = None


def _load():
    global _scores
    if _scores is not None:
        return _scores
    try:
        with open(SCORES_FILE, encoding="utf-8") as f:
            _scores = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        _scores = []
    return _scores


def _save():
    with open(SCORES_FILE, "w", encoding="utf-8") as f:
        json.dump(_scores, f, ensure_ascii=False, indent=2)


def get_all():
    """! Devuelve la tabla ordenada de mayor a menor puntaje."""
    return list(_load())


def qualifies(points):
    """! ¿Este puntaje entra al top?
        @param points  Puntaje a evaluar.
        @return True si hay espacio o si supera al último de la tabla.
    """
    scores = _load()
    if points <= 0:
        return False
    if len(scores) < MAX_ENTRIES:
        return True
    return points > scores[-1]["points"]


def add(initials, points, level):
    """! Inserta una entrada en la tabla y la persiste.
        @param initials  Tres letras del jugador.
        @param points    Puntaje alcanzado.
        @param level     Nivel máximo alcanzado en la partida.
        @return La posición (1 = primer lugar) donde quedó la entrada.
    """
    scores = _load()
    entry = {
        "initials": initials.upper()[:3],
        "points": int(points),
        "level": int(level),
        "date": date.today().isoformat(),
    }
    scores.append(entry)
    scores.sort(key=lambda e: e["points"], reverse=True)
    del scores[MAX_ENTRIES:]
    _save()
    return scores.index(entry) + 1 if entry in scores else 0