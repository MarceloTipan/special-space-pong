# -*- encoding: utf-8 -*-

"""! @brief La clase Movimiento controla la raqueta con la cámara."""

##
# @file movimiento.py
#
# @brief Define la clase Movimiento.
#
# @section description_movimiento Descripción
# Mide el movimiento de la mano con la cámara usando flujo óptico
# (Farneback) sobre la resta de frames consecutivos, y lo convierte
# en un desplazamiento horizontal para la raqueta.
#
# @section notes_movimiento Notas
# - Si no hay cámara disponible, deteccion() devuelve siempre 0 y el
#   juego sigue funcionando (con teclado).
#
# @section author_movimiento Autores
# - Marcelo Tipán
#
# Copyright (c) 2021 Proyecto_Pong.  All rights reserved.

import cv2
import numpy as np


class Movimiento:
    """! Convierte el movimiento de la mano en desplazamiento de raqueta."""

    ## Umbrales de conteo -> desplazamiento en píxeles
    THRESHOLDS = ((400, 230), (300, 100), (200, 50), (100, 20), (10, 5))

    def __init__(self):
        """! Enciende la cámara y captura el primer frame de referencia."""
        self.webcam = cv2.VideoCapture(0)
        check, frame = self.webcam.read()

        ## Indica si hay cámara utilizable
        self.available = bool(check)
        if not self.available:
            print("[Movimiento] No se detectó cámara: control solo por teclado")
            return

        self.prev_frame = frame
        self.prev_gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        self.kernel = np.ones((3, 3), np.uint8)

    def deteccion(self):
        """! Devuelve el desplazamiento horizontal detectado (píxeles).
             Positivo = derecha, negativo = izquierda, 0 = sin movimiento."""
        if not self.available:
            return 0

        ret, frame = self.webcam.read()
        if not ret:
            return 0

        # Resta de frames consecutivos: aísla lo que se movió
        diff = cv2.subtract(frame, self.prev_frame)
        self.prev_frame = frame
        diff_gray = cv2.cvtColor(diff, cv2.COLOR_BGR2GRAY)

        # Dilatación para consolidar las zonas de movimiento
        diff_gray = cv2.dilate(diff_gray, self.kernel, iterations=3)

        # Flujo óptico Farneback entre el frame anterior y el actual
        flow = cv2.calcOpticalFlowFarneback(
            self.prev_gray, diff_gray, None, 0.2, 4, 18, 1, 3, 1.1, 0)
        self.prev_gray = diff_gray

        return self._flow_to_delta(diff_gray, flow)

    def _flow_to_delta(self, img, flow, step=8):
        """! Convierte el campo de flujo en un desplazamiento discreto.
             Muestrea el tercio inferior de la imagen (donde está la mano),
             cuenta cuántos puntos se mueven en cada dirección y mapea el
             conteo a un desplazamiento según THRESHOLDS."""
        h, w = img.shape[:2]
        y, x = np.mgrid[2 * h / 3:h:step, step / 2:w:step].reshape(2, -1).astype(int)
        fx = flow[y, x].T[0]

        # Conteo neto de puntos por dirección (redondeo como el original)
        moved = np.int32(fx + 0.5)
        count = int(np.sum(moved < 0)) - int(np.sum(moved > 0))

        sign = 1 if count > 0 else -1
        magnitude = abs(count)
        for threshold, delta in self.THRESHOLDS:
            if magnitude > threshold:
                return sign * delta
        return 0

    def release(self):
        """! Libera la cámara (llamar al salir del juego)."""
        if self.available:
            self.webcam.release()