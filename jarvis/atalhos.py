"""Comandos instantâneos: pedidos simples executados direto, sem esperar o Claude.

"Abre o Spotify", "pausa a música", "próxima", "aumenta o volume", "que horas são"...
Se o pedido não for um desses (ou não der certo), devolve None e o Claude cuida.
"""

import datetime
import re
import unicodedata

import dados
from cerebro import NOME_USUARIO
from ferramentas import aplicativos, areas, computador

ARTIGOS = r"(?:o |a |os |as |um |uma |meu |minha )?"
NOMES_AREAS = {"financas": "finanças", "habitos": "hábitos", "academia": "academia", "leitura": "leitura",
               "aprendizado": "aprendizado", "crm": "o CRM", "inicio": "início"}
NOMES_CATEGORIAS = {"alimentacao": "alimentação", "saude": "saúde", "educacao": "educação"}
AREAS_FALADAS = {
    "financas": "financas", "financa": "financas", "gastos": "financas", "despesas": "financas", "dinheiro": "financas",
    "habitos": "habitos", "habito": "habitos", "academia": "academia", "treino": "academia", "treinos": "academia",
    "leitura": "leitura", "livros": "leitura", "leituras": "leitura", "aprendizado": "aprendizado",
    "estudos": "aprendizado", "crm": "crm", "clientes": "crm", "cliente": "crm", "inicio": "inicio", "home": "inicio",
}


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
    if not texto or len(texto.split()) > 9:
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

    # Áreas do JARVIS ("abra hábitos", "mostra minhas finanças", "volta pro início")
    area = re.fullmatch(r"(?:abre|abra|abrir|mostra|mostre|mostrar|vai para|vai pra|ir para|entra em|entrar em) "
                        r"(?:a area de |a area |area de |o |a |as |os |meu |minha |meus |minhas )?(\w+(?: \w+)?)", texto)
    if area and AREAS_FALADAS.get(area.group(1)):
        destino = AREAS_FALADAS[area.group(1)]
        areas.abrir_area(destino)
        return f"{'Voltando ao início' if destino == 'inicio' else 'Abrindo ' + NOMES_AREAS[destino]}, {NOME_USUARIO}."
    if re.fullmatch(r"(volta|voltar|fecha|fechar) ((pro|para o|ao) inicio|a area|essa area)", texto):
        areas.abrir_area("inicio")
        return f"Certo, {NOME_USUARIO}."

    # Despesa simples: "gastei 50 reais no almoço", "gastei 25,90 com uber"
    com_acentos = re.sub(r"\s+", " ", re.sub(r"[^\w ]", " ", pedido.lower())).replace("jarvis", "").strip()
    gasto = re.fullmatch(r"(?:gastei|paguei|comprei) (\d+(?: \d{1,2})?) (?:reais )?(?:com|no|na|em|de|do|da|pelo|pela) (.+)",
                         com_acentos)
    if gasto:
        valor = float(gasto.group(1).replace(" ", "."))
        lancamento = dados.adicionar_lancamento(valor, gasto.group(2))
        areas.ao_dados_mudaram("financas")
        categoria = NOMES_CATEGORIAS.get(lancamento["categoria"], lancamento["categoria"])
        return f"Anotado: {valor:.2f} reais em {categoria}, {NOME_USUARIO}.".replace(".", ",", 1)

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
