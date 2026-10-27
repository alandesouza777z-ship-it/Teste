"""WhatsApp pelo WhatsApp Web (o navegador precisa estar logado no web.whatsapp.com)."""

import json
import os
import re
import webbrowser
from urllib.parse import quote

from .computador import _schema
from .confirmacao import confirmar

ARQUIVO_CONTATOS = os.path.join(os.path.dirname(os.path.dirname(__file__)), "contatos.json")


def _contatos() -> dict:
    try:
        with open(ARQUIVO_CONTATOS, encoding="utf-8") as arquivo:
            return {nome.lower(): numero for nome, numero in json.load(arquivo).items()}
    except FileNotFoundError:
        return {}


def _numero(contato: str) -> str | None:
    if re.fullmatch(r"\+?[\d\s()-]{10,}", contato):
        digitos = re.sub(r"\D", "", contato)
        return "+" + (digitos if len(digitos) > 11 else "55" + digitos)
    return _contatos().get(contato.strip().lower())


def enviar_whatsapp(contato: str, mensagem: str) -> str:
    numero = _numero(contato)
    if not numero:
        nomes = ", ".join(_contatos()) or "nenhum"
        return f"Não conheço o contato '{contato}'. Contatos salvos: {nomes}. Peça o número ao usuário."
    if not confirmar(f"Enviar para {contato}: \"{mensagem}\"?"):
        return "O usuário cancelou o envio."
    try:
        import pywhatkit

        pywhatkit.sendwhatmsg_instantly(numero, mensagem, wait_time=15, tab_close=True, close_time=4)
        return f"Mensagem enviada para {contato}."
    except Exception as erro:
        return f"Falha ao enviar pelo WhatsApp Web: {erro}"


def abrir_conversa_whatsapp(contato: str) -> str:
    numero = _numero(contato)
    if not numero:
        return f"Não conheço o contato '{contato}'."
    webbrowser.open(f"https://web.whatsapp.com/send?phone={numero.lstrip('+')}&text={quote('')}")
    return f"Conversa com {contato} aberta."


def listar_contatos() -> str:
    contatos = _contatos()
    return ", ".join(contatos) if contatos else "Nenhum contato salvo em contatos.json."


FERRAMENTAS = [
    (_schema("enviar_whatsapp",
             "Envia uma mensagem de WhatsApp para um contato salvo (pelo nome) ou para um número. O usuário confirma antes.",
             {"contato": {"type": "string", "description": "Nome salvo em contatos.json ou número com DDD."},
              "mensagem": {"type": "string"}}, ["contato", "mensagem"]), enviar_whatsapp),
    (_schema("abrir_conversa_whatsapp", "Abre a conversa com um contato no WhatsApp Web.",
             {"contato": {"type": "string"}}, ["contato"]), abrir_conversa_whatsapp),
    (_schema("listar_contatos", "Lista os contatos salvos para o WhatsApp."), listar_contatos),
]
