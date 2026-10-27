# J.A.R.V.I.S. — seu assistente pessoal por voz

Um assistente estilo JARVIS do Homem de Ferro, que **ouve e fala com você**, controla o
**computador**, o **Spotify** e o **WhatsApp**, e pesquisa na internet. A inteligência vem do Claude
(API da Anthropic).

Exemplos do que você pode dizer:

- "Jarvis, toca Back in Black do AC/DC" / "Jarvis, pausa a música" / "Jarvis, próxima"
- "Jarvis, manda um WhatsApp pra minha mãe dizendo que chego às oito"
- "Jarvis, abre o Chrome" / "Jarvis, aumenta o volume" / "Jarvis, tira um print"
- "Jarvis, como está o computador?" (CPU, memória, bateria)
- "Jarvis, qual a cotação do dólar hoje?" (pesquisa na web)
- "Jarvis, desligar" encerra o assistente.

Depois que ele responde, você tem alguns segundos para continuar a conversa sem dizer "Jarvis" de novo.

## O aplicativo

Visual todo em **preto e branco**: uma **esfera 3D de partículas** no centro, anéis orbitais e um relógio.
A esfera muda conforme o que o JARVIS está fazendo:

- **aguardando**: respira devagar;
- **ouvindo**: fica mais clara e pulsa mais rápido;
- **processando**: escurece e gira mais rápido;
- **falando**: se deforma com os **graves da voz** em tempo real. Cada batida de grave solta uma
  onda de choque e dá um leve tremor na câmera.

Embaixo aparecem as legendas (o que você disse e o que ele respondeu) e uma caixa para digitar
pedidos. Quando ele pede confirmação, surgem os botões **Sim** e **Não** (também dá para responder
falando).

### Instalar como aplicativo no Windows

1. Instale o **Python 3.10+** em https://python.org (marque **"Add Python to PATH"**).
2. Baixe esta pasta, copie `.env.example` para `.env` e coloque sua chave da API.
3. Dê dois cliques em **`instalar_windows.bat`**.
4. Pronto: aparece o atalho **JARVIS** na Área de Trabalho, com o ícone da esfera.

O aplicativo fica em `dist\JARVIS\`. O `.env` e o `contatos.json` que ele usa ficam
**dentro dessa pasta**, ao lado do `JARVIS.exe`.

No macOS ou Linux, rode `bash instalar_mac_linux.sh`.

Para abrir sem empacotar (útil enquanto mexe no código): `python app.py`.

## Instalação pelo terminal (sem empacotar)

1. Instale o **Python 3.10+** (no Windows marque "Add Python to PATH").
2. Nesta pasta:
   ```bash
   python -m venv .venv
   # Windows: .venv\Scripts\activate    macOS/Linux: source .venv/bin/activate
   pip install -r requirements.txt
   ```
   Se o `PyAudio` falhar: no Windows use `pip install pipwin && pipwin install pyaudio`;
   no macOS `brew install portaudio`; no Linux `sudo apt install portaudio19-dev`.
3. Copie `.env.example` para `.env` e coloque sua chave da API da Anthropic
   (crie em https://console.anthropic.com).
4. Rode:
   ```bash
   python app.py            # aplicativo com a esfera 3D
   python main.py           # só voz, no terminal
   python main.py --texto   # só texto, no terminal (para testar sem microfone)
   ```

## Custo

O JARVIS usa o modelo **Claude Haiku 5.5**, rápido e barato: cerca de um décimo de centavo de dólar
por pedido. Para trocar de modelo, mude `MODELO` em `cerebro.py`.

## Spotify

1. Entre em https://developer.spotify.com/dashboard e crie um app.
2. Em *Redirect URIs* cadastre `http://127.0.0.1:8888/callback`.
3. Copie o *Client ID* e o *Client Secret* para o `.env`.
4. Na primeira vez o navegador abre pedindo autorização — aceite.

Controlar a reprodução pela API exige **Spotify Premium**. Sem Premium, o JARVIS ainda consegue
pausar/pular usando as teclas de mídia do sistema.

## WhatsApp

Usa o **WhatsApp Web**: deixe seu navegador padrão logado em https://web.whatsapp.com.

1. Copie `contatos.example.json` para `contatos.json` e coloque nomes e números (com +55 e DDD).
2. Diga "Jarvis, manda mensagem pro João dizendo ...". Ele **sempre confirma antes de enviar**.

Enquanto envia, o JARVIS abre o WhatsApp Web, digita e fecha a aba — não mexa no mouse/teclado
durante esses segundos. Ler mensagens recebidas não é suportado (o WhatsApp não oferece API
oficial para contas pessoais).

## A voz

A voz padrão é a `pt-BR-AntonioNeural` (Microsoft, gratuita). Para ouvir outras opções, rode
`python testar_vozes.py` e coloque a escolhida em `JARVIS_VOZ` no `.env`. As vozes
"Multilingual" são as mais naturais. A personalidade (educado, irônico, te chama de "senhor")
está em `cerebro.py`.

Para soar natural, o JARVIS:
- tira vírgulas e travessões antes de falar, então não faz pausa a cada vírgula;
- começa a falar assim que a primeira frase da resposta fica pronta, e gera a próxima enquanto
  fala a atual;
- avisa "Um momento, senhor." antes de pesquisar na internet.

A voz do ator do filme não está incluída: ela pertence ao ator e ao estúdio.

## Entender a sua voz

- A palavra "Jarvis" é reconhecida mesmo quando o reconhecimento entende errado ("Jarbas",
  "Javis", "Jarvas"...).
- O JARVIS recebe as várias interpretações possíveis do que você falou e o Claude interpreta
  pelo som e pelo contexto (por exemplo "bequi in bléqui" vira "Back in Black").
- Fale normalmente, perto do microfone. Depois que ele responde, você tem 8 segundos para
  continuar sem dizer "Jarvis" de novo.

## Segurança

- **Comandos de terminal** e **mensagens de WhatsApp** sempre pedem sua confirmação ("sim") antes.
- O `.env` e o `contatos.json` ficam fora do git (estão no `.gitignore`).
- O reconhecimento de voz usa o serviço gratuito do Google; o que você fala depois de "Jarvis" vai
  para a API da Anthropic.

## Estrutura

| Arquivo | O que faz |
|---|---|
| `app.py` | Aplicativo com janela (pywebview) |
| `web/` | Interface: HTML, esfera 3D (Three.js) e análise de áudio |
| `assistente.py` | Laço principal: palavra de ativação, conversa, confirmações |
| `main.py` | Versão de terminal (voz ou texto) |
| `instalar_windows.bat` / `instalar_mac_linux.sh` | Geram o aplicativo e o atalho |
| `voz.py` | Ouvir (microfone → texto) e falar (texto → voz) |
| `cerebro.py` | Personalidade do JARVIS e conversa com o Claude |
| `ferramentas/computador.py` | Programas, sites, volume, mídia, print, sistema, comandos |
| `ferramentas/spotify.py` | Tocar, pausar, pular, volume, música atual |
| `ferramentas/whatsapp.py` | Enviar mensagens e abrir conversas |

Para dar um novo poder ao JARVIS, crie uma função em `ferramentas/` e adicione o schema na
lista `FERRAMENTAS` do módulo — ele passa a usá-la sozinho.
