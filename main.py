"""Ponto de entrada. Rode com:  python main.py

Gestos no modo normal:
  mão esquerda            -> teclado virtual (pinça digita)
  direita: indicador      -> jogo pedra, papel e tesoura
  direita: 3 dedos        -> conversa com o avatar (tudo bem? / sono)
  direita: 2 dedos        -> MODO NAVEGADOR: abre o Chrome; mão direita = mouse, mão esquerda = teclado
  ROCK (indicador+mindinho, segurar 0,8 s) -> fecha o programa em QUALQUER momento, com qualquer mão
  duas mãos abertas (1 s) -> quadro de desenho (avatar pede OK)
No quadro e no navegador: deslizar a mão ABERTA da direita para a esquerda volta para a tela principal.
Teclas: Q cancela o modo atual | F tela cheia/janela | + e - espessura do pincel | ESC fecha
        I mostra FPS e o que o programa está lendo (dedos: indicador, médio, anelar, mindinho; OK sim/não)
"""
import os
import time
import cv2

from modulos.config import (RESOLUCAO_X, RESOLUCAO_Y, BRANCO, VERDE, VERMELHO, TEMPO_GESTO, TEMPO_BLOQUEIO,
                            TEMPO_SAIDA, AVATAR_LARGURA)
from modulos.detector_maos import DetectorMaos
from modulos.avatar import Avatar
from modulos.janela import Janela
from modulos.teclado_virtual import TecladoVirtual
from modulos.quadro import Quadro
from modulos.jogo import Jogo
from modulos.conversa import Conversa
from modulos.navegador import Navegador
from modulos.gestos import (dedos_esticados, gesto_ok, mao_aberta, gesto_rock,
                            EstadoDedos, GestoEstavel, Retencao)
from modulos.ui import escreve_centro, desenhar_progresso

# ---------------- inicialização ----------------
# No Windows, DirectShow + MJPG costuma dar 30 FPS reais em 720p (o padrão pode ficar em 10-15 FPS)
camera = cv2.VideoCapture(0, cv2.CAP_DSHOW) if os.name == "nt" else cv2.VideoCapture(0)
if not camera.isOpened():
    camera = cv2.VideoCapture(0)
camera.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*"MJPG"))
camera.set(cv2.CAP_PROP_FRAME_WIDTH, RESOLUCAO_X)
camera.set(cv2.CAP_PROP_FRAME_HEIGHT, RESOLUCAO_Y)
camera.set(cv2.CAP_PROP_FPS, 30)
camera.set(cv2.CAP_PROP_BUFFERSIZE, 1)   # sem fila de frames antigos (menos atraso)

janela = Janela("Imagem")   # tela cheia (F alterna); no modo navegador vira uma janelinha por cima do Chrome

detector = DetectorMaos()
avatar = Avatar()
teclado = TecladoVirtual()
modos = {
    "jogo": Jogo(avatar),
    "quadro": Quadro(avatar),
    "conversa": Conversa(avatar),
    "navegador": Navegador(teclado, (janela.tela_larg, janela.tela_alt)),
}
modos["quadro"].tamanho_saida = janela.tamanho_exibicao()   # para dividir a tela cheia ao meio

modo_atual = None       # None = modo normal (ocioso)
bloqueio_ate = 0        # evita reativar um gesto logo depois de sair de um modo
duas_maos = Retencao(1.0, tolerancia=0.2)
saida_rock = Retencao(TEMPO_SAIDA, tolerancia=0.15)   # sinal de rock segurado = fechar o programa
dedos_direita = EstadoDedos()                    # estado de cada dedo, com memória (não pisca)
gesto_direita = GestoEstavel(TEMPO_GESTO, 0.15)  # o gesto só vale depois de estável (tolera falhas rápidas)
ACOES = {   # gesto da mão direita (indicador, médio, anelar, mindinho) -> (modo, texto de progresso)
    (True, False, False, False): ("jogo", "Jogo: indicador"),
    (True, True, True, False): ("conversa", "Conversa: 3 dedos"),
    (True, True, False, False): ("navegador", "Navegador: 2 dedos"),
}
mostrar_info = False    # tecla I
fps = 30.0
t_ultimo_frame = time.time()


def iniciar_modo(nome, agora):
    global modo_atual
    modo_atual = modos[nome]
    modo_atual.iniciar(agora)
    gesto_direita.resetar()
    dedos_direita.resetar()
    duas_maos.resetar()


def sair_do_modo():
    global modo_atual, bloqueio_ate
    if modo_atual is not None:
        modo_atual.cancelar()
    modo_atual = None
    avatar.esconder()
    bloqueio_ate = time.time() + TEMPO_BLOQUEIO


