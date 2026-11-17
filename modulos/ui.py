import cv2
import numpy as np

from modulos.config import BRANCO, PRETO, AZUL, VERDE, RESOLUCAO_X


def escreve_centro(imagem, msg, y, escala=1.5, cor=BRANCO):
    """Texto centralizado com contorno preto (legível em qualquer fundo)."""
    (w, _), _ = cv2.getTextSize(msg, cv2.FONT_HERSHEY_COMPLEX, escala, 3)
    x = (RESOLUCAO_X - w) // 2
    cv2.putText(imagem, msg, (x, y), cv2.FONT_HERSHEY_COMPLEX, escala, PRETO, 8)
    cv2.putText(imagem, msg, (x, y), cv2.FONT_HERSHEY_COMPLEX, escala, cor, 3)


def imprime_botoes(imagem, posicao, letra, tamanho=70, cor_retangulo=BRANCO):
    cv2.rectangle(imagem, posicao, (posicao[0] + tamanho, posicao[1] + tamanho), cor_retangulo, cv2.FILLED)
    cv2.rectangle(imagem, posicao, (posicao[0] + tamanho, posicao[1] + tamanho), AZUL, 1)
    escala = 1.2 if len(letra) <= 1 else (0.9 if len(letra) == 2 else 0.65)   # "ENT", "<-", "SP" cabem na tecla
    (largura, altura), _ = cv2.getTextSize(letra, cv2.FONT_HERSHEY_COMPLEX, escala, 2)
    cv2.putText(imagem, letra, (posicao[0] + (tamanho - largura) // 2, posicao[1] + (tamanho + altura) // 2),
                cv2.FONT_HERSHEY_COMPLEX, escala, PRETO, 2)
    return imagem


def tamanho_tela():
    """Resolução do monitor (usa o tkinter, que já vem com o Python). Se falhar, assume Full HD."""
    try:
        import tkinter
        raiz = tkinter.Tk()
        raiz.withdraw()
        largura, altura = raiz.winfo_screenwidth(), raiz.winfo_screenheight()
        raiz.destroy()
        return largura, altura
    except Exception:
        return 1920, 1080


def ajustar_a_tela(imagem, largura, altura):
    """Amplia a imagem até caber na tela SEM deformar, centralizada (faixas pretas se sobrar espaço)."""
    h, w = imagem.shape[:2]
    escala = min(largura / w, altura / h)
    nova_w, nova_h = int(w * escala), int(h * escala)
    redimensionada = cv2.resize(imagem, (nova_w, nova_h))
    tela = np.zeros((altura, largura, 3), np.uint8)
    y0, x0 = (altura - nova_h) // 2, (largura - nova_w) // 2
    tela[y0:y0 + nova_h, x0:x0 + nova_w] = redimensionada
    return tela


def desenhar_progresso(imagem, texto, progresso, cor=VERDE):
    """Texto + barra de progresso embaixo: mostra que o gesto está sendo lido e quanto falta."""
    altura, largura = imagem.shape[:2]
    escreve_centro(imagem, texto, altura - 90, 0.9)
    x0 = (largura - 400) // 2
    cv2.rectangle(imagem, (x0, altura - 70), (x0 + 400, altura - 40), BRANCO, 2)
    cv2.rectangle(imagem, (x0, altura - 70), (x0 + int(400 * progresso), altura - 40), cor, cv2.FILLED)