"""Comandos instantâneos: pedidos simples executados direto, sem esperar o Claude.

"Abre o Spotify", "pausa a música", "próxima", "aumenta o volume", "que horas são"...
Se o pedido não for um desses (ou não der certo), devolve None e o Claude cuida.
"""

import datetime
import re
import unicodedata

from cerebro import NOME_USUARIO
from ferramentas import aplicativos, computador

ARTIGOS = r"(?:o |a |os |as |um |uma |meu |minha )?"


def _limpar(texto: str) -> str:
    texto = "".join(c for c in unicodedata.normalize("NFD", texto.lower()) if unicodedata.category(c) != "Mn")
    texto = re.sub(r"[^a-z0-9 ]", " ", texto)
    texto = re.sub(r"\b(jarvis|por favor|pra mim|para mim|agora|ai)\b", " ", texto)
    return re.sub(r"\s+", " ", texto).strip()


def _hora() -> str:
    agora = datetime.datetime.now()
    return f"São {agora.hour} e {agora.minute:02d}, {NOME_USUARIO}." if agora.minute else f"São {agora.hour} em ponto, {NOME_USUARIO}."


def executar_atalho(pedido: str) -> str | None:
    texto = _limpar(pedido)
    if not texto or len(texto.split()) > 7:
        return None

    if re.fullmatch(r"(que horas sao|que hora e essa|me diz as horas|horas)", texto):
        return _hora()

    # Música (teclas de mídia: funcionam com Spotify, YouTube etc.)
    if re.fullmatch(r"(pausa|pausar|pause|para|parar|continua|continuar|despausa|play|solta)" + r"( " + ARTIGOS + r"(musica|som|spotify))?", texto):
        computador.midia("tocar_pausar")
        return f"Certo, {NOME_USUARIO}."
    if re.fullmatch(r"(proxima|pula|pular|passa|avanca)( " + ARTIGOS + r"(musica|faixa))?|proxima musica", texto):
        computador.midia("proxima")
        return f"Próxima, {NOME_USUARIO}."
    if re.fullmatch(r"(volta|voltar|anterior)( " + ARTIGOS + r"(musica|faixa))?|musica anterior", texto):
        computador.midia("anterior")
        return f"Voltando, {NOME_USUARIO}."

    # Volume
    if re.fullmatch(r"(aumenta|aumentar|sobe|subir|mais)( " + ARTIGOS + r"(volume|som))?( um pouco)?", texto) and re.search(r"volume|som|aumenta|sobe", texto):
        computador.controlar_volume("aumentar", 6)
        return f"Volume aumentado, {NOME_USUARIO}."
    if re.fullmatch(r"(diminui|diminuir|abaixa|abaixar|baixa|menos)( " + ARTIGOS + r"(volume|som))?( um pouco)?", texto) and re.search(r"volume|som|diminui|abaixa|baixa", texto):
        computador.controlar_volume("diminuir", 6)
        return f"Volume reduzido, {NOME_USUARIO}."
    if re.fullmatch(r"(muta|mutar|silencia|silenciar|tira o som|sem som)", texto):
        computador.controlar_volume("mudo")
        return f"Silenciado, {NOME_USUARIO}."

    # Abrir e fechar aplicativos
    abrir = re.fullmatch(r"(?:abre|abra|abrir|inicia|iniciar|executa|liga) " + ARTIGOS + r"(.+)", texto)
    if abrir and not re.match(r"(site|pagina|pasta|arquivo|link) ", abrir.group(1)):
        resultado = aplicativos.abrir_programa(abrir.group(1))
        if resultado.startswith("Abrindo"):
            return f"{resultado[:-1]}, {NOME_USUARIO}."
        return None
    fechar = re.fullmatch(r"(?:fecha|feche|fechar|encerra|mata) " + ARTIGOS + r"(.+)", texto)
    if fechar:
        resultado = aplicativos.fechar_programa(fechar.group(1))
        if resultado.startswith("Pedi para fechar"):
            return f"Fechando, {NOME_USUARIO}."
        return None
    return None
