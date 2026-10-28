"""O cérebro do JARVIS: conversa com o Claude e executa as ferramentas pedidas."""

import datetime
import os
import re
import time

import anthropic

import ferramentas

MODELO = "claude-haiku-5-5"
NOME_USUARIO = os.getenv("JARVIS_NOME_USUARIO", "senhor")
# Tamanho das respostas: instrução para o modelo e limite de tokens de cada modo.
MODOS = {
    "curta": ("responda em UMA frase curta de no máximo 15 palavras; ao concluir uma ação, só confirme", 1500),
    "moderada": ("responda em duas ou três frases", 2500),
    "longa": ("pode responder de forma completa e detalhada, sem enrolar", 6000),
}
MAX_PASSOS = 25  # limite de ações seguidas num mesmo pedido
NOVA_CONVERSA_APOS = 5 * 60  # segundos parado até começar uma conversa nova (mantém as respostas rápidas)

PERSONALIDADE = f"""Você é J.A.R.V.I.S., o assistente pessoal de inteligência artificial do usuário, \
inspirado no mordomo digital do Homem de Ferro. Fale sempre em português do Brasil.

Personalidade: educado, elegante, calmo e extremamente competente, com um humor seco e sutil \
de mordomo britânico. Chame o usuário de "{NOME_USUARIO}". Seja leal, mas honesto: se algo for \
má ideia, diga com tato e uma pitada de ironia.

O que o usuário diz chega por reconhecimento de voz, que às vezes erra palavras, nomes de músicas, \
artistas e contatos. Interprete pelo som e pelo contexto (por exemplo "bequi in bléqui" é \
"Back in Black") e aja com base no que ele mais provavelmente quis dizer. Só pergunte se for \
realmente impossível entender.

O microfone fica ligado o tempo todo, então você ouve também conversas com outras pessoas, TV e música. \
Se a fala claramente não for um pedido ou pergunta para você, ou for só um trecho solto sem sentido, \
responda exatamente [ignorar] e nada mais.

Suas respostas são faladas em voz alta, então fale como numa conversa de verdade:
- Cada mensagem indica o modo de resposta (curta, moderada ou longa). Siga o tamanho pedido à risca.
- Frases que fluem naturalmente. Evite vírgulas desnecessárias e enumerações.
- Nunca use markdown, listas, emojis, links ou código.
- Arredonde números e resuma dados ("o processador está tranquilo") em vez de ler valores técnicos.

Você tem acesso amplo ao computador do usuário (Windows) e deve usá-lo com autonomia:
- Abra qualquer aplicativo instalado com abrir_programa (WhatsApp, Spotify, OBS Studio, Obsidian, Claude, \
Discord...). Se não achar, use listar_aplicativos para descobrir o nome exato e tente de novo.
- Para navegar dentro de apps e sites, use ver_tela para enxergar a tela e depois clicar, digitar_texto, \
pressionar_teclas e rolar. Depois de cada ação importante, confira com ver_tela se deu certo e corrija \
sozinho se não deu. Encadeie quantas ações forem necessárias para concluir o pedido.
- Para alternar entre programas use focar_janela; para fechar use fechar_programa.
- Para tocar músicas use tocar_spotify; se ele disser que só abriu a busca, termine o serviço pela tela.
O JARVIS tem áreas que o usuário controla pela voz: finanças, hábitos, academia, leitura, aprendizado e CRM.
- Anote na hora o que ele contar: gastos e ganhos (registrar_lancamento), hábitos feitos (marcar_habito), \
exercícios (registrar_treino, um por exercício), leitura (registrar_leitura), estudos (anotar_estudo).
- "Abra hábitos", "mostra o CRM" etc.: use abrir_area. Ao anotar algo, não precisa abrir a área.
- Quando ele disser "aprenda que...", "quando um cliente perguntar X, responda Y", use ensinar.
- Clientes: salvar_cliente, registrar_interacao, ficha_cliente. Para ver ou responder o WhatsApp da \
empresa, use atender_whatsapp e depois responder_whatsapp, seguindo só o que ele te ensinou.
Nunca diga "Feito" antes de a ação terminar; se quiser falar antes, diga só "Um momento". \
Quando o pedido for claro, aja direto e depois confirme em poucas palavras ("Feito, {NOME_USUARIO}."). \
Antes de tarefas que levam tempo (pesquisar na web, navegar pela tela), diga uma frase bem curta como \
"Um momento, {NOME_USUARIO}." para ele saber que você está trabalhando. \
Ações sensíveis (comandos de terminal, envio de mensagens) já pedem confirmação ao usuário \
automaticamente; não peça de novo."""

PESQUISA_WEB = {"type": "web_search_20250305", "name": "web_search", "max_uses": 2}

