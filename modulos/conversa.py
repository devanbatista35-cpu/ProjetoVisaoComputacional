from modulos.config import VERDE, BRANCO, TEMPO_TIMEOUT
from modulos.gestos import gesto_joinha, mao_fechada, Retencao
from modulos.ui import escreve_centro

class Conversa:
    """Avatar pergunta se está tudo bem.

    perguntando      -> avatar pergunta "esta tudo bem?"; espera um joinha (polegar para cima)
    respondendo      -> avatar responde que também está bem
    aguardando_sono  -> espera a pessoa fechar a mão direita
    dormindo         -> avatar diz que está com sono e a conversa termina
    """

    def __init__(self, avatar):
        self.avatar = avatar
        self.estado = None
        self.t_inicio = 0
        self.t_fim = None
        self.joinha = Retencao(0.5)
        self.punho = Retencao(0.6)

    def iniciar(self, agora):
        self.avatar.tocar("pergunta_tudo_bem")
        self.estado = "perguntando"
        self.t_inicio = agora
        self.t_fim = None
        self.joinha.resetar()
        self.punho.resetar()

    def cancelar(self):
        self.estado = None

    def atualizar(self, imagem, todas_maos, agora):
        """Retorna (imagem, finalizou)."""

        if self.estado == "perguntando":
            escreve_centro(imagem, "Responda com um joinha!", 650, 1.1, VERDE)
            if self.joinha.atualizar(any(gesto_joinha(m) for m in todas_maos), agora):
                self.avatar.tocar("resposta_estou_bem")
                self.estado = "respondendo"
            elif agora - self.t_inicio > TEMPO_TIMEOUT:
                return imagem, True

        elif self.estado == "respondendo":
            if self.avatar.terminou:
                self.estado = "aguardando_sono"
                self.t_inicio = agora
                self.punho.resetar()

        elif self.estado == "aguardando_sono":
            escreve_centro(imagem, "Feche a mao direita para o avatar dormir", 650, 1.0, VERDE)
            direita_fechada = any(m["lado"] == "Right" and mao_fechada(m) for m in todas_maos)
            # espera 1 s antes de aceitar, para não confundir com o joinha anterior
            pode = agora - self.t_inicio > 1.0
            if self.punho.atualizar(direita_fechada and pode, agora):
                self.avatar.tocar("sono")
                self.estado = "dormindo"
            elif agora - self.t_inicio > TEMPO_TIMEOUT:
                return imagem, True

        elif self.estado == "dormindo":
            escreve_centro(imagem, "Zzz...", 650, 1.5, BRANCO)
            if self.avatar.terminou:
                if self.t_fim is None:
                    self.t_fim = agora
                if agora - self.t_fim > 1.5:   # deixa o último frame na tela por um instante
                    return imagem, True

        return imagem, False
