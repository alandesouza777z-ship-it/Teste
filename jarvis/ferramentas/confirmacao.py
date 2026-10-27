"""Pergunta ao usuário antes de ações sensíveis (comandos, mensagens).

O main.py troca `perguntar` pela versão por voz ou por texto.
"""

SIM = ("sim", "pode", "confirmo", "confirma", "manda", "isso", "positivo", "claro", "s")


def _perguntar_texto(pergunta: str) -> str:
    return input(f"JARVIS: {pergunta} (sim/não) > ")


perguntar = _perguntar_texto


def confirmar(pergunta: str) -> bool:
    resposta = perguntar(pergunta).strip().lower()
    return any(resposta.startswith(p) for p in SIM)
