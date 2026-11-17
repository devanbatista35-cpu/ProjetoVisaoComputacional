import cv2
import numpy as np
from collections import deque
from pynput.keyboard import Controller, Key

from modulos.config import BRANCO, PRETO, AZUL, VERMELHO, AZUL_CLARO, VERDE, TECLADO_ZONA
from modulos.gestos import dedos_levantados, tamanho_mao, distancia_polegar_indicador
from modulos.ui import imprime_botoes


class TecladoVirtual:
    """Teclado na tela controlado pela mão esquerda. Só existe no modo navegador.

    O teclado é desenhado num PAINEL PRÓPRIO (`renderizar`), e não por cima da imagem da câmera.
    Na câmera aparece um retângulo (a "zona do teclado"): o dedo indicador dentro dele escolhe a tecla,
    como se fosse um touchpad. O cursor aparece nos dois lados.

    - Pinça (polegar + indicador): digita a tecla
    - Pinça com os outros 3 dedos levantados: maiúscula
    - Só o mindinho levantado: apaga
    - Teclas especiais: ENT = Enter | <- = apagar | SP = espaço

    O que você digita é enviado para a janela que estiver em foco no computador.
    """

    TECLAS = [list("1234567890"),
              list("QWERTYUIOP"),
              list("ASDFGHJKL") + ["ENT"],
              list("ZXCVBNM,.") + [" "],
              ["<-", "/", ":", "-", "?", "@", "_", "=", "&", "+"]]
    ESPECIAIS = {"ENT": Key.enter, "<-": Key.backspace}
    OFFSET = 50          # margem do teclado dentro do painel
    TAM_TECLA = 70
    PASSO_TECLA = 80
    LARGURA = 900        # tamanho do painel do teclado
    ALTURA = 560
    FUNDO = (40, 40, 40)

    def __init__(self):
        self.texto = '>'
        self.controle = Controller()
        self.zona = TECLADO_ZONA          # onde o teclado "mora" na imagem da câmera (canto da primeira tecla)
        self.pinca_ativa = False
        self.hist_hover = deque(maxlen=3)   # teclas sob o dedo ANTES da pinça
        self.ultimo_clique = 0
        self.ultimo_apagar = 0
        self.flash = None                   # (linha, coluna, tempo) para animar o clique
        self.hover = None                   # tecla sob o dedo agora
        self.maiuscula = False
        self.dedo = None                    # (x, y) do indicador na imagem da câmera

    # ------------------------------------------------------------------ lógica
    def _tecla_sob_dedo(self, x, y):
        """(linha, coluna) da tecla sob o dedo, ou None. A área de acerto é a célula inteira."""
        zx, zy = self.zona
        if x < zx - 5 or y < zy - 5:
            return None
        coluna = (x - zx + 5) // self.PASSO_TECLA
        linha = (y - zy + 5) // self.PASSO_TECLA
        if 0 <= linha < len(self.TECLAS) and 0 <= coluna < len(self.TECLAS[linha]):
            return int(linha), int(coluna)
        return None

    def _apertar(self, tecla):
        self.controle.press(tecla)
        self.controle.release(tecla)

    def atualizar(self, mao, agora):
        """Atualiza o estado e digita. `mao` é a mão do teclado (ou None se ela não está na câmera)."""
        if mao is None:
            self.dedo, self.hover, self.maiuscula, self.pinca_ativa = None, None, False, False
            self.hist_hover.clear()
            return

        info_dedos = dedos_levantados(mao)
        ix, iy, _ = mao["coordenadas"][8]
        tam = tamanho_mao(mao)
        dist = distancia_polegar_indicador(mao)

        # pinça com histerese (evita oscilar entre ligado/desligado)
        anterior = self.pinca_ativa
        self.pinca_ativa = dist < (0.45 * tam if self.pinca_ativa else 0.28 * tam)

        hover = self._tecla_sob_dedo(ix, iy)
        if not self.pinca_ativa:
            self.hist_hover.append(hover)

        maiuscula = info_dedos[1:] == [True, True, True]

        # clique = momento em que a pinça fecha (usa a tecla de antes, pois o dedo se mexe ao pinçar)
        if self.pinca_ativa and not anterior and agora - self.ultimo_clique > 0.2:
            alvo = self.hist_hover[0] if (self.hist_hover and self.hist_hover[0] is not None) else hover
            if alvo is not None:
                linha, coluna = alvo
                letra = self.TECLAS[linha][coluna]
                if letra in self.ESPECIAIS:
                    self._apertar(self.ESPECIAIS[letra])
                    if letra == "<-" and len(self.texto) > 1:
                        self.texto = self.texto[:-1]
                else:
                    letra = letra if maiuscula else letra.lower()
                    self.texto += letra
                    self._apertar(letra)
                self.ultimo_clique = agora
                self.flash = (linha, coluna, agora)

        # apagar (sem travar o programa)
        if info_dedos == [False, False, False, True] and len(self.texto) > 1 and agora - self.ultimo_apagar > 0.15:
            self.texto = self.texto[:-1]
            self._apertar(Key.backspace)
            self.ultimo_apagar = agora

        self.dedo, self.hover, self.maiuscula = (ix, iy), hover, maiuscula

    # ------------------------------------------------------------------ desenho
    @staticmethod
    def _rotulo(letra, maiuscula):
        if letra == " ":
            return "SP"
        if len(letra) == 1:
            return letra if maiuscula else letra.lower()
        return letra

    def renderizar(self, agora):
        """Desenha o teclado num painel próprio (LARGURA x ALTURA) e o devolve."""
        painel = np.full((self.ALTURA, self.LARGURA, 3), self.FUNDO, np.uint8)
        for i_linha, linha in enumerate(self.TECLAS):
            for i_col, letra in enumerate(linha):
                cor = BRANCO
                if self.hover == (i_linha, i_col) and not self.pinca_ativa:
                    cor = VERDE
                if self.flash and self.flash[0] == i_linha and self.flash[1] == i_col and agora - self.flash[2] < 0.2:
                    cor = AZUL_CLARO
                imprime_botoes(
                    painel,
                    (self.OFFSET + i_col * self.PASSO_TECLA, self.OFFSET + i_linha * self.PASSO_TECLA),
                    self._rotulo(letra, self.maiuscula),
                    tamanho=self.TAM_TECLA,
                    cor_retangulo=cor,
                )

        cv2.rectangle(painel, (self.OFFSET, 450), (830, 500), BRANCO, cv2.FILLED)
        cv2.rectangle(painel, (self.OFFSET, 450), (830, 500), AZUL, 1)
        cv2.putText(painel, self.texto[-40:], (self.OFFSET + 5, 485), cv2.FONT_HERSHEY_COMPLEX, 1, PRETO, 2)
        cv2.putText(painel, "Pinca = digitar | mindinho = apagar", (self.OFFSET, 535),
                    cv2.FONT_HERSHEY_COMPLEX, 0.7, BRANCO, 2)

        if self.dedo is not None:                        # o dedo, na posição equivalente do painel
            cx = self.OFFSET + (self.dedo[0] - self.zona[0])
            cy = self.OFFSET + (self.dedo[1] - self.zona[1])
            if 0 <= cx < self.LARGURA and 0 <= cy < self.ALTURA:
                cv2.circle(painel, (cx, cy), 12, VERMELHO if self.pinca_ativa else AZUL, cv2.FILLED)
                cv2.circle(painel, (cx, cy), 14, BRANCO, 2)
        return painel

    def desenhar_zona(self, imagem):
        """Na imagem da câmera: o retângulo da zona do teclado e a posição do dedo."""
        zx, zy = self.zona
        p1 = (zx - 5, zy - 5)
        p2 = (zx - 5 + len(self.TECLAS[0]) * self.PASSO_TECLA, zy - 5 + len(self.TECLAS) * self.PASSO_TECLA)
        cv2.rectangle(imagem, p1, p2, AZUL_CLARO, 3)
        cv2.putText(imagem, "ZONA DO TECLADO", (p1[0] + 8, p1[1] - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.8, PRETO, 4)
        cv2.putText(imagem, "ZONA DO TECLADO", (p1[0] + 8, p1[1] - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.8, AZUL_CLARO, 2)
        if self.dedo is not None:
            cv2.circle(imagem, self.dedo, 14, VERMELHO if self.pinca_ativa else AZUL, cv2.FILLED)
            cv2.circle(imagem, self.dedo, 16, BRANCO, 2)

    def salvar(self, caminho="texto_digitado.txt"):
        with open(caminho, "w") as arquivo:
            arquivo.write(self.texto)