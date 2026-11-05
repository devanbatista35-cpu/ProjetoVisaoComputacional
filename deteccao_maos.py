import cv2
import mediapipe as mp
import os
from time import sleep
from pynput.keyboard import Controller
import numpy as np


#definindo as cores
BRANCO = (255, 255, 255)
PRETO = (0, 0, 0)
AZUL = (255, 0, 0)
VERDE = (0, 255, 0)
VERMELHO = (0, 0, 255)
AZUL_CLARO = (255, 255, 0)

#acessar o módulo de detecção de mãos do MediaPipe
mp_maos = mp.solutions.hands #módulo para detectar as mãos na imagem
mp_desenho = mp.solutions.drawing_utils #módulo para desenhar as mãos na imagem

#adicionar o módulo de detecção de mãos
maos = mp_maos.Hands() #inicializar o módulo de detecção de mãos

#Acessar a webcam
camera = cv2.VideoCapture(0) #0 para 1 camera

#aumentar a resolução da webcam
resolucao_x = 1280
resolucao_y = 720
camera.set(cv2.CAP_PROP_FRAME_WIDTH, resolucao_x) #definir a largura da webcam
camera.set(cv2.CAP_PROP_FRAME_HEIGHT, resolucao_y) #definir a altura da webcam
bloco_notas = False #variável para controlar se o bloco de notas está aberto ou não
google_chrome = False
calculadora = False
teclas = [['Q', 'W', 'E', 'R', 'T', 'Y', 'U', 'I', 'O', 'P'],
            ['A','S','D','F','G','H','J','K','L'],
            ['Z','X','C','V','B','N','M', ',','.',' ']]
offset = 50
contador = 0
texto = '>'
teclado = Controller()
img_quadro = np.ones((resolucao_y, resolucao_x, 3), np.uint8)*255 #criar uma imagem em branco para o quadro de texto digitado
cor_pincel = (255,0,0)
espessura_pincel = 7
x_quadro, y_quadro = 0, 0

def encontra_coordenadas_maos(imagem, lado_invertido=False):
    #transformar a imagem para RGB, pois o MediaPipe trabalha com imagens RGB
    imagem_rgb = cv2.cvtColor(imagem, cv2.COLOR_BGR2RGB) #converter a imagem para RGB

    resultado = maos.process(imagem_rgb) #processar a imagem para detecção de mãos
    '''
    retorno do resultado:
    resultado.multi_hand_landmarks: lista de pontos de referência das mãos detectadas
    resultado.multi_handedness: lista de informações sobre a mão detectada (direita ou esquerda)
    resultado.multi_hand_world_landmarks: lista de pontos de referência das mãos detectadas em coordenadas do mundo real
    '''
    
    todas_maos = []
    if resultado.multi_hand_landmarks: #se houver mãos detectadas
        for lado_mao, marcacao_maos in zip(resultado.multi_handedness, resultado.multi_hand_landmarks): #para cada mão detectada
            
            info_mao = {}
            coordenadas = []
            for marcacao in marcacao_maos.landmark: #para cada ponto de referência da mão detectada
                coord_x, coord_y, coord_z = int(marcacao.x * resolucao_x), int(marcacao.y * resolucao_y), int(marcacao.z * resolucao_x) #converter as coordenadas para pixels
                coordenadas.append((coord_x, coord_y, coord_z)) #adicionar as coordenadas à lista                
            
            info_mao["coordenadas"] = coordenadas #adicionar as coordenadas da mão à informação da mão  
            if lado_invertido: #se o lado estiver invertido, a mão direita será a esquerda e vice-versa
                if lado_mao.classification[0].label == "Left":
                    info_mao["lado"] = "Right"
                else:
                    info_mao["lado"] = "Left"
            else:
                info_mao["lado"] = lado_mao.classification[0].label

            todas_maos.append(info_mao) #adicionar a informação da mão à lista de todas as mãos
            mp_desenho.draw_landmarks(imagem, marcacao_maos, mp_maos.HAND_CONNECTIONS) #desenhar as mãos na imagem
    
    return imagem, todas_maos #retornar a imagem com as mãos desenhadas e as coordenadas das mãos

