import cv2
import numpy as np

from modulos.config import (RESOLUCAO_X, RESOLUCAO_Y, PAINEL_W, QUADRO_TELA_DIVIDIDA, ESPESSURA_PINCEL,
                    SUAVIZACAO_PARADO, SUAVIZACAO_VELOCIDADE,
                    BRANCO, PRETO, AZUL, VERDE, VERMELHO, TEMPO_CONFIRMACAO, TEMPO_TIMEOUT,
                    DESLIZE_DISTANCIA, DESLIZE_TEMPO)
from modulos.filtros import OneEuro
from modulos.gestos import dedos_levantados, alguma_ok, razao_dedo, DetectorDeslize, Retencao
from modulos.ui import escreve_centro, desenhar_progresso

LARGURA_BASE = 1280          # largura interna da tela montada (depois ela é ampliada para o monitor)
BARRA_H = 70
AMARELO = (0, 255, 255)
CINZA = (40, 40, 40)
CORES = [(AZUL, "1 dedo"), (VERDE, "2 dedos"), (VERMELHO, "3 dedos"), (BRANCO, "4 = borracha")]

TOLERANCIA_MAO_PERDIDA = 0.3   # s: a mão some por um instante e o traço continua de onde parou
TEMPO_PEN = 0.12               # s: tolerância de falha na detecção do gesto de desenhar


