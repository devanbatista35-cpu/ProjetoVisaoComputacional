# Projeto de Visão Computacional

Aplicação interativa que usa a webcam para detectar mãos e controlar funcionalidades do computador por gestos. O projeto combina **Python**, **OpenCV** e **MediaPipe** para reconhecer movimentos em tempo real.

## Funcionalidades

- **Pedra, papel e tesoura:** jogue contra o avatar usando gestos.
- **Conversa com o avatar:** responda à pergunta “Tudo bem?” com um joinha e, em seguida, faça o avatar dormir.
- **Quadro de desenho:** desenhe com uma mão e selecione cores com a outra.
- **Modo navegador:** controle o cursor com a mão direita e use o teclado virtual com a mão esquerda.

## Requisitos

- Windows 10 ou 11.
- Python 3.11 ou 3.12.
- Webcam conectada e funcionando.
- Google Chrome instalado para a experiência recomendada. Se ele não for encontrado no caminho configurado, o programa tenta abrir o navegador padrão.

> A versão do MediaPipe especificada pelo projeto é `0.10.21`. Se houver problemas de instalação, confirme que está usando uma versão compatível do Python (3.9 a 3.12).

## Instalação

Abra o PowerShell na pasta do projeto e execute:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

Se o PowerShell bloquear a ativação do ambiente virtual, use o Prompt de Comando:

```cmd
.venv\Scripts\activate.bat
```

## Como executar

Com o ambiente virtual ativado:

```powershell
python main.py
```

O programa abre a janela de vídeo. Para obter melhores resultados, mantenha a mão inteira visível, use iluminação adequada e evite fundos muito carregados.

## Controles e gestos

Os gestos principais são reconhecidos com a **mão direita**. Segure o gesto por aproximadamente 0,4 segundo para iniciar o modo correspondente.

| Gesto | Ação |
|---|---|
| Indicador levantado | Inicia pedra, papel e tesoura |
| Indicador, médio e anelar levantados | Inicia a conversa com o avatar |
| Indicador e médio levantados | Abre o modo navegador |
| Duas mãos abertas por 1 segundo | Abre a confirmação do quadro de desenho |
| Sinal de rock mantido por cerca de 0,8 segundo | Encerra o programa |

### Pedra, papel e tesoura

Faça um gesto de **OK** para iniciar a rodada. Durante a contagem, mostre pedra (punho fechado), papel (quatro dedos estendidos) ou tesoura (indicador e médio estendidos).

### Conversa com o avatar

Faça um **joinha** para responder. Quando solicitado, feche a mão direita para o avatar dormir.

### Quadro de desenho

Confirme a abertura fazendo **OK**. Com uma mão, desenhe mantendo o indicador estendido e o médio dobrado. Com duas mãos, a mão à esquerda da imagem seleciona a cor:

| Dedos levantados na mão de seleção | Ação |
|---|---|
| 1 | Azul |
| 2 | Verde |
| 3 | Vermelho |
| 4 | Borracha |
| Punho fechado | Limpa o quadro |

Use `+` ou `-` para alterar a espessura do pincel. Passe a mão aberta da direita para a esquerda para voltar à tela principal.

### Modo navegador

- **Mão direita:** move o cursor; aproxime polegar e indicador para clicar. Mantendo a pinça, é possível arrastar.
- **Mão esquerda:** mova o indicador sobre uma tecla do painel virtual e faça pinça para digitá-la.
- Para digitar, clique primeiro na janela do navegador para deixá-la em foco.
- O navegador é aberto maximizado. A janela do programa fica reduzida no canto inferior direito.
- Abra e feche a mão para voltar à tela principal. O gesto de deslizar a mão aberta para a esquerda também retorna.

O teclado virtual envia teclas para a janela que estiver em foco. Tenha cuidado com o conteúdo digitado e com os aplicativos ativos.

## Arquivos gerados

- `quadro.png`: desenho salvo ao sair do modo de quadro.
- `texto_digitado.txt`: conteúdo digitado no teclado virtual, salvo ao encerrar o programa.
- `videos/_audio/`: arquivos WAV extraídos dos vídeos do avatar e reutilizados nas próximas execuções.

Os arquivos de saída são gravados no diretório de trabalho de onde `main.py` foi iniciado.

## Estrutura do projeto

```text
ProjetoVisaoComputacional/
├── main.py                  # Inicialização e loop principal
├── requirements.txt         # Dependências Python
├── modulos/
│   ├── detector_maos.py     # Captura e detecção das mãos
│   ├── gestos.py            # Reconhecimento e estabilização de gestos
│   ├── navegador.py         # Controle do mouse e modo navegador
│   ├── teclado_virtual.py   # Teclado virtual
│   ├── quadro.py            # Quadro de desenho
│   ├── jogo.py              # Pedra, papel e tesoura
│   ├── conversa.py          # Interação com o avatar
│   ├── avatar.py            # Reprodução de vídeo e áudio
│   ├── filtros.py           # Suavização do movimento
│   ├── janela.py            # Exibição e posicionamento da janela
│   ├── config.py            # Resolução, cores e parâmetros
│   └── ui.py                # Elementos visuais compartilhados
└── videos/                  # Vídeos do avatar e áudio extraído
```

## Solução de problemas

| Problema | O que verificar |
|---|---|
| `ModuleNotFoundError` ao iniciar | Ative `.venv` e instale as dependências com `python -m pip install -r requirements.txt`. |
| Erro ao instalar o MediaPipe | Verifique a versão do Python e tente usar Python 3.11 ou 3.12. |
| Webcam preta ou não detectada | Feche aplicativos que possam estar usando a câmera. Se necessário, altere o índice `0` de `VideoCapture` em `main.py`. |
| Gestos são reconhecidos incorretamente | Melhore a iluminação, mantenha a mão inteira no enquadramento e execute os gestos de forma clara. Pressione `I` para mostrar os dados de detecção. |
| Chrome não abre | Verifique `CHROME_PATH` em `modulos/config.py`. Se o Chrome não estiver nesse local, ajuste o caminho ou instale-o. |
| Teclado virtual digita na janela errada | Clique na janela do navegador antes de usar o teclado virtual. |
| `ESC` não encerra o programa | Dê foco à janela do programa e pressione `ESC` novamente. |

## Tecnologias

- [OpenCV](https://opencv.org/) — captura da webcam, processamento e interface visual.
- [MediaPipe](https://mediapipe.dev/) — detecção de mãos e pontos anatômicos.
- [NumPy](https://numpy.org/) — manipulação de imagens do quadro.
- [pynput](https://pynput.readthedocs.io/) — controle do mouse e envio de teclas.
- [Pygame](https://www.pygame.org/) e [imageio-ffmpeg](https://github.com/imageio/imageio-ffmpeg) — reprodução e preparação do áudio do avatar.
