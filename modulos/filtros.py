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
