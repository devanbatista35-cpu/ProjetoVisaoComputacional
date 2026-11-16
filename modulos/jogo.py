import random
from collections import Counter

from modulos.config import BRANCO, VERDE, VERMELHO, TEMPO_CONFIRMACAO, TEMPO_TIMEOUT
from modulos.gestos import gesto_jogada, alguma_ok, Retencao
from modulos.ui import escreve_centro

GANHA_DE = {"pedra": "tesoura", "tesoura": "papel", "papel": "pedra"}


def resolve(jogador, adversario):
    if jogador == adversario:
        return "empate"
    return "jogador" if GANHA_DE[jogador] == adversario else "avatar"


class Jogo:
    """Pedra, papel e tesoura.

    Estados: pergunta -> contagem -> revelando -> resultado
    """

    def __init__(self, avatar):
        self.avatar = avatar
        self.estado = None
        self.t_inicio = 0
        self.inicio_contagem = 0
        self.ok = Retencao(TEMPO_CONFIRMACAO)
        self.gestos_lidos = []
        self.jogada_jogador = None
        self.jogada_avatar = None
        self.mensagem = ""
        self.placar = {"jogador": 0, "avatar": 0}

    def iniciar(self, agora):
        self.avatar.tocar("pergunta")
        self.estado = "pergunta"
        self.t_inicio = agora
        self.mensagem = ""
        self.ok.resetar()

    def cancelar(self):
        self.estado = None

    def _nova_contagem(self, agora):
        self.estado = "contagem"
        self.inicio_contagem = agora
        self.gestos_lidos = []

    def atualizar(self, imagem, todas_maos, agora):
        """Retorna (imagem, finalizou)."""
        mao = todas_maos[0] if todas_maos else None

        if self.estado == "pergunta":
            escreve_centro(imagem, "Faca OK com a mao para jogar!", 650, 1.1, VERDE)
            if self.ok.atualizar(alguma_ok(todas_maos), agora):
                self.avatar.esconder()
                self._nova_contagem(agora)
            elif agora - self.t_inicio > TEMPO_TIMEOUT:
                return imagem, True

        elif self.estado == "contagem":
            tempo = agora - self.inicio_contagem
            if tempo < 3:
                escreve_centro(imagem, str(3 - int(tempo)), 360, 6)
                escreve_centro(imagem, "Prepare sua jogada...", 650, 1.1)
            else:
                escreve_centro(imagem, "JA!", 360, 6, VERDE)

            # le o gesto no final da contagem
            if tempo >= 2.5 and mao is not None:
                self.gestos_lidos.append(gesto_jogada(mao))

            if tempo >= 3.3:
                validos = [g for g in self.gestos_lidos if g is not None]
                if not validos:
                    self.mensagem = "Nao vi sua jogada! Tente de novo"
                    self._nova_contagem(agora)
                else:
                    self.jogada_jogador = Counter(validos).most_common(1)[0][0]
                    self.jogada_avatar = random.choice(["pedra", "papel", "tesoura"])
                    self.avatar.tocar(self.jogada_avatar)
                    self.estado = "revelando"
                    self.mensagem = ""

            if self.mensagem:
                escreve_centro(imagem, self.mensagem, 600, 1, VERMELHO)

        elif self.estado == "revelando":
            escreve_centro(imagem, f"Voce: {self.jogada_jogador.upper()}", 650, 1.1)
            if self.avatar.terminou:
                vencedor = resolve(self.jogada_jogador, self.jogada_avatar)
                if vencedor == "empate":
                    self.mensagem = "Empate! Vamos de novo"
                    self.avatar.esconder()
                    self._nova_contagem(agora)
                elif vencedor == "jogador":
                    self.placar["jogador"] += 1
                    self.avatar.tocar("avatar_perdeu")
                    self.estado = "resultado"
                    self.mensagem = "VOCE GANHOU!"
                else:
                    self.placar["avatar"] += 1
                    self.avatar.tocar("avatar_ganhou")
                    self.estado = "resultado"
                    self.mensagem = "VOCE PERDEU!"

        elif self.estado == "resultado":
            cor = VERDE if "GANHOU" in self.mensagem else VERMELHO
            escreve_centro(imagem, self.mensagem, 360, 2.5, cor)
            escreve_centro(imagem, f"Placar  Voce {self.placar['jogador']} x {self.placar['avatar']} Avatar", 650, 1.1, BRANCO)
            if self.avatar.terminou:
                return imagem, True

        return imagem, False
