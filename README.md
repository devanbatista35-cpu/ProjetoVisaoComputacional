# ✋ Controle por Gestos com Visão Computacional

Projeto da disciplina **Algoritmos e Pensamento Computacional** (Braz Cubas – 2026/2).

O programa usa a **webcam** para enxergar suas mãos e transforma gestos em ações no computador:

| Situação na câmera          | O que acontece                                              |
|-----------------------------|-------------------------------------------------------------|
| Só a **mão esquerda**       | Aparece um **teclado virtual** e você "digita" no ar        |
| Só a **mão direita**        | Gestos **abrem programas** (Bloco de Notas, Chrome, Calculadora) |
| **As duas mãos**            | Um **quadro de desenho**: uma mão desenha, a outra escolhe a cor |

Ao sair, o texto digitado é salvo em `texto_digitado.txt` e o desenho em `quadro.png`.

---

## 📚 Sumário

1. [Conceitos por trás do projeto](#-1-conceitos-por-trás-do-projeto)
2. [Estrutura de arquivos](#-2-estrutura-de-arquivos)
3. [Pré-requisitos](#-3-pré-requisitos)
4. [Passo a passo para executar](#-4-passo-a-passo-para-executar)
5. [Como usar: guia de gestos](#-5-como-usar-guia-de-gestos)
6. [Como o código funciona](#-6-como-o-código-funciona)
7. [Problemas comuns](#-7-problemas-comuns)
8. [Ideias de exercícios](#-8-ideias-de-exercícios)

---

## 🧠 1. Conceitos por trás do projeto

### O que é Visão Computacional?
É a área da computação que ensina o computador a **"enxergar"** e interpretar imagens. Para o computador, uma imagem é apenas uma **matriz de números** (pixels). Cada pixel colorido tem 3 valores: azul, verde e vermelho.

### Bibliotecas utilizadas

| Biblioteca   | Para que serve no projeto |
|--------------|---------------------------|
| **OpenCV** (`cv2`) | Ler a webcam, desenhar retângulos/textos/círculos e mostrar as janelas |
| **MediaPipe** (`mediapipe`) | Modelo de Inteligência Artificial do Google que **detecta mãos** e devolve 21 pontos de cada mão |
| **NumPy** (`numpy`) | Criar a imagem branca do quadro de desenho (uma matriz de números) |
| **pynput** | Simular o aperto de teclas reais no computador |
| **os** / **time** | Abrir/fechar programas do Windows e fazer pequenas pausas |

### Os 21 pontos da mão (landmarks)
O MediaPipe encontra **21 pontos** em cada mão. Os mais importantes aqui são as **pontas dos dedos**:

```
        8   12  16  20        ← pontas dos dedos
        |   |   |   |
        6   10  14  18        ← articulações (usadas para comparar)
   4    |   |   |   |
    \   5---9---13--17
     \  |            |
      2-1------------0        ← 0 = pulso
```

| Ponto | Dedo      |
|-------|-----------|
| 4     | Polegar   |
| 8     | Indicador |
| 12    | Médio     |
| 16    | Anelar    |
| 20    | Mínimo    |

Cada ponto tem coordenadas **x** (horizontal), **y** (vertical) e **z** (profundidade: quanto mais negativo, mais perto da câmera).

### Como o programa sabe se um dedo está levantado?
Na imagem, o **y cresce para baixo**. Então, se a ponta do dedo tem um **y menor** que a articulação dele, a ponta está **acima** → o dedo está **levantado**.

```python
if ponta.y < articulacao.y:   # ponta acima da articulação
    dedo levantado
```

> ⚠️ O polegar **não** é verificado. A lista de dedos sempre tem 4 posições: `[indicador, médio, anelar, mínimo]`.

---

## 📁 2. Estrutura de arquivos

```
MT_visao_computacional/
├── deteccao_maos.py        ← programa principal (é ele que você executa)
├── requirements.txt        ← lista de bibliotecas necessárias
├── README.md               ← este guia
├── texto_digitado.txt      ← gerado ao sair: texto do teclado virtual
├── quadro.png              ← gerado ao sair: desenho feito no quadro
└── venv/                   ← ambiente virtual Python (criado no Passo 2)
```

---

## 🧰 3. Pré-requisitos

- **Windows 10/11** (o projeto abre o Bloco de Notas, Chrome e Calculadora do Windows).
- **Webcam** funcionando.
- **Python 3.11** (recomendado). Baixe em <https://www.python.org/downloads/>.
  - Na instalação, marque a opção **"Add Python to PATH"**.

> ⚠️ **Versão do Python importa!** O MediaPipe 0.10.21 funciona com Python 3.9 a 3.12. Com Python 3.13 ou mais novo a instalação pode falhar.

Para conferir sua versão, abra o **PowerShell** e digite:

```powershell
python --version
```

---

## 🚀 4. Passo a passo para executar

### Passo 1 — Abrir o terminal na pasta do projeto
No VS Code/Cursor: menu **Terminal → New Terminal**. Ou, no Explorador de Arquivos, abra a pasta, clique na barra de endereço, digite `powershell` e aperte **Enter**.

Confirme que está na pasta certa:

```powershell
cd "C:\BRAZ CUBAS\2026_2\Algoritmos e Pensamento Computacional\MT_visao_computacional"
```

> 💡 As aspas são necessárias porque o caminho tem espaços.

### Passo 2 — Criar o ambiente virtual
Um **ambiente virtual** é uma "caixinha" isolada onde ficam as bibliotecas deste projeto, sem bagunçar o resto do computador.

```powershell
python -m venv venv
```

Isso cria uma pasta chamada `venv`. Ela é feita **uma única vez**; nas próximas execuções basta ativá-la.

> ℹ️ A pasta `venv` não deve ser copiada entre computadores nem enviada para o GitHub. Quem baixar o projeto cria a própria `venv` e instala as bibliotecas com o `requirements.txt`.

### Passo 3 — Ativar o ambiente virtual

```powershell
.\venv\Scripts\Activate.ps1
```

Se deu certo, aparece **`(venv)`** no começo da linha do terminal:

```
(venv) PS C:\BRAZ CUBAS\...\MT_visao_computacional>
```

> ❗ Se aparecer um erro de **"execução de scripts desabilitada"**, rode uma vez o comando abaixo e tente ativar de novo:
> ```powershell
> Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned
> ```
> Usando o **Prompt de Comando (cmd)** em vez do PowerShell, ative com: `venv\Scripts\activate.bat`

### Passo 4 — Instalar as bibliotecas

```powershell
python -m pip install --upgrade pip
pip install -r requirements.txt
```

Aguarde; o MediaPipe é grande e pode demorar alguns minutos.

### Passo 5 — Executar o programa

```powershell
python deteccao_maos.py
```

Duas janelas vão abrir:
- **Imagem** → a sua webcam com as marcações das mãos.
- **Quadro** → a folha branca de desenho.

### Passo 6 — Encerrar
Clique na janela **Imagem** e aperte **ESC**. Os arquivos `texto_digitado.txt` e `quadro.png` serão salvos na pasta do projeto.

### Resumo rápido (para as próximas vezes)
Depois da primeira instalação, basta:

```powershell
cd "C:\BRAZ CUBAS\2026_2\Algoritmos e Pensamento Computacional\MT_visao_computacional"
.\venv\Scripts\Activate.ps1
python deteccao_maos.py
```

---

## 🖐️ 5. Como usar: guia de gestos

> 💡 **Dicas para funcionar bem:** ambiente bem iluminado, fundo sem muita bagunça, mão inteira aparecendo na câmera, a uns 50–80 cm de distância. A imagem é espelhada, como um espelho mesmo.
>
> Se o programa confundir mão esquerda e direita na sua webcam, é só trocar de mão.

### ⌨️ Modo 1 — Teclado virtual (apenas a mão **esquerda**)

1. Mostre **só a mão esquerda**. Um teclado aparece no canto superior esquerdo.
2. Mova a **ponta do indicador** sobre uma tecla → ela fica **verde**.
3. **Empurre o dedo em direção à câmera** → a tecla fica **azul-clara** e a letra é digitada.
   - No canto superior direito aparece `Distancia camera`. A tecla é "apertada" quando esse valor fica **menor que -85**.
4. O texto aparece na barra branca abaixo do teclado.

| Gesto da mão esquerda                    | Efeito                         |
|------------------------------------------|--------------------------------|
| Indicador sobre a tecla                  | Seleciona (verde)              |
| Aproximar o indicador da câmera          | Digita a letra                 |
| Até 1 dedo levantado                     | Teclado em **minúsculas**      |
| 2 ou mais dedos levantados               | Teclado em **MAIÚSCULAS**      |
| Só o **mínimo** levantado 🤙              | Apaga a última letra da barra  |

> ⚠️ **Atenção:** a letra também é enviada como **tecla de verdade** para o programa que estiver em foco (via `pynput`). Experimente abrir o Bloco de Notas e digitar nele com o dedo! Mas cuidado com o que está aberto.

### 🚀 Modo 2 — Atalhos de programas (apenas a mão **direita**)

| Gesto da mão direita                      | Ação                         |
|-------------------------------------------|------------------------------|
| ☝️ Só o indicador                          | Abre o **Bloco de Notas**    |
| ✌️ Indicador + médio                       | Abre o **Google Chrome**     |
| 🤟 Indicador + médio + anelar              | Abre a **Calculadora**       |
| ✊ Mão fechada                              | Fecha o **Bloco de Notas**   |
| 🤘 Indicador + mínimo ("rock")             | **Encerra** o programa       |

> Cada programa só é aberto **uma vez** por execução (o código guarda isso em variáveis como `bloco_notas = True`). O Bloco de Notas pode ser reaberto depois de fechado com a mão fechada.
>
> O Chrome precisa estar instalado em `C:\Program Files\Google\Chrome\Application\chrome.exe`.

### 🎨 Modo 3 — Quadro de desenho (as **duas mãos**)

- Uma mão é o **pincel** (a primeira detectada pelo MediaPipe).
- A outra mão é a **paleta de cores**.

| Dedos levantados na mão da paleta | Cor / ação                 |
|-----------------------------------|----------------------------|
| 1 dedo                            | 🔵 Azul                    |
| 2 dedos                           | 🟢 Verde                   |
| 3 dedos                           | 🔴 Vermelho                |
| 4 dedos                           | ⬜ Branco (funciona como **borracha**) |
| Mão fechada                       | 🧽 **Limpa** todo o quadro |

Na mão do pincel:
- **Só o indicador levantado** → desenha.
- Qualquer outro gesto → para de desenhar (levanta o pincel).
- **Aproximar a mão da câmera** deixa o traço **mais grosso**.

---

## 🔍 6. Como o código funciona

### Visão geral (fluxograma)

```
 ┌───────────────────────┐
 │ Configurações iniciais│  cores, webcam 1280x720, teclado, quadro branco
 └──────────┬────────────┘
            ▼
 ┌───────────────────────┐
 │  Lê imagem da webcam  │◄─────────────────────┐
 │  e espelha (flip)     │                      │
 └──────────┬────────────┘                      │
            ▼                                   │
 ┌───────────────────────┐                      │
 │ MediaPipe detecta as  │                      │
 │ mãos (21 pontos cada) │                      │
 └──────────┬────────────┘                      │
            ▼                                   │
     Quantas mãos?                              │
   ┌────────┼─────────────┐                     │
   ▼ 1 esquerda  ▼ 1 direita   ▼ 2 mãos         │
 Teclado    Atalhos       Quadro de desenho     │
   └────────┴──────┬──────┘                     │
                   ▼                            │
        Mostra as janelas  ── ESC? ── não ──────┘
                   │ sim
                   ▼
   Salva texto_digitado.txt e quadro.png
```

### Principais funções

**`encontra_coordenadas_maos(imagem)`**
1. Converte a imagem de **BGR para RGB** (o OpenCV usa BGR e o MediaPipe espera RGB).
2. Pede ao MediaPipe para processar a imagem.
3. Converte os 21 pontos de cada mão de valores entre 0 e 1 para **pixels** (multiplicando pela resolução).
4. Guarda se a mão é `"Left"` ou `"Right"`.
5. Desenha o "esqueleto" da mão na imagem.
6. Retorna a imagem e uma lista de mãos, onde cada mão é um dicionário:
   ```python
   {"coordenadas": [(x, y, z), ... 21 pontos], "lado": "Left"}
   ```

**`dedos_levantados(mao)`**
Retorna uma lista com 4 valores `True`/`False`, por exemplo:
```python
[True, True, False, False]   # indicador e médio levantados ✌️
```
Comparar essa lista com um padrão é o que permite reconhecer cada gesto:
```python
if info_dedos_mao1 == [True, False, False, True]:   # 🤘
    break
```

**`imprime_botoes(imagem, posicao, letra, ...)`**
Desenha uma tecla do teclado virtual: retângulo preenchido, borda azul e a letra no meio.

### Detalhes interessantes

- **Cores no OpenCV são BGR**, não RGB. Por isso `AZUL = (255, 0, 0)` e `VERMELHO = (0, 0, 255)`.
- **Detecção de "clique" no teclado**: a tecla só é considerada pressionada quando o indicador está dentro do quadrado da tecla **e** a profundidade `z` é menor que `-85`. Um `contador` espera alguns quadros antes de registrar a letra, para evitar repetições.
- **O teclado é uma matriz** (lista de listas). Dois `for` aninhados calculam a posição de cada tecla:
  `x = offset + coluna * 80` e `y = offset + linha * 80`.
- **Desenho com linhas**: o quadro guarda a posição anterior do dedo (`x_quadro, y_quadro`) e liga ela à posição atual com `cv2.line`. Assim o traço fica contínuo.
- **Sobreposição**: `cv2.addWeighted` mistura a imagem da webcam com o quadro (20% de transparência) para você ver o desenho sobre o vídeo.

---

## 🛠️ 7. Problemas comuns

| Problema | Causa provável | Solução |
|----------|----------------|---------|
| `ModuleNotFoundError: No module named 'cv2'` (ou `mediapipe`) | Ambiente virtual não ativado ou bibliotecas não instaladas | Ative com `.\venv\Scripts\Activate.ps1` e rode `pip install -r requirements.txt` |
| `AttributeError: module 'mediapipe' has no attribute 'solutions'` | Versão nova do MediaPipe, que removeu `mp.solutions` | `pip install mediapipe==0.10.21` |
| Erro ao instalar o MediaPipe | Python muito novo (3.13+) | Instale o Python 3.11 e recrie o `venv` |
| Erro com NumPy 2.x | Incompatibilidade de versões | `pip install "numpy<2"` |
| Janela preta / erro em `cv2.cvtColor` | Webcam não encontrada ou em uso por outro app (Teams, Zoom...) | Feche os outros apps. Se tiver mais de uma câmera, troque `cv2.VideoCapture(0)` por `cv2.VideoCapture(1)` |
| "Execução de scripts desabilitada" ao ativar o venv | Política de segurança do PowerShell | `Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned` |
| Chrome não abre | Instalado em outro caminho | Ajuste o caminho na linha do `os.startfile(...chrome.exe)` |
| Teclas não são "apertadas" | Não chega a `z < -85` | Aproxime mais o dedo da câmera ou mude o valor `-85` no código (ex.: `-60`) |
| Mão não é detectada | Pouca luz ou mão cortada | Melhore a iluminação e mostre a mão inteira |
| ESC não fecha | Foco em outra janela | Clique na janela **Imagem** antes de apertar ESC |

---

## 🧪 8. Ideias de exercícios

1. **Adicionar um gesto novo**: fazer a mão direita com `[False, True, True, True]` abrir o Paint (`mspaint.exe`).
2. **Contar o polegar**: o polegar dobra para o lado, então compare o eixo **x** dos pontos 4 e 3 em vez do y.
3. **Nova cor no quadro**: trocar o branco por amarelo `(0, 255, 255)` e criar uma borracha separada.
4. **Tecla de apagar de verdade**: enviar `Key.backspace` do `pynput` quando o gesto de apagar for feito.
5. **Ajustar a sensibilidade**: transformar o `-85` em uma constante `LIMIAR_CLIQUE` no topo do arquivo.
6. **Salvar com data e hora**: gerar `quadro_2026-11-04_08-41.png` usando o módulo `datetime`.

---

## 📖 Referências

- [MediaPipe Hands – documentação](https://mediapipe.readthedocs.io/en/latest/solutions/hands.html)
- [OpenCV – documentação Python](https://docs.opencv.org/4.x/d6/d00/tutorial_py_root.html)
- [pynput – documentação](https://pynput.readthedocs.io/)
