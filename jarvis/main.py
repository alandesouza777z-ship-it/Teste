"""J.A.R.V.I.S. — assistente pessoal por voz.

Uso:
    python main.py           # modo voz: diga "Jarvis, ..." para falar com ele
    python main.py --texto   # modo texto, para testar sem microfone
"""

import os
import sys

from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env"))

from cerebro import NOME_USUARIO, Cerebro  # noqa: E402
from ferramentas import confirmacao  # noqa: E402

PALAVRA_ATIVACAO = os.getenv("JARVIS_PALAVRA_ATIVACAO", "jarvis").lower()
DESPEDIDAS = ("desligar jarvis", "jarvis desligar", "até logo jarvis", "encerrar jarvis")
JANELA_CONVERSA = 6  # segundos esperando continuação sem precisar dizer "Jarvis" de novo


def saudacao() -> str:
    import datetime

    hora = datetime.datetime.now().hour
    periodo = "Bom dia" if hora < 12 else "Boa tarde" if hora < 18 else "Boa noite"
    return f"{periodo}, {NOME_USUARIO}. Todos os sistemas operacionais. Em que posso ajudar?"


def modo_texto(cerebro: Cerebro) -> None:
    print(f"JARVIS: {saudacao()}  (digite 'sair' para encerrar)")
    while True:
        try:
            pedido = input("Você > ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if pedido.lower() in ("sair", "exit", "quit"):
            break
        if pedido:
            cerebro.responder(pedido, lambda texto: print(f"JARVIS: {texto}"))
    print(f"JARVIS: Até logo, {NOME_USUARIO}.")


def modo_voz(cerebro: Cerebro) -> None:
    import voz

    def perguntar_por_voz(pergunta: str) -> str:
        voz.falar(pergunta)
        resposta = voz.ouvir(tempo_limite=8, limite_frase=5)
        print(f"Você: {resposta}")
        return resposta

    confirmacao.perguntar = perguntar_por_voz

    voz.falar(saudacao())
    em_conversa = False
    while True:
        frase = voz.ouvir(tempo_limite=JANELA_CONVERSA if em_conversa else None)
        if not frase:
            em_conversa = False
            continue
        print(f"Você: {frase}")
        minuscula = frase.lower()

        if any(d in minuscula for d in DESPEDIDAS):
            voz.falar(f"Desligando. Até logo, {NOME_USUARIO}.")
            return

        if PALAVRA_ATIVACAO in minuscula:
            pedido = minuscula.split(PALAVRA_ATIVACAO, 1)[1].strip(" ,.!?")
            if not pedido:
                voz.falar(f"Pois não, {NOME_USUARIO}?")
                pedido = voz.ouvir(tempo_limite=8)
                print(f"Você: {pedido}")
        elif em_conversa:
            pedido = frase
        else:
            continue

        if pedido:
            cerebro.responder(pedido, voz.falar)
            em_conversa = True


def main() -> None:
    if not os.getenv("ANTHROPIC_API_KEY"):
        sys.exit("Defina ANTHROPIC_API_KEY no arquivo .env (veja .env.example).")
    cerebro = Cerebro()
    try:
        if "--texto" in sys.argv:
            modo_texto(cerebro)
        else:
            modo_voz(cerebro)
    except KeyboardInterrupt:
        print(f"\nJARVIS: Até logo, {NOME_USUARIO}.")


if __name__ == "__main__":
    main()
