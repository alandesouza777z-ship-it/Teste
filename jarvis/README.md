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

## Instalação (Windows, macOS ou Linux)

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
   python main.py           # modo voz
   python main.py --texto   # modo texto (para testar sem microfone)
   ```

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

A voz padrão é a `pt-BR-AntonioNeural` (Microsoft, gratuita, masculina e calma), com o tom um
pouco mais grave. Troque em `JARVIS_VOZ` no `.env` — `en-GB-RyanNeural` dá o sotaque britânico de
mordomo. A personalidade (educado, irônico, te chama de "senhor") está em `cerebro.py` e
você pode editá-la à vontade.

A voz do ator do filme não está incluída: ela pertence ao ator e ao estúdio. Se quiser algo ainda
mais próximo, serviços como o ElevenLabs têm vozes no estilo "mordomo britânico" que podem ser
ligadas na função `falar` de `voz.py`.

## Segurança

- **Comandos de terminal** e **mensagens de WhatsApp** sempre pedem sua confirmação ("sim") antes.
- O `.env` e o `contatos.json` ficam fora do git (estão no `.gitignore`).
- O reconhecimento de voz usa o serviço gratuito do Google; o que você fala depois de "Jarvis" vai
  para a API da Anthropic.

## Estrutura

| Arquivo | O que faz |
|---|---|
| `main.py` | Laço principal: palavra de ativação, modo voz/texto |
| `voz.py` | Ouvir (microfone → texto) e falar (texto → voz) |
| `cerebro.py` | Personalidade do JARVIS e conversa com o Claude |
| `ferramentas/computador.py` | Programas, sites, volume, mídia, print, sistema, comandos |
| `ferramentas/spotify.py` | Tocar, pausar, pular, volume, música atual |
| `ferramentas/whatsapp.py` | Enviar mensagens e abrir conversas |

Para dar um novo poder ao JARVIS, crie uma função em `ferramentas/` e adicione o schema na
lista `FERRAMENTAS` do módulo — ele passa a usá-la sozinho.
