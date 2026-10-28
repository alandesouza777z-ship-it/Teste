# J.A.R.V.I.S. — seu assistente pessoal por voz

Um assistente estilo JARVIS do Homem de Ferro, que **ouve e fala com você**, controla o
**computador**, o **Spotify** e o **WhatsApp**, e pesquisa na internet. A inteligência vem do Claude
(API da Anthropic).

Ele **ouve o tempo todo**: é só falar, sem precisar dizer "Jarvis". Para ele parar de ouvir,
clique no **botão de microfone** (ou `Ctrl+M`, ou diga "pare de me ouvir"). Conversas com
outras pessoas, TV e falas soltas são ignoradas. Com música tocando no Spotify, ele só atende
quando você chama "Jarvis" (para não confundir a letra da música com pedidos).

Exemplos do que você pode dizer:

- "Toca Back in Black do AC/DC" / "Pausa a música" / "Próxima"
- "Manda um WhatsApp pra minha mãe dizendo que chego às oito"
- "Abre o OBS" / "Fecha o Edge" / "Vai para o WhatsApp" / "Abre a pasta Downloads"
- "O que tem na minha tela?" / "Como está o computador?" / "Qual a cotação do dólar hoje?"
- "Modo respostas longas" / "Modo curto" — muda o tamanho das respostas
- "Desligar" encerra o assistente.

## Áreas

Abas no topo (ou pela voz: "abra hábitos", "mostra o CRM", "volta pro início"; `Esc` fecha):

| Área | O que guarda | Exemplos de voz |
|---|---|---|
| **Finanças** | receitas, despesas, saldo do mês, gastos por categoria | "gastei 50 reais no almoço", "recebi 2500 do cliente João", "quanto gastei esse mês?" |
| **Hábitos** | hábitos com os últimos 7 dias e sequência | "marquei o hábito de meditar", "como estão meus hábitos?" |
| **Academia** | exercícios, séries, carga, recordes | "fiz supino 4 de 10 com 60 quilos e agachamento 4 de 8 com 80" |
| **Leitura** | estante com progresso de cada livro | "comecei a ler O Poder do Hábito, 400 páginas", "li 20 páginas" |
| **Aprendizado** | o que o JARVIS sabe para atender clientes + seus estudos | "aprenda que a instalação custa 300 reais", "estudei 30 minutos de inglês" |
| **CRM** | funil de clientes (lead, negociação, cliente, perdido) com histórico | "cadastra a cliente Fernanda, telefone ..., em negociação de 1200 reais" |

Tudo fica salvo no seu computador, no arquivo `jarvis.db` (ao lado do `.env`). Dá também para
adicionar, marcar e excluir direto na tela.

## Atendimento no WhatsApp

Diga **"atenda o WhatsApp"** (ou clique em **Atender WhatsApp** no CRM). O JARVIS:

1. abre o WhatsApp Web numa janela própria do Chrome (na primeira vez, escaneie o QR Code em
   *Aparelhos conectados* no celular; depois a sessão fica salva);
2. lê as conversas não lidas, diz quem escreveu e o que quer;
3. escreve a resposta usando **só o que você ensinou** na área de Aprendizado e a ficha do cliente
   no CRM (clientes novos entram como *lead* automaticamente);
4. **lê a resposta e pergunta se pode enviar** (diga "sim" ou clique). Com
   `JARVIS_ATENDIMENTO=automatico` no `.env`, ele envia sem perguntar;
5. anota a conversa no histórico do cliente.

"Manda mensagem pro João dizendo..." também usa essa janela e encontra o telefone pelo CRM.

**Atenção:** o WhatsApp não tem integração oficial para contas comuns e proíbe automações em
massa. Use para responder seus clientes no dia a dia, não para disparos. Se o WhatsApp mudar o
site, essa parte pode precisar de ajuste.

## Velocidade

- **Reconhecimento de voz em ~0,3 s (recomendado):** crie uma chave grátis em
  https://console.groq.com/keys e coloque em `GROQ_API_KEY` no `.env`. Ele passa a usar o Whisper
  *large-v3-turbo* (o modelo grande, bem mais preciso que o do PC) e não precisa mais carregar
  nada no seu computador. Sem a chave, ele usa o Whisper local.
- Ele aprende os nomes dos seus hábitos, livros e clientes para reconhecê-los melhor.

- **Comandos instantâneos**: "abre o X", "fecha o X", "pausa", "próxima", "volta a música",
  "aumenta/diminui o volume", "silencia" e "que horas são" são feitos na hora, sem esperar a IA.
- Ele detecta **voz** (não volume): para de gravar meio segundo depois que você termina de falar,
  mesmo com ventilador ou barulho de fundo.
- Embaixo do estado aparece um **cronômetro** ("entender 0.4s · responder 1.1s"): quanto tempo levou
  para transcrever sua fala e para começar a responder.
- Se o seu PC demorar mais de 2,5 s para transcrever, ele troca sozinho para um modelo de voz mais leve.

## Tamanho das respostas

Nos botões **CURTA · MÉDIA · LONGA** ao lado da caixa de texto (ou pela voz):

- **Curta** (padrão): uma frase; ao fazer algo, só confirma ("Feito, senhor.").
- **Média**: duas ou três frases.
- **Longa**: explicações completas.

## O aplicativo

Janela sem bordas, em preto e branco, com brilho cinematográfico:

