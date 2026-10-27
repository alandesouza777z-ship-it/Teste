"""J.A.R.V.I.S. no terminal (sem interface gráfica).

Uso:
    python main.py           # modo voz: diga "Jarvis, ..." para falar com ele
    python main.py --texto   # modo texto, para testar sem microfone

Para o aplicativo com a esfera 3D, use: python app.py
"""

import os
import sys

import config  # noqa: F401  (carrega o .env)
from assistente import Assistente, saudacao
from cerebro import NOME_USUARIO, Cerebro


def modo_texto() -> None:
    cerebro = Cerebro()
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


def modo_voz() -> None:
    import voz

    Assistente(falar=voz.falar).rodar()


def main() -> None:
    if not os.getenv("ANTHROPIC_API_KEY"):
        sys.exit("Defina ANTHROPIC_API_KEY no arquivo .env (veja .env.example).")
    try:
        modo_texto() if "--texto" in sys.argv else modo_voz()
    except KeyboardInterrupt:
        print(f"\nJARVIS: Até logo, {NOME_USUARIO}.")


if __name__ == "__main__":
    main()
