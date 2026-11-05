"""
libras_knn.py - Reconhecimento de sinais estaticos com k-NN (Proposta B)

Uso:
    python libras_knn.py coletar NOME   # grava exemplos (NOME = quem esta fazendo os sinais)
    python libras_knn.py treinar        # mede o acerto e salva o modelo
    python libras_knn.py reconhecer     # reconhece os sinais em tempo real

Privacidade: so as coordenadas da mao (numeros) sao salvas. Nenhuma imagem da camera e gravada.

Antes da mostra, confira a lista SINAIS com uma pessoa que conhece Libras.
"""
import csv
import os
import sys
import threading
import time
from collections import Counter

import cv2
import joblib
import mediapipe as mp
import numpy as np

try:
    import winsound  # so existe no Windows; usado para tocar audios .wav
except ImportError:
    winsound = None

# ----------------------------------------------------------------------------
# CONFIGURACOES (ajuste aqui)
# ----------------------------------------------------------------------------
SINAIS = ["1", "2", "3", "4", "5", "A", "B", "L", "V", "Y"]  # lista a validar com quem conhece Libras
NUMEROS = {"1": "um", "2": "dois", "3": "tres", "4": "quatro", "5": "cinco"}

ARQUIVO_DADOS = "dados_sinais.csv"
ARQUIVO_MODELO = "sinais.joblib"
PASTA_AUDIO = "audio"            # audio/A.wav, audio/1.wav ... (opcional; senao usa pyttsx3)

RESOLUCAO_X, RESOLUCAO_Y = 1280, 720
META_AMOSTRAS = 50               # amostras por sinal, por pessoa
INTERVALO_GRAVACAO = 3           # grava 1 amostra a cada N quadros (evita exemplos quase iguais)
K = 5                            # numero de vizinhos do k-NN
FOLGA_LIMITE = 1.3               # quanto acima do "normal" a distancia pode ir antes de rejeitar
FRAMES_CONFIRMACAO = 12          # quadros seguidos com o mesmo sinal (cerca de 0,5 s)
COOLDOWN_S = 1.5                 # pausa entre duas respostas
ESPELHAR_ESQUERDA = True         # um so conjunto de dados serve para as duas maos

BRANCO, PRETO = (255, 255, 255), (0, 0, 0)
VERDE, VERMELHO, AZUL = (0, 200, 0), (0, 0, 255), (255, 0, 0)

mp_maos = mp.solutions.hands
mp_desenho = mp.solutions.drawing_utils


# ----------------------------------------------------------------------------
# NORMALIZACAO E DETECCAO
# ----------------------------------------------------------------------------
def normalizar(pontos, lado):
    """Transforma os 21 pontos em 42 numeros que nao dependem de onde a mao esta nem de
    quao perto da camera ela esta. Devolve None se a mao for pequena demais."""
    pontos = pontos.copy()
    pontos -= pontos[0]                              # 1) pulso vira a origem
    escala = np.linalg.norm(pontos[9][:2])           # 2) tamanho da mao: pulso -> base do dedo medio
    if escala < 1e-6:
        return None
    pontos /= escala
    if ESPELHAR_ESQUERDA and lado == "Left":         # 3) mao esquerda vira "direita"
        pontos[:, 0] *= -1
    return pontos[:, :2].flatten()                   # so x e y (o z do MediaPipe e ruidoso)


def detectar(maos, imagem):
    """Devolve (vetor_normalizado, lado, marcacao) ou (None, None, None) se nao houver mao."""
    rgb = cv2.cvtColor(imagem, cv2.COLOR_BGR2RGB)
    resultado = maos.process(rgb)
    if not resultado.multi_hand_landmarks:
        return None, None, None
    marcacao = resultado.multi_hand_landmarks[0]
    lado = resultado.multi_handedness[0].classification[0].label
    pontos = np.array([[p.x, p.y, p.z] for p in marcacao.landmark])
    return normalizar(pontos, lado), lado, marcacao


def abrir_camera():
    camera = cv2.VideoCapture(0)
    camera.set(cv2.CAP_PROP_FRAME_WIDTH, RESOLUCAO_X)
    camera.set(cv2.CAP_PROP_FRAME_HEIGHT, RESOLUCAO_Y)
    return camera


