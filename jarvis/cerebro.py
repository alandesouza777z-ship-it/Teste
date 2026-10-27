"""O cérebro do JARVIS: conversa com o Claude e executa as ferramentas pedidas."""

import datetime
import os

import anthropic

import ferramentas

MODELO = "claude-haiku-5-5"
NOME_USUARIO = os.getenv("JARVIS_NOME_USUARIO", "senhor")

PERSONALIDADE = f"""Você é J.A.R.V.I.S., o assistente pessoal de inteligência artificial do usuário, \
inspirado no mordomo digital do Homem de Ferro. Fale sempre em português do Brasil.

Personalidade: educado, elegante, calmo e extremamente competente, com um humor seco e sutil \
de mordomo britânico. Chame o usuário de "{NOME_USUARIO}". Seja leal, mas honesto: se algo for \
má ideia, diga com tato e uma pitada de ironia.

Suas respostas são faladas em voz alta por um sintetizador, então:
- Responda em frases curtas e naturais, normalmente uma ou duas.
- Nunca use markdown, listas, emojis, links ou código na resposta.
- Escreva números e horários do jeito que se falam.

Você controla o computador, o Spotify e o WhatsApp do usuário pelas ferramentas disponíveis, \
e pode pesquisar na web para informações atuais. Quando o pedido for claro, aja direto e depois \
confirme em poucas palavras ("Feito, {NOME_USUARIO}."). Se faltar informação essencial, pergunte. \
Ações sensíveis (comandos de terminal, envio de mensagens) já pedem confirmação ao usuário \
automaticamente; não peça de novo."""

PESQUISA_WEB = {"type": "web_search_20250305", "name": "web_search", "max_uses": 3}


class Cerebro:
    def __init__(self):
        self.cliente = anthropic.Anthropic()
        self.historico: list = []

    def _chamar(self):
        return self.cliente.messages.create(
            model=MODELO,
            max_tokens=16000,
            system=PERSONALIDADE + f"\n\nAgora são {datetime.datetime.now():%d/%m/%Y %H:%M}.",
            tools=ferramentas.SCHEMAS + [PESQUISA_WEB],
            messages=self.historico,
            # Esforço baixo = respostas rápidas, que é o que importa numa conversa por voz.
            output_config={"effort": "low"},
        )

    def responder(self, texto_usuario: str, ao_falar) -> None:
        """Processa um pedido. `ao_falar(texto)` é chamado com cada trecho de resposta."""
        self.historico.append({"role": "user", "content": texto_usuario})
        while True:
            try:
                resposta = self._chamar()
            except anthropic.AuthenticationError:
                ao_falar("Minha chave de acesso à API parece inválida, senhor. Verifique o arquivo ponto env.")
                self.historico.pop()
                return
            except anthropic.RateLimitError:
                ao_falar("Estou recebendo pedidos demais no momento. Tente de novo em instantes.")
                self.historico.pop()
                return
            except anthropic.APIConnectionError:
                ao_falar("Perdi a conexão com meus servidores, senhor. Verifique a internet.")
                self.historico.pop()
                return

            self.historico.append({"role": "assistant", "content": resposta.content})

            if resposta.stop_reason == "refusal":
                ao_falar("Receio não poder ajudar com isso, senhor.")
                return

            texto = " ".join(b.text for b in resposta.content if b.type == "text").strip()
            if texto:
                ao_falar(texto)

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
