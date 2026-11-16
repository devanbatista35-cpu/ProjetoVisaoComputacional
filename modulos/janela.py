import os
import cv2

from modulos.config import RESOLUCAO_X, RESOLUCAO_Y, NAV_LARGURA, NAV_POSICAO
from modulos.ui import ajustar_a_tela, tamanho_tela


def _dpi_consciente():
    """No Windows com escala (125%, 150%...), faz o programa, o mouse e a tela usarem os mesmos pixels."""
    if os.name != "nt":
        return
    try:
        import ctypes
        try:
            ctypes.windll.shcore.SetProcessDpiAwareness(2)
        except Exception:
            ctypes.windll.user32.SetProcessDPIAware()
    except Exception:
        pass


class Janela:
    """Janela do programa. Três formas:

    - cheia:    tela cheia (padrão)
    - janela:   janela comum de 1280x720 (tecla F alterna)
    - compacta: janelinha no canto, SEMPRE POR CIMA, usada no modo navegador para não cobrir o Chrome
    """

    def __init__(self, nome="Imagem"):
        _dpi_consciente()
        self.nome = nome
        self.tela_larg, self.tela_alt = tamanho_tela()
        self.tela_cheia = True
        self.tipo = None
        self.nav_larg = NAV_LARGURA
        self.nav_alt = int(NAV_LARGURA * RESOLUCAO_Y / RESOLUCAO_X)
        cv2.namedWindow(nome, cv2.WINDOW_NORMAL)
        self._aplicar("cheia")

    def alternar_tela_cheia(self):
        self.tela_cheia = not self.tela_cheia

    def tamanho_exibicao(self):
        """Tamanho da tela onde a imagem é exibida (os modos usam para se adaptar)."""
        return (self.tela_larg, self.tela_alt) if self.tela_cheia else (RESOLUCAO_X, RESOLUCAO_Y)

    def mostrar(self, imagem, compacta=False, info=None):
        desejado = "compacta" if compacta else ("cheia" if self.tela_cheia else "janela")
        if desejado != self.tipo:
            self._aplicar(desejado)
        if desejado == "cheia":
            alvo = (self.tela_larg, self.tela_alt)
        elif desejado == "janela":
            alvo = (RESOLUCAO_X, RESOLUCAO_Y)
        else:
            alvo = (self.nav_larg, self.nav_alt)
        saida = ajustar_a_tela(imagem, *alvo)
        if info:
            cv2.putText(saida, info, (20, saida.shape[0] - 20), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
        cv2.imshow(self.nome, saida)

    # ------------------------------------------------------------------
    def _aplicar(self, tipo):
        nome = self.nome
        if tipo == "cheia":
            self._por_cima(False)
            cv2.setWindowProperty(nome, cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)
        else:
            cv2.setWindowProperty(nome, cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_NORMAL)
            if tipo == "janela":
                self._por_cima(False)
                cv2.resizeWindow(nome, RESOLUCAO_X, RESOLUCAO_Y)
            else:
                cv2.resizeWindow(nome, self.nav_larg, self.nav_alt)
                margem = 20
                x = margem if "esquerda" in NAV_POSICAO else self.tela_larg - self.nav_larg - margem
                y = margem if "cima" in NAV_POSICAO else self.tela_alt - self.nav_alt - 90   # 90 = barra de tarefas
                cv2.moveWindow(nome, x, y)
                self._por_cima(True)
        self.tipo = tipo

    def _por_cima(self, ligado):
        """Deixa a janela sempre por cima das outras (para não sumir atrás do Chrome)."""
        try:
            cv2.setWindowProperty(self.nome, getattr(cv2, "WND_PROP_TOPMOST", 5), 1 if ligado else 0)
        except Exception:
            pass
        if os.name == "nt":
            try:
                import ctypes
                hwnd = ctypes.windll.user32.FindWindowW(None, self.nome)
                if hwnd:
                    # HWND_TOPMOST = -1, HWND_NOTOPMOST = -2; flags: sem mover, sem redimensionar, sem roubar o foco
                    ctypes.windll.user32.SetWindowPos(hwnd, -1 if ligado else -2, 0, 0, 0, 0, 0x0001 | 0x0002 | 0x0010)
            except Exception:
                pass