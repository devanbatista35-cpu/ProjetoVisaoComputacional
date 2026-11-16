import cv2
from collections import deque
from pynput.keyboard import Controller, Key

from modulos.config import BRANCO, PRETO, AZUL, VERDE, VERMELHO, AZUL_CLARO
from modulos.gestos import dedos_levantados, tamanho_mao, distancia_polegar_indicador
from modulos.ui import imprime_botoes


class TecladoVirtual:
    """Teclado na tela controlado pela mão esquerda.

    - Mover o indicador: escolhe a tecla
    - Pinça (polegar + indicador): clica
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
    OFFSET = 50
    TAM_TECLA = 70
    PASSO_TECLA = 80

    def __init__(self):
        self.texto = '>'
        self.controle = Controller()
        self.pinca_ativa = False
        self.hist_hover = deque(maxlen=3)   # teclas sob o dedo ANTES da pinça
        self.ultimo_clique = 0
        self.ultimo_apagar = 0
        self.flash = None                   # (linha, coluna, tempo) para animar o clique

    def _tecla_sob_dedo(self, x, y):
        """(linha, coluna) da tecla sob o dedo, ou None. A área de acerto é a célula inteira."""
        if x < self.OFFSET - 5 or y < self.OFFSET - 5:
            return None
        coluna = (x - self.OFFSET + 5) // self.PASSO_TECLA
        linha = (y - self.OFFSET + 5) // self.PASSO_TECLA
        if 0 <= linha < len(self.TECLAS) and 0 <= coluna < len(self.TECLAS[linha]):
            return int(linha), int(coluna)
        return None

    def _apertar(self, tecla):
        self.controle.press(tecla)
        self.controle.release(tecla)

    def atualizar(self, imagem, mao, agora):
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

        self._desenhar(imagem, hover, maiuscula, agora)
        cv2.circle(imagem, (ix, iy), 9, VERMELHO if self.pinca_ativa else AZUL, cv2.FILLED)
        return imagem

    def desenhar(self, imagem, agora):
        """Só mostra o teclado (sem mão para controlá-lo)."""
        self._desenhar(imagem, None, False, agora)

    @staticmethod
    def _rotulo(letra, maiuscula):
        if letra == " ":
            return "SP"
        if len(letra) == 1:
            return letra if maiuscula else letra.lower()
        return letra

    def _desenhar(self, imagem, hover, maiuscula, agora):
        for i_linha, linha in enumerate(self.TECLAS):
            for i_col, letra in enumerate(linha):
                cor = BRANCO
                if hover == (i_linha, i_col) and not self.pinca_ativa:
                    cor = VERDE
                if self.flash and self.flash[0] == i_linha and self.flash[1] == i_col and agora - self.flash[2] < 0.2:
                    cor = AZUL_CLARO
                imprime_botoes(
                    imagem,
                    (self.OFFSET + i_col * self.PASSO_TECLA, self.OFFSET + i_linha * self.PASSO_TECLA),
                    self._rotulo(letra, maiuscula),
                    tamanho=self.TAM_TECLA,
                    cor_retangulo=cor,
                )

        cv2.rectangle(imagem, (self.OFFSET, 450), (830, 500), BRANCO, cv2.FILLED)
        cv2.rectangle(imagem, (self.OFFSET, 450), (830, 500), AZUL, 1)
        cv2.putText(imagem, self.texto[-40:], (self.OFFSET, 480), cv2.FONT_HERSHEY_COMPLEX, 1, PRETO, 2)
        cv2.putText(imagem, "Pinca = clicar | mindinho = apagar", (self.OFFSET, 530),
                    cv2.FONT_HERSHEY_COMPLEX, 0.7, BRANCO, 2)

    def salvar(self, caminho="texto_digitado.txt"):
        with open(caminho, "w") as arquivo:
            arquivo.write(self.texto)