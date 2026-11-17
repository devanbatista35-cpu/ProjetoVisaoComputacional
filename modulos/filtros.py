import math


class _PassaBaixa:
    def __init__(self):
        self.y = None

    def aplicar(self, valor, alpha):
        self.y = valor if self.y is None else alpha * valor + (1 - alpha) * self.y
        return self.y


class OneEuro:
    """Filtro 1-Euro: suaviza BASTANTE quando a mão está quase parada (tira o tremor)
    e quase NÃO atrasa quando ela se move rápido. Funciona melhor que a média simples.

    min_cutoff: menor = mais liso parado (e mais atraso). beta: maior = menos atraso em movimento.
    """

    def __init__(self, min_cutoff=1.5, beta=0.03, d_cutoff=1.0):
        self.min_cutoff = min_cutoff
        self.beta = beta
        self.d_cutoff = d_cutoff
        self.x = _PassaBaixa()
        self.dx = _PassaBaixa()
        self.t_anterior = None

    @staticmethod
    def _alpha(cutoff, dt):
        tau = 1.0 / (2 * math.pi * cutoff)
        return 1.0 / (1.0 + tau / dt)

    def filtrar(self, valor, t):
        if self.t_anterior is None:
            self.t_anterior = t
            self.x.y = valor
            self.dx.y = 0.0
            return valor
        dt = max(t - self.t_anterior, 1 / 120)
        self.t_anterior = t
        velocidade = (valor - self.x.y) / dt
        velocidade = self.dx.aplicar(velocidade, self._alpha(self.d_cutoff, dt))
        cutoff = self.min_cutoff + self.beta * abs(velocidade)
        return self.x.aplicar(valor, self._alpha(cutoff, dt))


class Rolagem:
    """Converte o movimento vertical da mão em "cliques" da roda do mouse.

    atualizar(y, agora) recebe a altura da mão (pixels da câmera, y cresce para baixo) e devolve o número
    de passos a rolar neste frame: POSITIVO = rolar para cima (a página sobe), NEGATIVO = para baixo.
    Mão subindo  -> página sobe | mão descendo -> página desce (com invertido=True, o contrário).

    passo_pixels: quanto a mão precisa andar para gerar 1 passo (MENOR = rola mais rápido).
    """

    PASSOS_MAX = 5      # limite por frame (evita um pulo enorme se a detecção der um salto)

    def __init__(self, passo_pixels=30, invertido=False):
        self.passo = max(passo_pixels, 1)
        self.sinal = -1 if invertido else 1
        self.filtro = OneEuro(1.0, 0.02)    # tira o tremor da mão parada sem atrasar o movimento
        self.resetar()

    def resetar(self):
        self.filtro = OneEuro(1.0, 0.02)
        self.y_anterior = None
        self.acumulado = 0.0

    def atualizar(self, y, agora):
        y = self.filtro.filtrar(y, agora)
        if self.y_anterior is None:
            self.y_anterior = y
            return 0
        delta = (self.y_anterior - y) * self.sinal      # mão subindo => y diminui => delta positivo
        self.y_anterior = y
        self.acumulado += delta
        passos = int(self.acumulado / self.passo)       # int() corta em direção ao zero
        if passos:
            self.acumulado -= passos * self.passo
            passos = max(-self.PASSOS_MAX, min(self.PASSOS_MAX, passos))
        return passos