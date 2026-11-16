"""Reconhecimento de gestos. Cada mão é um dict: {"coordenadas": [(x, y, z) x21], "lado": "Left"/"Right"}."""
import math


def dedos_levantados(mao):
    """[indicador, médio, anelar, mindinho] -> True se levantado."""
    return [mao["coordenadas"][ponta][1] < mao["coordenadas"][ponta - 2][1] for ponta in (8, 12, 16, 20)]


def tamanho_mao(mao):
    """Distância pulso -> base do dedo médio. Serve para normalizar distâncias."""
    x0, y0, _ = mao["coordenadas"][0]
    x9, y9, _ = mao["coordenadas"][9]
    return max(math.hypot(x9 - x0, y9 - y0), 1)


def distancia_polegar_indicador(mao):
    x1, y1, _ = mao["coordenadas"][4]
    x2, y2, _ = mao["coordenadas"][8]
    return math.hypot(x2 - x1, y2 - y1)


def razao_dedo(mao, ponta):
    """Quão esticado está o dedo: distância pulso->ponta dividida por pulso->articulação (em 3D).
    ~1.4 ou mais = esticado, ~0.7 ou menos = dobrado. Não depende da mão estar de pé ou inclinada."""
    c = mao["coordenadas"]
    pulso = c[0]
    d_ponta = math.dist(pulso, c[ponta])
    d_junta = math.dist(pulso, c[ponta - 2])
    return d_ponta / max(d_junta, 1)


def mao_aberta(mao):
    return dedos_levantados(mao) == [True, True, True, True]


def gesto_ok(mao):
    """Polegar e indicador se tocando, outros 3 dedos levantados."""
    d = dedos_levantados(mao)
    return distancia_polegar_indicador(mao) < 0.3 * tamanho_mao(mao) and d[1:] == [True, True, True]


def alguma_ok(lista_maos):
    return any(gesto_ok(m) for m in lista_maos)


def gesto_joinha(mao):
    """Thumbs up: 4 dedos fechados e polegar apontando para cima."""
    if dedos_levantados(mao) != [False, False, False, False]:
        return False
    c = mao["coordenadas"]
    tam = tamanho_mao(mao)
    ponta, articulacao, base = c[4], c[3], c[2]
    polegar_para_cima = ponta[1] < articulacao[1] < base[1]
    bem_acima_dos_dedos = ponta[1] < c[5][1] - 0.3 * tam  # acima da base do indicador
    return polegar_para_cima and bem_acima_dos_dedos


def mao_fechada(mao):
    """Punho fechado (e não um joinha)."""
    return dedos_levantados(mao) == [False, False, False, False] and not gesto_joinha(mao)


def gesto_rock(mao):
    """Sinal de rock: indicador e mindinho esticados, médio e anelar dobrados (o polegar não importa).
    Usa a razão de extensão dos dedos, então funciona com a mão inclinada."""
    return (razao_dedo(mao, 8) > 1.2 and razao_dedo(mao, 20) > 1.2
            and razao_dedo(mao, 12) < 1.15 and razao_dedo(mao, 16) < 1.15)


def gesto_quatro_dedos(mao):
    """4 dedos esticados (indicador, médio, anelar e mindinho); o polegar não importa."""
    return all(razao_dedo(mao, ponta) > 1.2 for ponta in (8, 12, 16, 20))


def gesto_jogada(mao):
    """Pedra, papel ou tesoura. None se não for nenhum."""
    d = dedos_levantados(mao)
    if d == [False, False, False, False]:
        return "pedra"
    if d == [True, True, True, True]:
        return "papel"
    if d == [True, True, False, False]:
        return "tesoura"
    return None


class Retencao:
    """Só confirma uma condição depois que ela for mantida por `tempo` segundos."""

    def __init__(self, tempo=0.4):
        self.tempo = tempo
        self.desde = None

    def atualizar(self, condicao, agora):
        if condicao:
            if self.desde is None:
                self.desde = agora
            return agora - self.desde >= self.tempo
        self.desde = None
        return False

    def progresso(self, agora):
        if self.desde is None:
            return 0.0
        return min((agora - self.desde) / self.tempo, 1.0)

    def resetar(self):
        self.desde = None


class DetectorDeslize:
    """Detecta uma mão ABERTA (4 dedos) passando rápido pela imagem.

    sentido=-1: da direita para a esquerda da tela. O vídeo é espelhado, então é o mesmo
    movimento que você faz: da SUA direita para a SUA esquerda.
    Funciona com qualquer mão (cada mão é acompanhada por uma "trilha").
    """

    def __init__(self, distancia_min=380, janela=0.7, sentido=-1):
        self.distancia_min = distancia_min   # pixels que a mão precisa percorrer...
        self.janela = janela                 # ...em no máximo esse tempo (segundos)
        self.sentido = sentido
        self.trilhas = []

    def resetar(self):
        self.trilhas = []

    def atualizar(self, maos, agora):
        livres = list(self.trilhas)
        for mao in maos:
            x, y, _ = mao["coordenadas"][9]          # centro da palma
            trilha = min(livres, key=lambda t: math.hypot(t["x"] - x, t["y"] - y), default=None)
            if trilha is not None and math.hypot(trilha["x"] - x, trilha["y"] - y) < 300:
                livres.remove(trilha)
            else:
                trilha = {"hist": []}
                self.trilhas.append(trilha)
            trilha["x"], trilha["y"], trilha["t"] = x, y, agora
            trilha["hist"].append((agora, x, y, gesto_quatro_dedos(mao)))
            trilha["hist"] = [h for h in trilha["hist"] if agora - h[0] <= self.janela]

        self.trilhas = [t for t in self.trilhas if agora - t["t"] <= 0.3]   # mão sumiu: descarta

        for trilha in self.trilhas:
            if self._deslizou(trilha["hist"]):
                self.resetar()
                return True
        return False

    def _deslizou(self, hist):
        if not hist or not hist[-1][3]:
            return False                              # tem que terminar com a mão ABERTA (não o dedo desenhando)

        # trecho mais recente em que a mão esteve aberta (tolera uma falha isolada na detecção)
        inicio = len(hist) - 1
        while inicio > 0:
            if hist[inicio - 1][3]:
                inicio -= 1
            elif inicio >= 2 and hist[inicio - 2][3]:
                inicio -= 2
            else:
                break
        trecho = hist[inicio:]
        if len(trecho) < 4:
            return False

        dx = trecho[-1][1] - trecho[0][1]
        dy = trecho[-1][2] - trecho[0][2]
        return dx * self.sentido >= self.distancia_min and abs(dy) < 0.6 * abs(dx)