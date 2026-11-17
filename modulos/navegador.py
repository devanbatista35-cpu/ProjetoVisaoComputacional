import os
import webbrowser

import cv2
import numpy as np
from pynput.mouse import Controller as Mouse, Button

from modulos.config import (RESOLUCAO_X, RESOLUCAO_Y, CHROME_PATH, NAV_MARGEM, SCROLL_PASSO_PIXELS, SCROLL_INVERTIDO,
                     DESLIZE_DISTANCIA, DESLIZE_TEMPO, BRANCO, VERDE, VERMELHO)
from modulos.filtros import OneEuro, Rolagem
from modulos.gestos import (tamanho_mao, distancia_polegar_indicador, DetectorDeslize, EstadoDedos, GestoEstavel)
from modulos.ui import escreve_centro

AMARELO = (0, 255, 255)
URL_INICIAL = "https://www.google.com"
TEMPO_INICIO = 1.5        # s: ignora o deslize no começo (as mãos ainda estão se mexendo)
TEMPO_PARADO_NO_CLIQUE = 0.25   # s: o cursor fica parado no começo da pinça (o clique não "escorrega")
POSE_ROLAGEM = (True, True, False, False)   # indicador e médio esticados, anelar e mindinho dobrados


class Navegador:
    """Abre o navegador e deixa você usá-lo só com as mãos.

    - MÃO DIREITA = mouse: mexer a mão move o cursor; pinça (polegar + indicador) clica;
      segurar a pinça e mover arrasta.
    - MÃO ESQUERDA = teclado virtual (existe só neste modo): o indicador dentro da "zona do teclado"
      (retângulo azul claro na câmera) escolhe a tecla e a pinça digita. O que você digita vai para a janela
      que estiver em foco: clique no Chrome antes de escrever.
    - MÃO ESQUERDA com 2 DEDOS (indicador e médio) subindo ou descendo = ROLA a página (o teclado fica em
      pausa enquanto você rola). A rolagem vai para a janela que estiver sob o cursor.
    - Passar a mão ABERTA da direita para a esquerda volta para a tela principal.

    Enquanto este modo está ativo a janela do programa vira uma janelinha no canto (sempre por cima):
    o TECLADO fica à ESQUERDA e a imagem da câmera à DIREITA, sem um cobrir o outro.
    """

    janela_compacta = True

    def __init__(self, teclado, tamanho_tela):
        self.teclado = teclado
        self.larg_tela, self.alt_tela = tamanho_tela
        self.mouse = Mouse()
        self.chrome_aberto = False
        self.deslize = DetectorDeslize(DESLIZE_DISTANCIA * RESOLUCAO_X, DESLIZE_TEMPO, sentido=-1)
        self.t_inicio = 0
        self.dedos_rolagem = EstadoDedos()               # estado dos dedos da mão esquerda (com memória)
        self.gesto_rolagem = GestoEstavel(0.2, 0.15)     # os 2 dedos precisam ficar estáveis por 0,2 s
        self.rolagem = Rolagem(SCROLL_PASSO_PIXELS, SCROLL_INVERTIDO)
        self.rolando = False
        self.pos_rolagem = None                          # (x, y) da mão que rola, para o desenho
        self.ultimo_passo = (0, 0)                       # (quando, sentido) do último passo de rolagem
        self._zerar_mouse()

    def _zerar_mouse(self):
        self.filtro_x = OneEuro(1.0, 0.05)
        self.filtro_y = OneEuro(1.0, 0.05)
        self.pinca = False
        self.t_pinca = 0
        self.pressionado = False
        self.ponteiro = None    # (x, y) suavizado na imagem da câmera

    def iniciar(self, agora):
        self.t_inicio = agora
        self.deslize.resetar()
        self.dedos_rolagem.resetar()
        self.gesto_rolagem.resetar()
        self.rolagem.resetar()
        self.rolando = False
        self._zerar_mouse()
        self._abrir_navegador()

    def cancelar(self):
        self._soltar()

    def _abrir_navegador(self):
        if self.chrome_aberto:      # só abre uma vez (abrir de novo criaria outra janela do Chrome)
            return
        self.chrome_aberto = True
        try:
            if hasattr(os, "startfile") and os.path.exists(CHROME_PATH):
                os.startfile(CHROME_PATH)
            else:
                webbrowser.open(URL_INICIAL)    # Chrome não encontrado: abre o navegador padrão
        except Exception as erro:
            print(f"Nao consegui abrir o navegador: {erro}")

    # ------------------------------------------------------------------
    def _escolher_maos(self, todas_maos):
        """Retorna (mao_do_teclado, mao_do_mouse)."""
        if len(todas_maos) >= 2:
            esquerda, direita = sorted(todas_maos[:2], key=lambda m: m["coordenadas"][0][0])
            return esquerda, direita
        if len(todas_maos) == 1:
            mao = todas_maos[0]
            return (mao, None) if mao["lado"] == "Left" else (None, mao)
        return None, None

    def atualizar(self, imagem, todas_maos, agora):
        """Retorna (tela, finalizou). A tela tem o teclado à ESQUERDA e a câmera à DIREITA, sem sobreposição."""
        mao_teclado, mao_mouse = self._escolher_maos(todas_maos)

        self.rolando = self._atualizar_rolagem(mao_teclado, agora)
        self.teclado.atualizar(None if self.rolando else mao_teclado, agora)   # rolando: teclado em pausa
        self._atualizar_mouse(mao_mouse, agora)

        self.teclado.desenhar_zona(imagem)      # na câmera: zona do teclado e posição do dedo
        self._desenhar_interface(imagem, agora) # na câmera: zona e ponteiro do mouse, rolagem, dicas
        tela = self._montar(self.teclado.renderizar(agora), imagem)

        if self.deslize.atualizar(todas_maos, agora) and agora - self.t_inicio > TEMPO_INICIO:
            return tela, True
        return tela, False

    @staticmethod
    def _montar(painel_teclado, imagem):
        """Teclado | câmera, lado a lado, com a mesma altura."""
        altura = painel_teclado.shape[0]
        largura_camera = int(round(imagem.shape[1] * altura / imagem.shape[0]))
        camera = cv2.resize(imagem, (largura_camera, altura))
        tela = np.hstack([painel_teclado, camera])
        cv2.line(tela, (painel_teclado.shape[1], 0), (painel_teclado.shape[1], altura), (0, 0, 0), 4)
        return tela

    # ------------------------------------------------------------------
    def _atualizar_rolagem(self, mao, agora):
        """Mão esquerda com 2 dedos subindo/descendo = rolar a página. Retorna True enquanto está rolando."""
        if mao is None:
            self.dedos_rolagem.resetar()
            self.gesto_rolagem.resetar()
            self.rolagem.resetar()
            return False

        pose = self.dedos_rolagem.atualizar(mao)
        if self.gesto_rolagem.atualizar(pose, agora) != POSE_ROLAGEM:
            self.rolagem.resetar()
            return False

        x, y, _ = mao["coordenadas"][9]               # centro da palma: acompanha a mão toda
        self.pos_rolagem = (x, y)
        if pose != POSE_ROLAGEM:                       # falha rápida da detecção: mantém, sem rolar neste frame
            return True
        passos = self.rolagem.atualizar(y, agora)
        if passos:
            self.mouse.scroll(0, passos)               # positivo = rola para cima
            self.ultimo_passo = (agora, 1 if passos > 0 else -1)
        return True

    # ------------------------------------------------------------------
    def _atualizar_mouse(self, mao, agora):
        if mao is None:
            self._soltar()
            self.pinca = False
            return

        x, y, _ = mao["coordenadas"][5]     # base do indicador: não se mexe quando você faz a pinça
        sx = self.filtro_x.filtrar(x, agora)
        sy = self.filtro_y.filtrar(y, agora)
        self.ponteiro = (sx, sy)

        tam = tamanho_mao(mao)
        dist = distancia_polegar_indicador(mao)
        anterior = self.pinca
        self.pinca = dist < (0.45 * tam if self.pinca else 0.28 * tam)   # histerese

        if self.pinca and not anterior:
            self.t_pinca = agora
            self.mouse.press(Button.left)
            self.pressionado = True
        elif not self.pinca and anterior:
            self._soltar()

        if self.pinca and agora - self.t_pinca < TEMPO_PARADO_NO_CLIQUE:
            return      # começo da pinça: cursor parado

        # a câmera inteira (menos a margem) vira a tela inteira: não precisa esticar o braço
        m = NAV_MARGEM
        nx = min(max((sx / RESOLUCAO_X - m) / (1 - 2 * m), 0.0), 1.0)
        ny = min(max((sy / RESOLUCAO_Y - m) / (1 - 2 * m), 0.0), 1.0)
        self.mouse.position = (int(nx * (self.larg_tela - 1)), int(ny * (self.alt_tela - 1)))

    def _soltar(self):
        if self.pressionado:
            self.mouse.release(Button.left)
            self.pressionado = False

    # ------------------------------------------------------------------
    def _desenhar_interface(self, imagem, agora):
        m = NAV_MARGEM
        p1 = (int(m * RESOLUCAO_X), int(m * RESOLUCAO_Y))
        p2 = (int((1 - m) * RESOLUCAO_X), int((1 - m) * RESOLUCAO_Y))
        cv2.rectangle(imagem, p1, p2, AMARELO, 2)       # área da câmera que cobre a tela toda (mouse)
        cv2.putText(imagem, "MOUSE", (p2[0] - 130, p1[1] - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.8, AMARELO, 2)

        if self.ponteiro is not None:
            px, py = int(self.ponteiro[0]), int(self.ponteiro[1])
            cv2.circle(imagem, (px, py), 16, VERMELHO if self.pinca else VERDE, cv2.FILLED)
            cv2.circle(imagem, (px, py), 18, BRANCO, 2)

        if self.rolando and self.pos_rolagem is not None:    # indicador de rolagem junto da mão
            x, y = self.pos_rolagem
            cv2.putText(imagem, "ROLAGEM", (x - 70, y + 110), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 0, 0), 5)
            cv2.putText(imagem, "ROLAGEM", (x - 70, y + 110), cv2.FONT_HERSHEY_SIMPLEX, 1.0, VERDE, 2)
            quando, sentido = self.ultimo_passo
            if sentido and agora - quando < 0.4:             # seta no sentido em que a página está andando
                cv2.arrowedLine(imagem, (x, y - sentido * -60), (x, y - sentido * 60), VERDE, 8, tipLength=0.5)

        escreve_centro(imagem, "Dir: cursor | pinca = clique", 628, 0.9)
        escreve_centro(imagem, "Esq: 2 dedos subindo/descendo = rolar", 666, 0.9)
        escreve_centro(imagem, "Deslize a mao aberta p/ esquerda = voltar", 704, 0.9)