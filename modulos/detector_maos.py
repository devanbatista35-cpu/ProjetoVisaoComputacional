import time

import cv2
import mediapipe as mp

from modulos.config import RESOLUCAO_X, RESOLUCAO_Y
from modulos.gestos import EstabilizadorLado


class DetectorMaos:
    """Encontra as mãos na imagem e devolve as coordenadas em pixels."""

    def __init__(self):
        self.mp_maos = mp.solutions.hands
        self.mp_desenho = mp.solutions.drawing_utils
        self.estabilizador = EstabilizadorLado()   # o rótulo Left/Right não pisca mais
        # model_complexity=0 deixa a detecção bem mais rápida
        self.maos = self.mp_maos.Hands(
            max_num_hands=2,
            model_complexity=0,
            min_detection_confidence=0.7,
            min_tracking_confidence=0.6,
        )

    def processar(self, imagem, lado_invertido=False):
        pequena = cv2.resize(imagem, (640, 360))   # mais rápido; as coordenadas são normalizadas (0 a 1)
        imagem_rgb = cv2.cvtColor(pequena, cv2.COLOR_BGR2RGB)
        imagem_rgb.flags.writeable = False
        resultado = self.maos.process(imagem_rgb)

        todas_maos = []
        if resultado.multi_hand_landmarks:
            for lado_mao, marcacao_maos in zip(resultado.multi_handedness, resultado.multi_hand_landmarks):
                coordenadas = []
                for marcacao in marcacao_maos.landmark:
                    coordenadas.append((int(marcacao.x * RESOLUCAO_X),
                                        int(marcacao.y * RESOLUCAO_Y),
                                        int(marcacao.z * RESOLUCAO_X)))

                lado = lado_mao.classification[0].label
                if lado_invertido:
                    lado = "Right" if lado == "Left" else "Left"

                todas_maos.append({"coordenadas": coordenadas, "lado": lado})
                self.mp_desenho.draw_landmarks(imagem, marcacao_maos, self.mp_maos.HAND_CONNECTIONS)

        self.estabilizador.estabilizar(todas_maos, time.time())
        return imagem, todas_maos