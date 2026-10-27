"""Registro das ferramentas que o JARVIS pode usar.

Cada módulo expõe FERRAMENTAS: lista de (schema, função). O schema segue o
formato de tools da API da Anthropic.
"""

from . import computador, navegador, spotify, whatsapp  # noqa: F401

_todas = computador.FERRAMENTAS + navegador.FERRAMENTAS + spotify.FERRAMENTAS + whatsapp.FERRAMENTAS

SCHEMAS = [schema for schema, _ in _todas]
FUNCOES = {schema["name"]: funcao for schema, funcao in _todas}


def executar(nome: str, argumentos: dict):
    funcao = FUNCOES.get(nome)
    if funcao is None:
        return f"Ferramenta desconhecida: {nome}"
    resultado = funcao(**argumentos)
    # Ferramentas como ver_tela devolvem blocos de conteúdo (imagem + texto) em vez de texto.
    return resultado if isinstance(resultado, list) else str(resultado)