- **núcleo 3D**: esfera de 14 mil partículas com um cristal luminoso no centro;
- **HUD estilo Homem de Ferro**: anéis com marcações girando, órbitas em 3D e campo de estrelas;
- **espectro de áudio** em volta da esfera, que reage à voz do JARVIS;
- **painel de sistema** (relógio, processador, memória, disco, bateria) e **registro** das conversas;
- a câmera acompanha levemente o mouse, dando profundidade.

A esfera muda conforme o estado: aguardando, ouvindo (mais clara), processando (gira rápido) e
falando (deforma com os graves, com ondas de choque nas batidas).

## Abrir com palmas

Bata **duas palmas** e o JARVIS:

1. abre e já começa a tocar **Back in Black, do AC/DC** no Spotify (funciona sem Premium: ele
   abre a música e aperta o play sozinho);
2. abre no **Google Chrome** o **Claude** (claude.ai) e o sistema da **Vault**
   (vaultsistemas.com/hoje);
3. abre o **WhatsApp Web** e diz quantas **conversas com mensagens não lidas** você tem.

O número vem do título da aba do WhatsApp Web, que mostra quantas *conversas* têm mensagens
novas (não o total de mensagens). Deixe o Chrome logado no WhatsApp da empresa. Você também pode
perguntar a qualquer momento: "quantas mensagens não lidas eu tenho no WhatsApp?".
Os sites e o WhatsApp são configuráveis no `.env` (`JARVIS_PALMAS_SITES`, `JARVIS_PALMAS_WHATSAPP`). O detector
(`JARVIS-Palmas.exe`) roda escondido e inicia junto com o Windows. Enquanto o JARVIS está
aberto, ele não ouve palmas e solta o microfone.

- Não reconhece suas palmas? Aumente `JARVIS_PALMAS_SENSIBILIDADE` no `.env` (ex.: `1.5`).
- Abre sozinho com barulhos? Diminua (ex.: `0.7`).
- Outra música: troque `JARVIS_PALMAS_MUSICA` (copie o link da música no Spotify:
  Compartilhar → Copiar link, e use o código depois de `/track/` no formato `spotify:track:CODIGO`).
  Deixe vazio para abrir só o JARVIS.
- Para desligar de vez: `desligar_palmas.bat`.

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

A voz tem um **efeito JARVIS**: presença nítida, leve dobra metálica e ambiente curto de sala,
inspirado no assistente do filme. Desligue com `JARVIS_EFEITO_VOZ=0`.

- **Grátis (padrão):** vozes neurais da Microsoft. Rode `python testar_vozes.py` para comparar e
  coloque a escolhida em `JARVIS_VOZ`.
- **Premium (ElevenLabs, pago):** voz muito mais humana. Crie uma conta em elevenlabs.io, escolha
  na biblioteca uma voz grave de "mordomo britânico" e coloque `ELEVENLABS_API_KEY` e
  `ELEVENLABS_VOZ` no `.env`.

A voz do ator do filme (e do dublador brasileiro) não pode ser copiada: ela pertence a eles.

## Entender a sua voz

O JARVIS usa o **Whisper** (da OpenAI, código aberto), que roda **no seu computador**: entende
português muito melhor que o reconhecimento gratuito do Google e não precisa de internet para isso.

- Na primeira vez ele baixa o modelo (~500 MB). Até terminar, usa o Google.
- O microfone fica aberto o tempo todo e ele espera ~0,8 segundo de silêncio antes de considerar
  que você terminou.
- Se o PC tiver placa de vídeo NVIDIA, o Whisper roda nela (bem mais rápido).
- Ele conhece nomes como Spotify, WhatsApp, OBS, Obsidian e Claude, e entende "Jarvis" mesmo
  quando ouve "Jarbas" ou "Javis".
- PC lento? Use `JARVIS_WHISPER_MODELO=base` no `.env`. PC forte? `medium` é ainda mais preciso.

## Controle do computador

O JARVIS pode:

- abrir **qualquer aplicativo instalado** (ele lê a lista do menu Iniciar, incluindo apps da
  Microsoft Store como WhatsApp, Spotify e Claude);
- fechar programas, alternar entre janelas, maximizar, minimizar e mostrar a área de trabalho;
- **enxergar a tela**, clicar, digitar (com acentos), usar atalhos e rolar páginas, para navegar
  dentro de apps e sites e conferir se a tarefa deu certo;
- abrir pastas e arquivos e procurar arquivos pelo nome.

Comandos de terminal e mensagens de WhatsApp continuam pedindo confirmação.

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
| `palmas.py` | Detector de palmas que abre o JARVIS |
| `ferramentas/aplicativos.py` | Abrir, fechar e alternar aplicativos |
| `ferramentas/controle.py` | Ver a tela, clicar, teclas, pastas e arquivos |
| `ferramentas/computador.py` | Sites, volume, mídia, print, sistema, comandos |
| `dados.py` | Banco de dados das áreas (SQLite) |
| `web/areas.js` | Telas das áreas |
| `ferramentas/areas.py` | Comandos de voz das áreas |
| `ferramentas/whatsapp_atendimento.py` | Ler e responder clientes no WhatsApp Web |
| `ferramentas/navegador.py` | Chrome e WhatsApp Web (sites, conversas não lidas) |
| `ferramentas/spotify.py` | Tocar, pausar, pular, volume, música atual |
| `ferramentas/whatsapp.py` | Enviar mensagens e abrir conversas |

Para dar um novo poder ao JARVIS, crie uma função em `ferramentas/` e adicione o schema na
lista `FERRAMENTAS` do módulo — ele passa a usá-la sozinho.