def texto_tela(sinal):
    """Texto sem acento (o OpenCV nao desenha acentos)."""
    return f"Numero {sinal}" if sinal in NUMEROS else f"Letra {sinal}"


def frase_fala(sinal):
    if sinal in NUMEROS:
        return f"Número {NUMEROS[sinal].replace('tres', 'três')}"
    return f"Letra {sinal}"


# ----------------------------------------------------------------------------
# DADOS (CSV: pessoa, sinal, 42 numeros)
# ----------------------------------------------------------------------------
def carregar_dados():
    if not os.path.exists(ARQUIVO_DADOS):
        return [], [], np.empty((0, 42))
    pessoas, rotulos, X = [], [], []
    with open(ARQUIVO_DADOS, newline="", encoding="utf-8") as arquivo:
        for linha in csv.reader(arquivo):
            if len(linha) != 44:
                continue
            pessoas.append(linha[0])
            rotulos.append(linha[1])
            X.append([float(v) for v in linha[2:]])
    return pessoas, rotulos, np.array(X)


def salvar_amostras(novas):
    if not novas:
        return
    with open(ARQUIVO_DADOS, "a", newline="", encoding="utf-8") as arquivo:
        csv.writer(arquivo).writerows(novas)
    print(f"{len(novas)} amostras salvas em {ARQUIVO_DADOS}")


# ----------------------------------------------------------------------------
# MODO 1: COLETAR
# ----------------------------------------------------------------------------
def coletar(pessoa):
    """Teclas: n/b = proximo/anterior sinal | g = liga/desliga gravacao | s = salvar | ESC = sair"""
    pessoas, rotulos, _ = carregar_dados()
    contagem = Counter(r for p, r in zip(pessoas, rotulos) if p == pessoa)
    novas, indice, gravando, quadros = [], 0, False, 0
    camera = abrir_camera()

    with mp_maos.Hands(max_num_hands=1, min_detection_confidence=0.6) as maos:
        while True:
            sucesso, imagem = camera.read()
            if not sucesso:
                print("Nao consegui ler a webcam.")
                break
            imagem = cv2.flip(imagem, 1)
            vetor, lado, marcacao = detectar(maos, imagem)
            if marcacao is not None:
                mp_desenho.draw_landmarks(imagem, marcacao, mp_maos.HAND_CONNECTIONS)

            sinal = SINAIS[indice]
            if gravando and vetor is not None:
                quadros += 1
                if quadros % INTERVALO_GRAVACAO == 0:
                    novas.append([pessoa, sinal, *[round(float(v), 5) for v in vetor]])
                    contagem[sinal] += 1
                if contagem[sinal] >= META_AMOSTRAS:
                    gravando = False  # meta atingida: para sozinho

            cor = VERMELHO if gravando else VERDE
            cv2.rectangle(imagem, (0, 0), (RESOLUCAO_X, 110), BRANCO, cv2.FILLED)
            cv2.putText(imagem, f"Pessoa: {pessoa}   Sinal: {sinal}   ({contagem[sinal]}/{META_AMOSTRAS})",
                        (20, 45), cv2.FONT_HERSHEY_COMPLEX, 1, PRETO, 2)
            estado = "GRAVANDO" if gravando else "parado"
            cv2.putText(imagem, f"{estado} | n/b troca sinal | g grava | s salva | ESC sai",
                        (20, 90), cv2.FONT_HERSHEY_COMPLEX, 0.8, cor, 2)
            if vetor is None:
                cv2.putText(imagem, "Mao nao detectada", (20, 160), cv2.FONT_HERSHEY_COMPLEX, 1, VERMELHO, 2)

            cv2.imshow("Coleta de sinais", imagem)
            tecla = cv2.waitKey(1) & 0xFF
            if tecla == 27:
                break
            elif tecla == ord("n"):
                indice, gravando = (indice + 1) % len(SINAIS), False
            elif tecla == ord("b"):
                indice, gravando = (indice - 1) % len(SINAIS), False
            elif tecla == ord("g"):
                gravando = not gravando
            elif tecla == ord("s"):
                salvar_amostras(novas)
                novas = []

    salvar_amostras(novas)
    camera.release()
    cv2.destroyAllWindows()