class Quadro:
    """Quadro de desenho: câmera de um lado, quadro branco do outro, numa janela só.

    - Com duas mãos: a mão da DIREITA da tela desenha (indicador esticado)
      e a da ESQUERDA escolhe a cor (1-4 dedos). Punho segurado por 0,8 s limpa tudo.
    - Com uma mão só: ela desenha com a cor atual.
    - Passar a mão ABERTA rápido da direita para a esquerda (como virar a página) volta à tela principal.
    - O retângulo amarelo na câmera é a área que corresponde ao quadro.
    """

    def __init__(self, avatar):
        self.avatar = avatar
        self.img = None                                  # criado no primeiro frame de desenho
        self.cor = AZUL
        self.espessura = ESPESSURA_PINCEL
        self.estado = None                               # "confirmando" | "desenhando"
        self.t_inicio = 0
        self.tamanho_saida = (RESOLUCAO_X, RESOLUCAO_Y)  # tamanho da tela de exibição (o main atualiza)
        self.ok = Retencao(TEMPO_CONFIRMACAO, tolerancia=0.25)   # tolera falhas rápidas na leitura
        self.limpar = Retencao(0.8)
        self.deslize = DetectorDeslize(DESLIZE_DISTANCIA * RESOLUCAO_X, DESLIZE_TEMPO, sentido=-1)
        self.t_desenho = 0                               # quando o desenho começou
        self.ultimo_pulso = None                         # (x, y, tempo) do pulso da mão que desenha
        self._resetar_traco()

    def _resetar_traco(self):
        self.filtro_x = OneEuro(SUAVIZACAO_PARADO, SUAVIZACAO_VELOCIDADE)
        self.filtro_y = OneEuro(SUAVIZACAO_PARADO, SUAVIZACAO_VELOCIDADE)
        self.anterior = None     # último ponto desenhado no quadro
        self.ultimo_pen = 0      # última vez que o gesto de desenhar foi confirmado
        self.pen_bruto = False
        self.pen_conta = 0
        self.ultima_mao = 0      # última vez que a mão que desenha foi vista

    def mudar_espessura(self, delta):
        self.espessura = max(2, min(40, self.espessura + delta))

    def _layout(self):
        """Tamanho dos painéis, zona da câmera que vira o quadro e posição da câmera no painel."""
        if QUADRO_TELA_DIVIDIDA:
            largura_s, altura_s = self.tamanho_saida
            total_h = int(round(LARGURA_BASE * altura_s / largura_s))
            pw = LARGURA_BASE // 2
            ph = total_h - BARRA_H
        else:
            pw = PAINEL_W
            ph = int(RESOLUCAO_Y * PAINEL_W / RESOLUCAO_X)

        # zona da câmera com o MESMO formato do quadro (o desenho não sai deformado)
        zh = RESOLUCAO_Y
        zw = int(round(zh * pw / ph))
        if zw > RESOLUCAO_X:
            zw = RESOLUCAO_X
            zh = int(round(zw * ph / pw))

        esc_cam = min(pw / RESOLUCAO_X, ph / RESOLUCAO_Y)   # câmera inteira dentro do painel esquerdo
        cam_w, cam_h = int(RESOLUCAO_X * esc_cam), int(RESOLUCAO_Y * esc_cam)
        return {
            "pw": pw, "ph": ph,
            "zx0": (RESOLUCAO_X - zw) // 2, "zy0": (RESOLUCAO_Y - zh) // 2, "zw": zw, "zh": zh,
            "esc_zona": pw / zw,
            "esc_cam": esc_cam, "cam_w": cam_w, "cam_h": cam_h,
            "off_x": (pw - cam_w) // 2, "off_y": (ph - cam_h) // 2,
        }

    def iniciar(self, agora):
        self.avatar.tocar("pergunta_quadro")
        self.estado = "confirmando"
        self.t_inicio = agora
        self.ok.resetar()
        self.limpar.resetar()
        self.deslize.resetar()
        self.ultimo_pulso = None
        self._resetar_traco()

    def _escolher_maos(self, todas_maos, agora):
        """Retorna (mao_que_desenha, mao_da_cor)."""
        if len(todas_maos) >= 2:
            # pela posição na tela (mais confiável que o rótulo Left/Right)
            esquerda, direita = sorted(todas_maos[:2], key=lambda m: m["coordenadas"][0][0])
            return direita, esquerda

        if len(todas_maos) == 1:
            mao = todas_maos[0]
            if self.ultimo_pulso is not None:
                x, y, t = self.ultimo_pulso
                dt = agora - t
                if dt < 1.0:
                    px, py, _ = mao["coordenadas"][0]
                    distancia = ((px - x) ** 2 + (py - y) ** 2) ** 0.5
                    if distancia > 250 + 1200 * dt:
                        # é a mão da cor: a que desenha sumiu por um instante. Ignora (senão riscaria o quadro).
                        return None, None
            return mao, None
        return None, None

    def atualizar(self, imagem, todas_maos, agora):
        """Retorna (imagem, finalizou)."""
        if self.estado == "confirmando":
            escreve_centro(imagem, "Abrir o quadro de desenho?", 600, 1.2)
            escreve_centro(imagem, "Faca OK para confirmar", 650, 1.0, VERDE)
            if self.ok.progresso(agora) > 0:
                desenhar_progresso(imagem, "OK detectado... segure", self.ok.progresso(agora))
            if self.ok.atualizar(alguma_ok(todas_maos), agora):
                self.avatar.esconder()
                self.estado = "desenhando"
                self.deslize.resetar()
                self.t_desenho = agora
                self.ultimo_pulso = None
                self._resetar_traco()
            elif agora - self.t_inicio > TEMPO_TIMEOUT:
                return imagem, True
            else:
                return imagem, False

        # ---------------- desenhando ----------------
        lay = self._layout()
        pw, ph = lay["pw"], lay["ph"]
        if self.img is None:
            self.img = np.full((ph, pw, 3), 255, np.uint8)
        elif self.img.shape[:2] != (ph, pw):            # trocou tela cheia <-> janela
            self.img = cv2.resize(self.img, (pw, ph))

        mao_desenha, mao_cor = self._escolher_maos(todas_maos, agora)

        # cor / limpar (só com as duas mãos visíveis)
        quer_limpar = False
        if mao_cor is not None:
            qtd = sum(dedos_levantados(mao_cor))
            if 1 <= qtd <= 4:
                self.cor = CORES[qtd - 1][0]
            quer_limpar = qtd == 0
        if self.limpar.atualizar(quer_limpar, agora):
            self.img = np.full((ph, pw, 3), 255, np.uint8)
            self.limpar.resetar()

        # passar a mão ABERTA da direita para a esquerda = voltar à tela principal
        deslizou = self.deslize.atualizar(todas_maos, agora)
        if deslizou and agora - self.t_desenho > 1.0:   # ignora no começo (as mãos ainda estão se mexendo)
            return imagem, True

        # traço
        cursor_cam, cursor_quadro, desenhando, fora_da_area = None, None, False, False
        if mao_desenha is not None:
            self.ultima_mao = agora
            self.ultimo_pulso = (*mao_desenha["coordenadas"][0][:2], agora)

            x, y, _ = mao_desenha["coordenadas"][8]
            sx = self.filtro_x.filtrar(x, agora)    # tira o tremor sem atrasar o movimento
            sy = self.filtro_y.filtrar(y, agora)

            bx_bruto = (sx - lay["zx0"]) * lay["esc_zona"]
            by_bruto = (sy - lay["zy0"]) * lay["esc_zona"]
            fora_da_area = not (0 <= bx_bruto < pw and 0 <= by_bruto < ph)
            bx = int(min(max(bx_bruto, 0), pw - 1))  # fora da área o cursor fica na borda (não some)
            by = int(min(max(by_bruto, 0), ph - 1))
            esp = int(self.espessura * (3 if self.cor == BRANCO else 1))
            cursor_cam, cursor_quadro = (sx, sy), (bx, by, esp)

            # gesto de desenhar: indicador esticado e médio dobrado (vale em qualquer inclinação da mão).
            # Histerese: para ligar exige mais do que para continuar ligado.
            r_indicador = razao_dedo(mao_desenha, 8)
            r_medio = razao_dedo(mao_desenha, 12)
            limite = 1.1 if self.pen_bruto else 1.25
            self.pen_bruto = r_indicador > limite and r_medio < 1.2
            self.pen_conta = self.pen_conta + 1 if self.pen_bruto else 0
            if self.pen_conta >= 2:                  # 2 frames seguidos: evita pontinhos soltos
                self.ultimo_pen = agora
            desenhando = agora - self.ultimo_pen < TEMPO_PEN

            if desenhando:
                if self.anterior is None:
                    cv2.circle(self.img, (bx, by), max(esp // 2, 1), self.cor, cv2.FILLED)
                else:
                    cv2.line(self.img, self.anterior, (bx, by), self.cor, esp)
                self.anterior = (bx, by)
            else:
                self.anterior = None
        elif agora - self.ultima_mao > TOLERANCIA_MAO_PERDIDA:
            self._resetar_traco()   # a mão sumiu de vez: recomeça limpo (não liga pontos distantes)

        return self._montar_tela(imagem, lay, cursor_cam, cursor_quadro, desenhando, fora_da_area, agora), False

    def _montar_tela(self, imagem, lay, cursor_cam, cursor_quadro, desenhando, fora_da_area, agora):
        pw, ph = lay["pw"], lay["ph"]

        # painel esquerdo: câmera inteira + retângulo da área de desenho
        camera = np.full((ph, pw, 3), CINZA, np.uint8)
        ox, oy, ec = lay["off_x"], lay["off_y"], lay["esc_cam"]
        camera[oy:oy + lay["cam_h"], ox:ox + lay["cam_w"]] = cv2.resize(imagem, (lay["cam_w"], lay["cam_h"]))
        if lay["zw"] < RESOLUCAO_X or lay["zh"] < RESOLUCAO_Y:
            p1 = (ox + int(lay["zx0"] * ec), oy + int(lay["zy0"] * ec))
            p2 = (ox + int((lay["zx0"] + lay["zw"]) * ec), oy + int((lay["zy0"] + lay["zh"]) * ec))
            cv2.rectangle(camera, p1, p2, AMARELO, 2)
            cv2.putText(camera, "AREA DE DESENHO", (p1[0] + 8, p2[1] - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, AMARELO, 1)

        quadro = self.img.copy()

        # o mesmo cursor nos dois lados: mostra onde o dedo está desenhando
        cor_cursor = (170, 170, 170) if self.cor == BRANCO else self.cor
        preenchimento = cv2.FILLED if desenhando else 2
        if cursor_quadro is not None:
            bx, by, esp = cursor_quadro
            raio = max(esp // 2, 3)
            cv2.circle(quadro, (bx, by), raio, cor_cursor, preenchimento)
            cv2.circle(quadro, (bx, by), raio + 2, PRETO, 1)
            sx, sy = cursor_cam
            cx, cy = ox + int(sx * ec), oy + int(sy * ec)
            cv2.circle(camera, (cx, cy), max(int(raio / lay["esc_zona"] * ec), 5), cor_cursor, preenchimento)
            cv2.circle(camera, (cx, cy), max(int(raio / lay["esc_zona"] * ec), 5) + 2, PRETO, 1)

        self._rotulo(camera, "CAMERA")
        self._rotulo(quadro, "QUADRO")
        if fora_da_area:
            self._rotulo(camera, "Mao fora da area", pos=(10, 60))
        if self.limpar.progresso(agora) > 0:
            self._rotulo(quadro, "Limpando...", pos=(pw // 2 - 80, ph // 2))

        painel = np.hstack([camera, quadro])
        cv2.line(painel, (pw, 0), (pw, ph), PRETO, 3)
        return np.vstack([painel, self._barra(2 * pw)])

    @staticmethod
    def _rotulo(painel, texto, pos=(10, 28)):
        cv2.putText(painel, texto, pos, cv2.FONT_HERSHEY_SIMPLEX, 0.7, PRETO, 4)
        cv2.putText(painel, texto, pos, cv2.FONT_HERSHEY_SIMPLEX, 0.7, BRANCO, 2)

    def _barra(self, largura):
        barra = np.full((BARRA_H, largura, 3), CINZA, np.uint8)
        for i, (cor, rotulo) in enumerate(CORES):
            x = 20 + i * 200
            selecionada = cor == self.cor
            cv2.rectangle(barra, (x, 15), (x + 40, 55), cor, cv2.FILLED)
            cv2.rectangle(barra, (x, 15), (x + 40, 55), AMARELO if selecionada else BRANCO, 4 if selecionada else 1)
            cv2.putText(barra, rotulo, (x + 50, 42), cv2.FONT_HERSHEY_SIMPLEX, 0.55, BRANCO, 1)
        fonte = cv2.FONT_HERSHEY_SIMPLEX
        cv2.putText(barra, "Esq: cor | Dir: indicador desenha", (800, 20), fonte, 0.45, BRANCO, 1)
        cv2.putText(barra, f"Punho=limpar | +/-: espessura {int(self.espessura)} | Q: fechar", (800, 42), fonte, 0.45, BRANCO, 1)
        cv2.putText(barra, "Voltar: deslize a mao ABERTA p/ esquerda", (800, 64), fonte, 0.45, BRANCO, 1)
        return barra

    def cancelar(self):
        """Fecha o quadro (salva o desenho se ele estava aberto)."""
        if self.estado == "desenhando" and self.img is not None:
            cv2.imwrite("quadro.png", self.img)
        self.estado = None