"""Registro das ferramentas que o JARVIS pode usar.

Cada módulo expõe FERRAMENTAS: lista de (schema, função). O schema segue o
formato de tools da API da Anthropic.
"""

from . import computador, spotify, whatsapp

_todas = computador.FERRAMENTAS + spotify.FERRAMENTAS + whatsapp.FERRAMENTAS

SCHEMAS = [schema for schema, _ in _todas]
FUNCOES = {schema["name"]: funcao for schema, funcao in _todas}


def executar(nome: str, argumentos: dict) -> str:
    funcao = FUNCOES.get(nome)
    if funcao is None:
        return f"Ferramenta desconhecida: {nome}"
    return str(funcao(**argumentos))