# ----------------------------------------------------------------------------
# MODO 2: TREINAR
# ----------------------------------------------------------------------------
def calcular_limite(X, grupos):
    """Distancia maxima aceitavel ao exemplo mais proximo; acima disso o sinal e 'desconhecido'.
    Calculada com pessoas que o modelo nao viu, para nao ficar pequena demais."""
    from sklearn.neighbors import NearestNeighbors

    distancias = []
    pessoas = sorted(set(grupos))
    if len(pessoas) >= 2:
        for pessoa in pessoas:
            dela = grupos == pessoa
            vizinhos = NearestNeighbors(n_neighbors=1).fit(X[~dela])
            d, _ = vizinhos.kneighbors(X[dela])
            distancias.extend(d.ravel())
        folga = FOLGA_LIMITE
    else:
        vizinhos = NearestNeighbors(n_neighbors=2).fit(X)
        d, _ = vizinhos.kneighbors(X)
        distancias = d[:, 1]
        folga = FOLGA_LIMITE * 2
        print("AVISO: so ha dados de uma pessoa; o limite de rejeicao fica pouco confiavel.")
    return float(np.percentile(distancias, 95) * folga)


def treinar():
    from sklearn.metrics import accuracy_score, classification_report, confusion_matrix
    from sklearn.model_selection import LeaveOneGroupOut, cross_val_predict, train_test_split
    from sklearn.neighbors import KNeighborsClassifier

    pessoas, rotulos, X = carregar_dados()
    if len(rotulos) == 0:
        print(f"Sem dados. Rode primeiro: python {os.path.basename(__file__)} coletar NOME")
        return
    y, grupos = np.array(rotulos), np.array(pessoas)
    sinais = sorted(set(y))

    print("Amostras por sinal:", dict(Counter(rotulos)))
    print("Pessoas:", dict(Counter(pessoas)))
    modelo = KNeighborsClassifier(n_neighbors=K)

    if len(set(grupos)) >= 2:
        print("\nValidacao 'deixe uma pessoa de fora' (o teste que importa para a mostra):")
        previsoes = cross_val_predict(modelo, X, y, groups=grupos, cv=LeaveOneGroupOut())
        for pessoa in sorted(set(grupos)):
            dela = grupos == pessoa
            print(f"  {pessoa}: {accuracy_score(y[dela], previsoes[dela]):.1%}")
        reais, previstos = y, previsoes
    else:
        print("\nAVISO: com uma unica pessoa o acerto e otimista. Colete com mais gente.")
        X_tr, X_te, y_tr, y_te = train_test_split(X, y, test_size=0.2, stratify=y, random_state=0)
        previstos = modelo.fit(X_tr, y_tr).predict(X_te)
        reais = y_te

    print(f"\nAcerto geral: {accuracy_score(reais, previstos):.1%}  (meta: 90% no total, 80% por sinal)")
    print(classification_report(reais, previstos, zero_division=0))
    print("Matriz de confusao (linha = sinal real, coluna = sinal previsto):")
    print("      " + " ".join(f"{s:>4}" for s in sinais))
    for sinal, linha in zip(sinais, confusion_matrix(reais, previstos, labels=sinais)):
        print(f"{sinal:>5} " + " ".join(f"{v:>4}" for v in linha))

    modelo.fit(X, y)  # modelo final usa todos os dados
    limite = calcular_limite(X, grupos)
    joblib.dump({"modelo": modelo, "limite": limite}, ARQUIVO_MODELO)
    print(f"\nModelo salvo em {ARQUIVO_MODELO} (limite de rejeicao = {limite:.3f})")


# ----------------------------------------------------------------------------
# MODO 3: RECONHECER
# ----------------------------------------------------------------------------
_trava_voz = threading.Lock()


def _falar_pyttsx3(frase):
    if not _trava_voz.acquire(blocking=False):
        return  # ja esta falando
    try:
        import pyttsx3

        motor = pyttsx3.init()
        for voz in motor.getProperty("voices"):
            if "pt" in voz.id.lower() or "portug" in voz.name.lower():
                motor.setProperty("voice", voz.id)
                break
        motor.say(frase)
        motor.runAndWait()
    except Exception as erro:  # a voz nunca pode derrubar o programa
        print("Voz indisponivel:", erro)
    finally:
        _trava_voz.release()


