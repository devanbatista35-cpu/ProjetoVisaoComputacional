"""Configurações gerais do projeto. Ajuste aqui os nomes dos videos e os tempos."""
import os

# resolução da webcam
RESOLUCAO_X = 1280
RESOLUCAO_Y = 720

# largura do avatar no canto superior direito (em pixels da imagem de 1280 px; ele acompanha a tela cheia)
AVATAR_LARGURA = 320

# quadro de desenho: estabilidade do traço
ESPESSURA_PINCEL = 8           # espessura em pixels do quadro (as teclas + e - mudam durante o desenho)
SUAVIZACAO_PARADO = 1.5        # MENOR = traço mais liso com a mão parada (mas com mais atraso)
SUAVIZACAO_VELOCIDADE = 0.03   # MAIOR = menos atraso quando a mão se move rápido

# quadro de desenho em tela cheia:
#   True  = a tela inteira é dividida ao meio, sem faixas pretas (câmera à esquerda, quadro à direita).
#           A câmera é recortada no centro para ter o mesmo formato do quadro.
#   False = mostra a câmera inteira, mas sobram faixas pretas em cima e embaixo.
QUADRO_TELA_DIVIDIDA = True

# quadro de desenho no modo QUADRO_TELA_DIVIDIDA = False: largura de cada painel (webcam e quadro lado a lado).
# 640 -> janela de 1280 px. Se a sua tela for grande, pode aumentar (ex.: 800).
PAINEL_W = 640

# cores (BGR)
BRANCO = (255, 255, 255)
PRETO = (0, 0, 0)
AZUL = (255, 0, 0)
VERDE = (0, 255, 0)
VERMELHO = (0, 0, 255)
AZUL_CLARO = (255, 255, 0)

# videos do avatar
# a pasta "videos" fica ao lado do main.py, não importa de onde você rode o programa
RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PASTA_VIDEOS = os.path.join(RAIZ, "videos")
VIDEOS = {
    # jogo
    "pergunta": "avatar_pergunta.mp4",                      # "Quer jogar?"
    "pedra": "avatar_pedra.mp4",
    "papel": "avatar_papel.mp4",
    "tesoura": "avatar_tesoura.mp4",
    "avatar_ganhou": "avatar_ganhou.mp4",                   # jogador perdeu
    "avatar_perdeu": "avatar_perdeu.mp4",                   # jogador ganhou
    # quadro
    "pergunta_quadro": "avatar_pergunta_quadro.mp4",        # "Quer abrir o quadro?"
    # conversa
    "pergunta_tudo_bem": "avatar_pergunta_tudo_bem.mp4",    # "Esta tudo bem?"
    "resposta_estou_bem": "avatar_estou_bem.mp4",           # "Eu tambem estou bem!"
    "sono": "avatar_sono.mp4",                              # "Estou com sono..."
}

# tempos (segundos)
TEMPO_CONFIRMACAO = 0.4     # quanto tempo segurar o OK
TEMPO_GESTO = 0.6           # quanto tempo segurar um gesto da mão direita para ativá-lo
TEMPO_TIMEOUT = 20          # sem resposta, o avatar desiste e volta ao normal
TEMPO_BLOQUEIO = 2          # pausa depois de sair de um modo
TEMPO_SAIDA = 0.8           # quanto tempo segurar o sinal de rock para fechar o programa
DESLIZE_DISTANCIA = 0.30    # no quadro: a mão aberta percorre essa fração da largura da imagem...
DESLIZE_TEMPO = 0.7         # ...em no máximo esse tempo (s) = "passar a mão" da direita p/ esquerda e voltar

# modo navegador (gesto: 2 dedos da mão direita)
CHROME_PATH = r"C:\Program Files\Google\Chrome\Application\chrome.exe"   # se não existir, abre o navegador padrão
NAV_LARGURA = 640               # largura da janelinha do programa enquanto você usa o navegador
NAV_POSICAO = "baixo-direita"   # baixo-direita, baixo-esquerda, cima-direita ou cima-esquerda
NAV_MARGEM = 0.15               # margem da câmera que você não precisa alcançar (a mão cobre a tela sem esticar o braço)