def dedos_levantados(mao):
    dedos = []
    for ponta_dedo in [8,12, 16,20]: #pontos de referência das pontas dos dedos
        if mao["coordenadas"][ponta_dedo][1] < mao["coordenadas"][ponta_dedo - 2][1]: #se a ponta do dedo estiver acima da articulação do dedo
            dedos.append(True) #dedo levantado
        else:
            dedos.append(False) #dedo abaixado

    return dedos

def imprime_botoes(imagem, posicao, letra, tamanho = 50, cor_retangulo = BRANCO):
    cv2.rectangle(
        imagem, 
        posicao, 
        (posicao[0] + tamanho, posicao[1] + tamanho), 
        cor_retangulo, 
        cv2.FILLED
    ) #desenhar um retângulo branco no canto superior esquerdo da imagem
    cv2.rectangle(
        imagem, 
        posicao, 
        (posicao[0] + tamanho, posicao[1] + tamanho), 
        AZUL, 
        1
    )
    cv2.putText(imagem, letra, (posicao[0] + 15, posicao[1] + 30), cv2.FONT_HERSHEY_COMPLEX, 1, PRETO, 2) #escrever a letra dentro do retângulo
    return imagem

#mostrar a webcam
while True:
    sucesso, imagem = camera.read() #leitura da webcamimagem = encontra_coordenadas_maos(imagem) #encontrar as coordenadas das mãos na imagem
    imagem = cv2.flip(imagem, 1) #inverter a imagem horizontalmente

    imagem, todas_maos = encontra_coordenadas_maos(imagem) #encontrar as coordenadas das mãos na imagem

    #Checar se há apenas uma mão detectada. 
    if len(todas_maos) == 1:
        info_dedos_mao1 = dedos_levantados(todas_maos[0]) #verificar quais dedos estão levantados
        
        if todas_maos[0]["lado"] == "Left": #se a mão for esquerda, inverter a lista de dedos para que o dedo indicador seja o primeiro elemento da lista
            indicador_x, indicador_y, indicador_z = todas_maos[0]["coordenadas"][8] #coordenadas do dedo indicador
            cv2.putText(imagem, f'Distancia camera: {indicador_z}', (850, 50), cv2.FONT_HERSHEY_COMPLEX, 1, AZUL, 2) #escrever a distância da câmera na imagem
            
            for indice_linha, linha_teclado in enumerate(teclas):

                for indice, letra in enumerate(linha_teclado):
                    if sum(info_dedos_mao1) <= 1:
                        letra = letra.lower()
                    imagem = imprime_botoes(imagem, (offset+indice*80, offset+indice_linha*80), letra) #imprimir os botões do teclado na imagem
                    if offset+indice*80 < indicador_x < 100+indice*80 and offset+indice_linha*80 < indicador_y < 100+ indice_linha*80:
                        imagem = imprime_botoes(imagem, (offset+indice*80, offset+indice_linha*80), letra, cor_retangulo=VERDE) #imprimir o botão pressionado em verde
                        if indicador_z < -85:
                            contador = 1
                            escreve = letra
                            imagem = imprime_botoes(imagem, (offset+indice*80, offset+indice_linha*80), letra, cor_retangulo=AZUL_CLARO) #imprimir o botão pressionado em verde
            if contador:
                contador += 1
                if contador == 3:
                    texto += escreve
                    contador = 0
                    teclado.press(escreve)
            
            if info_dedos_mao1 == [False, False, False, True] and len(texto) > 1:
                texto = texto[:-1]
                sleep(0.15)

            cv2.rectangle(imagem, (offset, 450), (830, 500), BRANCO, cv2.FILLED) #desenhar um retângulo branco para o texto digitad
            cv2.rectangle(imagem, (offset, 450), (830, 500), AZUL, 1) #desenhar um retângulo branco para o texto digitad
            cv2.putText(imagem, texto[-40:], (offset, 480), cv2.FONT_HERSHEY_COMPLEX, 1, PRETO, 2)
            cv2.circle(imagem, (indicador_x, indicador_y), 7,AZUL, cv2.FILLED) #desenhar um círculo vermelho na ponta do dedo indicador


        if todas_maos[0]["lado"] == "Right": #se a mão for direita, inverter a lista de dedos para que o dedo indicador seja o primeiro elemento da lista
            if info_dedos_mao1 == [True, False, False, False] and bloco_notas == False: #se apenas o dedo indicador estiver levantado
                bloco_notas = True #abrir o bloco de notas
                os.startfile(r'C:\Windows\System32\notepad.exe')  
            
            if info_dedos_mao1 == [True, True, False, False] and google_chrome == False: #se apenas o dedo indicador estiver levantado
                google_chrome = True #abrir o Google Chrome
                os.startfile(r'C:\Program Files\Google\Chrome\Application\chrome.exe')          
            
            if info_dedos_mao1 == [True, True, True, False] and calculadora == False: #se apenas o dedo indicador estiver levantado
                calculadora = True #abrir a calculadora
                os.startfile(r'C:\Windows\System32\calc.exe')  
            
            if info_dedos_mao1 == [False, False, False, False] and bloco_notas == True:
                bloco_notas = False #fechar o bloco de notas
                os.system("taskkill /im notepad.exe /f") #fechar o bloco de notas:
            
            if info_dedos_mao1 == [True, False, False, True]:
                break
    
    if len(todas_maos) == 2:
        info_dedos_mao1 = dedos_levantados(todas_maos[0]) #verificar quais dedos estão levantados da mão 1
        info_dedos_mao2 = dedos_levantados(todas_maos[1]) #verificar quais dedos estão levantados da mão 2
        
        indicador_x, indicador_y, indicador_z = todas_maos[0]["coordenadas"][8] #coordenadas do dedo indicador da mão 1
        if sum(info_dedos_mao2) == 1:
            cor_pincel = AZUL
        elif sum(info_dedos_mao2) == 2:
            cor_pincel = VERDE
        elif sum(info_dedos_mao2) == 3:
            cor_pincel = VERMELHO
        elif sum(info_dedos_mao2) == 4:
            cor_pincel = BRANCO
        else:
            img_quadro = np.ones((resolucao_y, resolucao_x, 3), np.uint8)*255 #criar uma imagem em branco para o quadro de texto digitado

        espessura_pincel = int(abs(indicador_z))//3 + 5 #definir a espessura do pincel com base na distância da câmera
        cv2.circle(imagem, (indicador_x, indicador_y), espessura_pincel, cor_pincel, cv2.FILLED) #desenhar um círculo na ponta do dedo indicador da mão 1 com a cor do pincel selecionada

        if info_dedos_mao1 == [True, False, False, False]: #se apenas o dedo indicador da mão 1 estiver levantado
            if x_quadro == 0 and y_quadro == 0:
                x_quadro, y_quadro = indicador_x, indicador_y
            
            cv2.line(img_quadro, (x_quadro, y_quadro), (indicador_x, indicador_y), cor_pincel, espessura_pincel) #desenhar uma linha no quadro de texto digitado com a cor do pincel selecionada
            x_quadro, y_quadro = indicador_x, indicador_y
        else: 
            x_quadro, y_quadro = 0, 0
        
        imagem = cv2.addWeighted(imagem, 1, img_quadro, 0.2, 0) #sobrepor o quadro de texto digitado na imagem da webcam

    cv2.imshow("Imagem", imagem) #mostrar a webcam

    cv2.imshow("Quadro", img_quadro) #mostrar o quadro de texto digitado

    tecla = cv2.waitKey(1) #esperar 1 milisegundo para atualizar a imagem
    if tecla == 27: #se a tecla for ESC, sair do loop
        break #sair do loop

with open("texto_digitado.txt", "w") as arquivo: #abrir um arquivo de texto para escrever o texto digitado
    arquivo.write(texto) #escrever o texto digitado no arquivo

cv2.imwrite('quadro.png', img_quadro) #salvar o quadro de texto digitado como uma imagem