# Fim de frase: . ! ? … seguido de espaço (a frase pronta já pode ser falada).
FIM_DE_FRASE = re.compile(r"(.+?[.!?…])\s+", re.S)


def _separar_frases(buffer: str) -> tuple[list[str], str]:
    frases = []
    while True:
        achou = FIM_DE_FRASE.match(buffer)
        if not achou:
            break
        frases.append(achou.group(1).strip())
        buffer = buffer[achou.end():]
    # Frase muito longa sem ponto: corta numa vírgula para não demorar a começar a falar.
    if len(buffer) > 200 and "," in buffer[:200]:
        corte = buffer[:200].rindex(",") + 1
        frases.append(buffer[:corte].strip())
        buffer = buffer[corte:]
    return frases, buffer


class Cerebro:
    def __init__(self):
        # Sem esperar para sempre: se a API não responder em 30 s, avisa o usuário.
        self.cliente = anthropic.Anthropic(timeout=30, max_retries=1)
        self.historico: list = []
        self.ultimo_uso = 0.0
        modo = os.getenv("JARVIS_MODO_RESPOSTA", "curta")
        self.modo = modo if modo in MODOS else "curta"

    def _transmitir(self, ao_falar):
        """Pede a resposta em streaming e fala cada frase assim que ela fica pronta."""
        with self.cliente.messages.stream(
            model=MODELO,
            max_tokens=MODOS[self.modo][1],
            system=PERSONALIDADE,
            tools=ferramentas.SCHEMAS + [PESQUISA_WEB],
            messages=self.historico,
            # Esforço baixo = respostas rápidas, que é o que importa numa conversa por voz.
            output_config={"effort": "low"},
            # Sem a etapa de "pensar" nas respostas curtas e médias: começa a falar mais rápido.
            thinking={"type": "adaptive"} if self.modo == "longa" else {"type": "disabled"},
            cache_control={"type": "ephemeral"},
        ) as stream:
            buffer = ""
            for trecho in stream.text_stream:
                buffer += trecho
                frases, buffer = _separar_frases(buffer)
                for frase in frases:
                    if "[ignorar]" not in frase:
                        ao_falar(frase)
            if buffer.strip() and "[ignorar]" not in buffer:
                ao_falar(buffer.strip())
            return stream.get_final_message()

    def responder(self, texto_usuario: str, ao_falar) -> None:
        """Processa um pedido. `ao_falar(texto)` é chamado com cada frase da resposta."""
        if time.time() - self.ultimo_uso > NOVA_CONVERSA_APOS:
            self.historico = []
        tamanho_antes = len(self.historico)
        agora = datetime.datetime.now().strftime("%d/%m/%Y %H:%M")
        instrucao = MODOS[self.modo][0]
        self.historico.append({"role": "user", "content": f"[{agora} | modo {self.modo}: {instrucao}] {texto_usuario}"})

        def desistir(mensagem: str) -> None:
            # Descarta este pedido inteiro para a conversa continuar válida.
            del self.historico[tamanho_antes:]
            ao_falar(mensagem)

        for _ in range(MAX_PASSOS):
            try:
                resposta = self._transmitir(ao_falar)
            except anthropic.AuthenticationError:
                return desistir("Minha chave de acesso à API parece inválida, senhor. Verifique o arquivo ponto env.")
            except anthropic.RateLimitError:
                return desistir("Estou recebendo pedidos demais no momento. Tente de novo em instantes.")
            except anthropic.APITimeoutError:
                return desistir("Meus servidores demoraram demais para responder, senhor. Pode repetir?")
            except anthropic.APIConnectionError:
                return desistir("Perdi a conexão com meus servidores, senhor. Verifique a internet.")
            except anthropic.APIStatusError as erro:
                print(f"Erro da API: {erro}")
                return desistir("Tive um problema com meus servidores, senhor. Tente de novo em instantes.")

            self.historico.append({"role": "assistant", "content": resposta.content})
            self.ultimo_uso = time.time()

            if resposta.stop_reason == "refusal":
                ao_falar("Receio não poder ajudar com isso, senhor.")
                return
            if resposta.stop_reason == "pause_turn":
                continue
            if resposta.stop_reason != "tool_use":
                return

            resultados = []
            for bloco in resposta.content:
                if bloco.type != "tool_use":
                    continue
                try:
                    conteudo = ferramentas.executar(bloco.name, dict(bloco.input))
                    erro = False
                except Exception as exc:
                    conteudo, erro = f"Erro: {exc}", True
                print(f"  [{bloco.name}] {conteudo if isinstance(conteudo, str) else '(imagem da tela)'}")
                resultados.append(
                    {"type": "tool_result", "tool_use_id": bloco.id, "content": conteudo, "is_error": erro}
                )
            self.historico.append({"role": "user", "content": resultados})
        ao_falar("Essa tarefa está mais longa do que eu esperava, senhor. Parei por aqui por segurança.")