# ---------------- loop principal ----------------
while True:
    sucesso, imagem = camera.read()
    if not sucesso:
        break
    if imagem.shape[1] != RESOLUCAO_X or imagem.shape[0] != RESOLUCAO_Y:
        imagem = cv2.resize(imagem, (RESOLUCAO_X, RESOLUCAO_Y))   # webcam que não entrega 1280x720
    imagem = cv2.flip(imagem, 1)
    imagem, todas_maos = detector.processar(imagem)
    agora = time.time()
    fps = 0.9 * fps + 0.1 / max(agora - t_ultimo_frame, 1e-3)
    t_ultimo_frame = agora

    # sinal de rock em QUALQUER momento (qualquer mão, qualquer modo) fecha o programa
    if saida_rock.atualizar(any(gesto_rock(m) for m in todas_maos), agora):
        break

    if modo_atual is not None:
        # um modo (jogo, quadro, conversa ou navegador) está no controle
        imagem, terminou = modo_atual.atualizar(imagem, todas_maos, agora)
        if terminou:
            sair_do_modo()

    else:
        if len(todas_maos) != 2:
            duas_maos.resetar()

        # ---------- uma mão ----------
        if len(todas_maos) == 1:
            mao = todas_maos[0]

            if mao["lado"] == "Left":
                gesto_direita.resetar()
                dedos_direita.resetar()
                imagem = teclado.atualizar(imagem, mao, agora)

            else:
                # o gesto precisa ser SEGURADO (senão dedos levantados em sequência disparariam os gestos
                # intermediários), mas uma falha rápida da detecção não zera a contagem
                estavel = gesto_direita.atualizar(dedos_direita.atualizar(mao), agora)
                if agora > bloqueio_ate:
                    if estavel in ACOES:
                        iniciar_modo(ACOES[estavel][0], agora)
                    elif gesto_direita.candidato in ACOES:   # barra mostrando que o gesto está sendo lido
                        desenhar_progresso(imagem, ACOES[gesto_direita.candidato][1], gesto_direita.progresso(agora))

        # ---------- duas mãos: abertas por 1 s abrem o quadro ----------
        elif len(todas_maos) == 2:
            gesto_direita.resetar()
            dedos_direita.resetar()
            abertas = all(mao_aberta(m) for m in todas_maos) and agora > bloqueio_ate
            if duas_maos.atualizar(abertas, agora):
                iniciar_modo("quadro", agora)
            elif abertas:
                progresso = duas_maos.progresso(agora)
                cv2.rectangle(imagem, (440, 650), (840, 680), BRANCO, 2)
                cv2.rectangle(imagem, (440, 650), (440 + int(400 * progresso), 680), VERDE, cv2.FILLED)
                escreve_centro(imagem, "Segure as duas maos abertas...", 630, 0.9)

        else:
            gesto_direita.resetar()
            dedos_direita.resetar()

    # avatar por cima de tudo
    imagem = avatar.desenhar(imagem, AVATAR_LARGURA)
    if saida_rock.progresso(agora) > 0:     # barra de "saindo...": abaixar a mão cancela
        h_img, w_img = imagem.shape[:2]
        escreve_centro(imagem, "Saindo... (abaixe a mao para cancelar)", h_img - 100, 1.0, VERMELHO)
        x0 = (w_img - 400) // 2
        cv2.rectangle(imagem, (x0, h_img - 80), (x0 + 400, h_img - 50), BRANCO, 2)
        cv2.rectangle(imagem, (x0, h_img - 80), (x0 + int(400 * saida_rock.progresso(agora)), h_img - 50),
                      VERMELHO, cv2.FILLED)

    if mostrar_info:    # o que o programa está lendo: dedos (indicador, médio, anelar, mindinho) e OK
        for k, m in enumerate(todas_maos):
            dedos = "".join("1" if v else "0" for v in dedos_esticados(m))
            cv2.putText(imagem, f"{m['lado']}: dedos {dedos} | OK: {'SIM' if gesto_ok(m) else 'nao'}",
                        (20, 40 + 36 * k), cv2.FONT_HERSHEY_SIMPLEX, 0.9, VERDE, 2)

    compacta = modo_atual is not None and getattr(modo_atual, "janela_compacta", False)
    janela.mostrar(imagem, compacta, f"FPS: {fps:.0f}" if mostrar_info else None)

    tecla = cv2.waitKey(1) & 0xFF
    if tecla == 27:  # ESC
        break
    if tecla == ord('q') and modo_atual is not None:
        sair_do_modo()
    if tecla in (ord('+'), ord('=')) and modo_atual is modos["quadro"]:
        modos["quadro"].mudar_espessura(2)
    if tecla in (ord('-'), ord('_')) and modo_atual is modos["quadro"]:
        modos["quadro"].mudar_espessura(-2)
    if tecla == ord('i'):
        mostrar_info = not mostrar_info
    if tecla == ord('f'):
        janela.alternar_tela_cheia()
        modos["quadro"].tamanho_saida = janela.tamanho_exibicao()

# ---------------- encerramento ----------------
sair_do_modo()          # fecha e salva o quadro se estiver aberto; solta o mouse se estava pressionado
camera.release()
cv2.destroyAllWindows()
teclado.salvar()