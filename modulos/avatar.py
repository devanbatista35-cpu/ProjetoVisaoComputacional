import os
import subprocess
import time
import cv2

from modulos.config import PASTA_VIDEOS, VIDEOS, RESOLUCAO_X, RESOLUCAO_Y

os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")
import pygame
import imageio_ffmpeg

PASTA_AUDIO = os.path.join(PASTA_VIDEOS, "_audio")


def extrair_audio(caminho_video):
    """Extrai o audio do mp4 para .wav. Só faz isso uma vez: depois reaproveita o arquivo."""
    os.makedirs(PASTA_AUDIO, exist_ok=True)
    nome = os.path.splitext(os.path.basename(caminho_video))[0] + ".wav"
    caminho_wav = os.path.join(PASTA_AUDIO, nome)

    # já extraído e o video não mudou desde então
    if os.path.exists(caminho_wav) and os.path.getmtime(caminho_wav) >= os.path.getmtime(caminho_video):
        return caminho_wav

    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()  # ffmpeg que vem junto com o imageio-ffmpeg
    resultado = subprocess.run(
        [ffmpeg, "-y", "-i", caminho_video, "-vn", "-acodec", "pcm_s16le", "-ar", "44100", "-ac", "2", caminho_wav],
        capture_output=True,
    )
    if resultado.returncode != 0 or not os.path.exists(caminho_wav):
        return None  # video sem trilha de audio
    return caminho_wav


class Avatar:
    """Toca os videos mp4 do avatar (imagem pelo OpenCV, som pelo pygame) por cima da webcam."""

    def __init__(self):
        self.cap = None
        self.terminou = True    # True quando o video acabou (ou não existe)
        self.visivel = False
        self.ultimo = None      # último frame, mantido na tela depois que o video acaba
        self.fps = 30
        self.t0 = 0
        self.frame_atual = -1
        self.fim_falso = 0      # video ausente: finge que dura 2 s (para testar sem videos)
        self.som_atual = None
        self.sons = {}

        try:
            pygame.mixer.init()
            self._preparar_sons()
        except pygame.error as erro:
            print(f"Audio desativado: {erro}")

    def _preparar_sons(self):
        """Extrai e carrega o audio de todos os videos de uma vez (evita travar na hora de tocar)."""
        print("Preparando audios...")
        for nome, arquivo in VIDEOS.items():
            caminho = os.path.join(PASTA_VIDEOS, arquivo)
            if not os.path.exists(caminho):
                continue
            wav = extrair_audio(caminho)
            if wav:
                self.sons[nome] = pygame.mixer.Sound(wav)

    def tocar(self, nome):
        self.esconder()
        caminho = os.path.join(PASTA_VIDEOS, VIDEOS[nome])
        if not os.path.exists(caminho):
            print(f"Video nao encontrado: {caminho}")
            self.terminou = False
            self.fim_falso = time.time() + 2
            return

        self.cap = cv2.VideoCapture(caminho)
        self.fps = self.cap.get(cv2.CAP_PROP_FPS) or 30
        self.frame_atual = -1
        self.terminou = False
        self.visivel = True
        self.t0 = time.time()

        som = self.sons.get(nome)
        if som is not None:
            som.play()
            self.som_atual = som

    def esconder(self):
        if self.som_atual is not None:
            self.som_atual.stop()
            self.som_atual = None
        if self.cap is not None:
            self.cap.release()
            self.cap = None
        self.visivel = False
        self.terminou = True
        self.ultimo = None

    def _proximo_frame(self):
        if self.cap is None:
            # video ausente: termina depois do tempo falso
            if not self.terminou and time.time() >= self.fim_falso:
                self.terminou = True
            return None
        if not self.visivel:
            return None

        if not self.terminou:
            # o video segue o relógio (e não o ritmo do loop), assim fica no mesmo tempo do áudio
            alvo = int((time.time() - self.t0) * self.fps)
            if alvo > self.frame_atual:
                ok = True
                while self.frame_atual < alvo - 1 and ok:   # pula os frames atrasados
                    ok = self.cap.grab()
                    self.frame_atual += 1
                if ok:
                    ok, frame = self.cap.read()
                    self.frame_atual += 1
                if ok:
                    self.ultimo = frame
                else:
                    self.terminou = True
        return self.ultimo

    def desenhar(self, imagem, largura_max=320):
        """Sobrepõe o frame atual no canto superior direito da imagem."""
        frame = self._proximo_frame()
        if frame is None:
            return imagem
        h0, w0 = frame.shape[:2]
        escala = min(largura_max / w0, (RESOLUCAO_Y - 40) / h0)
        w, h = int(w0 * escala), int(h0 * escala)
        imagem[20:20 + h, RESOLUCAO_X - w - 20:RESOLUCAO_X - 20] = cv2.resize(frame, (w, h))
        return imagem