def falar(sinal):
    """Toca audio/<sinal>.wav se existir (melhor); senao usa a voz do Windows (pyttsx3)."""
    arquivo = os.path.join(PASTA_AUDIO, f"{sinal}.wav")
    if winsound is not None and os.path.exists(arquivo):
        winsound.PlaySound(arquivo, winsound.SND_FILENAME | winsound.SND_ASYNC)
    else:
        threading.Thread(target=_falar_pyttsx3, args=(frase_fala(sinal),), daemon=True).start()


def reconhecer():
    if not os.path.exists(ARQUIVO_MODELO):
        print(f"Modelo nao encontrado. Rode: python {os.path.basename(__file__)} treinar")
        return
    dados = joblib.load(ARQUIVO_MODELO)
    modelo, limite = dados["modelo"], dados["limite"]

    candidato, quadros, ultimo = None, 0, 0.0
    mostrado, mostrado_ate = "", 0.0
    camera = abrir_camera()

    with mp_maos.Hands(max_num_hands=1, min_detection_confidence=0.6) as maos:
        while True:
            sucesso, imagem = camera.read()
            if not sucesso:
                print("Nao consegui ler a webcam.")
                break
            imagem = cv2.flip(imagem, 1)
            vetor, lado, marcacao = detectar(maos, imagem)
            if marcacao is not None:
                mp_desenho.draw_landmarks(imagem, marcacao, mp_maos.HAND_CONNECTIONS)

            if vetor is None:
                candidato, quadros = None, 0
                status, distancia = "Mostre a mao", None
            else:
                distancia = float(modelo.kneighbors([vetor], n_neighbors=1)[0][0][0])
                if distancia > limite:                     # nao parece com nenhum sinal conhecido
                    candidato, quadros = None, 0
                    status = "Sinal nao reconhecido"
                else:
                    previsto = modelo.predict([vetor])[0]
                    quadros = quadros + 1 if previsto == candidato else 1
                    candidato = previsto
                    status = f"{texto_tela(previsto)} ({min(quadros, FRAMES_CONFIRMACAO)}/{FRAMES_CONFIRMACAO})"
                    agora = time.time()
                    if quadros >= FRAMES_CONFIRMACAO and agora - ultimo > COOLDOWN_S:
                        ultimo, mostrado, mostrado_ate = agora, previsto, agora + 2.0
                        print("Sinal reconhecido:", texto_tela(previsto))
                        falar(previsto)

            cv2.rectangle(imagem, (0, 0), (RESOLUCAO_X, 70), BRANCO, cv2.FILLED)
            cv2.putText(imagem, status, (20, 48), cv2.FONT_HERSHEY_COMPLEX, 1.2, PRETO, 2)
            if distancia is not None:  # util para ajustar FOLGA_LIMITE; pode remover na mostra
                cv2.putText(imagem, f"dist {distancia:.2f} / limite {limite:.2f}", (20, RESOLUCAO_Y - 20),
                            cv2.FONT_HERSHEY_COMPLEX, 0.7, AZUL, 2)
            if mostrado and time.time() < mostrado_ate:
                cv2.putText(imagem, texto_tela(mostrado), (RESOLUCAO_X // 2 - 220, RESOLUCAO_Y // 2),
                            cv2.FONT_HERSHEY_COMPLEX, 3, VERDE, 6)

            cv2.imshow("Reconhecimento de sinais", imagem)
            if cv2.waitKey(1) & 0xFF == 27:
                break

    camera.release()
    cv2.destroyAllWindows()


# ----------------------------------------------------------------------------
if __name__ == "__main__":
    modo = sys.argv[1] if len(sys.argv) > 1 else ""
    if modo == "coletar" and len(sys.argv) > 2:
        coletar(sys.argv[2])
    elif modo == "treinar":
        treinar()
    elif modo == "reconhecer":
        reconhecer()
    else:
        print(__doc__)
