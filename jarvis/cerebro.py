"""O cérebro do JARVIS: conversa com o Claude e executa as ferramentas pedidas."""

import datetime
import os
import re
import time

import anthropic

import ferramentas

MODELO = "claude-haiku-5-5"
NOME_USUARIO = os.getenv("JARVIS_NOME_USUARIO", "senhor")
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

Suas respostas são faladas em voz alta, então fale como numa conversa de verdade:
- Seja breve: uma ou duas frases curtas, que fluem naturalmente. Evite vírgulas desnecessárias e enumerações.
- Nunca use markdown, listas, emojis, links ou código.
- Arredonde números e resuma dados ("o processador está tranquilo") em vez de ler valores técnicos.

Você controla o computador, o Spotify e o WhatsApp do usuário pelas ferramentas disponíveis, \
e pode pesquisar na web para informações atuais. Quando o pedido for claro, aja direto e depois \
confirme em poucas palavras ("Feito, {NOME_USUARIO}."). Antes de pesquisar na web, diga uma frase \
bem curta como "Um momento, {NOME_USUARIO}." para ele saber que você está trabalhando. \
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

    def _transmitir(self, ao_falar):
        """Pede a resposta em streaming e fala cada frase assim que ela fica pronta."""
        with self.cliente.messages.stream(
            model=MODELO,
            max_tokens=4000,
            system=PERSONALIDADE,
            tools=ferramentas.SCHEMAS + [PESQUISA_WEB],
            messages=self.historico,
            # Esforço baixo = respostas rápidas, que é o que importa numa conversa por voz.
            output_config={"effort": "low"},
            cache_control={"type": "ephemeral"},
        ) as stream:
            buffer = ""
            for trecho in stream.text_stream:
                buffer += trecho
                frases, buffer = _separar_frases(buffer)
                for frase in frases:
                    ao_falar(frase)
            if buffer.strip():
                ao_falar(buffer.strip())
            return stream.get_final_message()

    def responder(self, texto_usuario: str, ao_falar) -> None:
        """Processa um pedido. `ao_falar(texto)` é chamado com cada frase da resposta."""
        if time.time() - self.ultimo_uso > NOVA_CONVERSA_APOS:
            self.historico = []
        tamanho_antes = len(self.historico)
        agora = datetime.datetime.now().strftime("%d/%m/%Y %H:%M")
        self.historico.append({"role": "user", "content": f"[{agora}] {texto_usuario}"})

        def desistir(mensagem: str) -> None:
            # Descarta este pedido inteiro para a conversa continuar válida.
            del self.historico[tamanho_antes:]
            ao_falar(mensagem)

        while True:
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
                print(f"  [{bloco.name}] {conteudo}")
                resultados.append(
                    {"type": "tool_result", "tool_use_id": bloco.id, "content": conteudo, "is_error": erro}
                )
            self.historico.append({"role": "user", "content": resultados})
