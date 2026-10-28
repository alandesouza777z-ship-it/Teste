"""Banco de dados local do JARVIS (SQLite): finanças, hábitos, academia, leitura, aprendizado e CRM.

Fica no arquivo jarvis.db, ao lado do .env. Tudo aqui é usado tanto pela interface
(app.py -> api_area) quanto pela voz (ferramentas/areas.py).
"""

import datetime
import os
import sqlite3
import threading

from config import PASTA_USUARIO

ARQUIVO = os.path.join(PASTA_USUARIO, "jarvis.db")
_trava = threading.Lock()

ESQUEMA = """
CREATE TABLE IF NOT EXISTS lancamentos (
    id INTEGER PRIMARY KEY, data TEXT NOT NULL, tipo TEXT NOT NULL CHECK (tipo IN ('despesa', 'receita')),
    valor REAL NOT NULL, categoria TEXT NOT NULL DEFAULT 'outros', descricao TEXT NOT NULL DEFAULT '');
CREATE TABLE IF NOT EXISTS habitos (
    id INTEGER PRIMARY KEY, nome TEXT NOT NULL UNIQUE COLLATE NOCASE, criado TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS habitos_feitos (
    habito_id INTEGER NOT NULL REFERENCES habitos(id) ON DELETE CASCADE, data TEXT NOT NULL,
    PRIMARY KEY (habito_id, data));
CREATE TABLE IF NOT EXISTS treinos (
    id INTEGER PRIMARY KEY, data TEXT NOT NULL, exercicio TEXT NOT NULL, series INTEGER, repeticoes INTEGER,
    carga REAL, observacao TEXT NOT NULL DEFAULT '');
CREATE TABLE IF NOT EXISTS livros (
    id INTEGER PRIMARY KEY, titulo TEXT NOT NULL, autor TEXT NOT NULL DEFAULT '', paginas INTEGER,
    pagina_atual INTEGER NOT NULL DEFAULT 0, status TEXT NOT NULL DEFAULT 'lendo', criado TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS leituras (
    id INTEGER PRIMARY KEY, livro_id INTEGER NOT NULL REFERENCES livros(id) ON DELETE CASCADE,
    data TEXT NOT NULL, paginas INTEGER NOT NULL);
CREATE TABLE IF NOT EXISTS estudos (
    id INTEGER PRIMARY KEY, data TEXT NOT NULL, tema TEXT NOT NULL, minutos INTEGER, anotacao TEXT NOT NULL DEFAULT '');
CREATE TABLE IF NOT EXISTS conhecimento (
    id INTEGER PRIMARY KEY, titulo TEXT NOT NULL, conteudo TEXT NOT NULL, criado TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS clientes (
    id INTEGER PRIMARY KEY, nome TEXT NOT NULL, telefone TEXT NOT NULL DEFAULT '', empresa TEXT NOT NULL DEFAULT '',
    etapa TEXT NOT NULL DEFAULT 'lead', valor REAL, notas TEXT NOT NULL DEFAULT '', ultimo_contato TEXT, criado TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS interacoes (
    id INTEGER PRIMARY KEY, cliente_id INTEGER NOT NULL REFERENCES clientes(id) ON DELETE CASCADE,
    data TEXT NOT NULL, canal TEXT NOT NULL DEFAULT 'whatsapp', resumo TEXT NOT NULL);
"""

ETAPAS_CRM = ["lead", "negociacao", "cliente", "perdido"]
CATEGORIAS = {
    "alimentacao": ("almoco", "jantar", "lanche", "comida", "restaurante", "mercado", "ifood", "padaria", "cafe"),
    "transporte": ("uber", "gasolina", "combustivel", "onibus", "metro", "estacionamento", "pedagio", "99"),
    "moradia": ("aluguel", "condominio", "luz", "energia", "agua", "internet", "gas"),
    "saude": ("farmacia", "remedio", "medico", "consulta", "academia", "dentista", "exame"),
    "lazer": ("cinema", "show", "bar", "viagem", "jogo", "netflix", "spotify", "streaming"),
    "compras": ("roupa", "sapato", "presente", "amazon", "shopee", "mercado livre", "eletronico"),
    "educacao": ("curso", "livro", "faculdade", "escola", "aula"),
    "trabalho": ("cliente", "fornecedor", "sistema", "servidor", "ferramenta", "anuncio", "marketing"),
}


def hoje() -> str:
    return datetime.date.today().isoformat()


def _conectar() -> sqlite3.Connection:
    con = sqlite3.connect(ARQUIVO, timeout=10)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys = ON")
    return con


def _executar(sql: str, parametros=()) -> list[dict]:
    with _trava, _conectar() as con:
        cursor = con.execute(sql, parametros)
        linhas = [dict(linha) for linha in cursor.fetchall()]
        if sql.lstrip().upper().startswith("INSERT"):
            return [{"id": cursor.lastrowid}]
        return linhas


def iniciar() -> None:
    with _trava, _conectar() as con:
        con.executescript(ESQUEMA)


def _sem_acento(texto: str) -> str:
    import unicodedata

    return "".join(c for c in unicodedata.normalize("NFD", texto.lower()) if unicodedata.category(c) != "Mn")


def adivinhar_categoria(descricao: str) -> str:
    texto = _sem_acento(descricao)
    for categoria, palavras in CATEGORIAS.items():
        if any(p in texto for p in palavras):
            return categoria
    return "outros"


# ---------- Finanças ----------

def adicionar_lancamento(valor: float, descricao: str = "", tipo: str = "despesa", categoria: str = "",
                         data: str = "") -> dict:
    categoria = (categoria or (adivinhar_categoria(descricao) if tipo == "despesa" else "receitas")).lower()
    novo = _executar("INSERT INTO lancamentos (data, tipo, valor, categoria, descricao) VALUES (?, ?, ?, ?, ?)",
                     (data or hoje(), tipo, abs(float(valor)), categoria, descricao))[0]
    return {"id": novo["id"], "valor": abs(float(valor)), "categoria": categoria, "tipo": tipo}


def resumo_financas(mes: str = "") -> dict:
    mes = mes or hoje()[:7]
    totais = {l["tipo"]: l["total"] for l in _executar(
        "SELECT tipo, SUM(valor) AS total FROM lancamentos WHERE substr(data, 1, 7) = ? GROUP BY tipo", (mes,))}
    categorias = _executar(
        "SELECT categoria, SUM(valor) AS total FROM lancamentos WHERE tipo = 'despesa' AND substr(data, 1, 7) = ? "
        "GROUP BY categoria ORDER BY total DESC", (mes,))
    despesas, receitas = totais.get("despesa", 0) or 0, totais.get("receita", 0) or 0
    return {"mes": mes, "despesas": despesas, "receitas": receitas, "saldo": receitas - despesas,
            "categorias": categorias,
            "lancamentos": _executar("SELECT * FROM lancamentos ORDER BY data DESC, id DESC LIMIT 60")}


# ---------- Hábitos ----------

def criar_habito(nome: str) -> dict:
    existente = _executar("SELECT id FROM habitos WHERE nome = ?", (nome.strip(),))
    if existente:
        return {"id": existente[0]["id"], "nome": nome, "ja_existia": True}
    return {"id": _executar("INSERT INTO habitos (nome, criado) VALUES (?, ?)", (nome.strip(), hoje()))[0]["id"],
            "nome": nome}


def _achar_habito(nome: str) -> dict | None:
    from difflib import get_close_matches

    habitos = _executar("SELECT * FROM habitos")
    por_nome = {_sem_acento(h["nome"]): h for h in habitos}
    procurado = _sem_acento(nome.strip())
    if procurado in por_nome:
        return por_nome[procurado]
    contem = [h for n, h in por_nome.items() if procurado in n or n in procurado]
    if contem:
        return contem[0]
    parecido = get_close_matches(procurado, por_nome, n=1, cutoff=0.55)
    return por_nome[parecido[0]] if parecido else None


def marcar_habito(nome: str, data: str = "", feito: bool = True, criar_se_nao_existir: bool = True) -> dict:
    habito = _achar_habito(nome)
    if habito is None:
        if not criar_se_nao_existir:
            return {"erro": f"Hábito '{nome}' não existe."}
        habito = {"id": criar_habito(nome)["id"], "nome": nome}
    if feito:
        _executar("INSERT OR IGNORE INTO habitos_feitos (habito_id, data) VALUES (?, ?)", (habito["id"], data or hoje()))
    else:
        _executar("DELETE FROM habitos_feitos WHERE habito_id = ? AND data = ?", (habito["id"], data or hoje()))
    return {"nome": habito["nome"], "feito": feito, "sequencia": _sequencia(habito["id"])}


def _sequencia(habito_id: int) -> int:
    datas = {l["data"] for l in _executar("SELECT data FROM habitos_feitos WHERE habito_id = ?", (habito_id,))}
    dia, dias = datetime.date.today(), 0
    if dia.isoformat() not in datas:
        dia -= datetime.timedelta(days=1)  # ainda dá tempo de fazer hoje
    while dia.isoformat() in datas:
        dias += 1
        dia -= datetime.timedelta(days=1)
    return dias


def status_habitos() -> dict:
    semana = [(datetime.date.today() - datetime.timedelta(days=i)).isoformat() for i in range(6, -1, -1)]
    habitos = []
    for h in _executar("SELECT * FROM habitos ORDER BY nome"):
        feitos = {l["data"] for l in _executar(
            "SELECT data FROM habitos_feitos WHERE habito_id = ? AND data >= ?", (h["id"], semana[0]))}
        habitos.append({**h, "semana": [d in feitos for d in semana], "hoje": hoje() in feitos,
                        "sequencia": _sequencia(h["id"])})
    return {"dias": semana, "habitos": habitos}


# ---------- Academia ----------

def registrar_treino(exercicio: str, series: int | None = None, repeticoes: int | None = None,
                     carga: float | None = None, observacao: str = "", data: str = "") -> dict:
    novo = _executar("INSERT INTO treinos (data, exercicio, series, repeticoes, carga, observacao) VALUES (?, ?, ?, ?, ?, ?)",
                     (data or hoje(), exercicio, series, repeticoes, carga, observacao))[0]
    return {"id": novo["id"], "exercicio": exercicio}


def resumo_academia() -> dict:
    inicio_semana = (datetime.date.today() - datetime.timedelta(days=6)).isoformat()
    dias = _executar("SELECT COUNT(DISTINCT data) AS n FROM treinos WHERE data >= ?", (inicio_semana,))[0]["n"]
    recordes = _executar("SELECT exercicio, MAX(carga) AS carga FROM treinos WHERE carga IS NOT NULL "
                         "GROUP BY exercicio ORDER BY exercicio")
    return {"dias_semana": dias, "recordes": recordes,
            "treinos": _executar("SELECT * FROM treinos ORDER BY data DESC, id DESC LIMIT 80")}


# ---------- Leitura ----------

def adicionar_livro(titulo: str, autor: str = "", paginas: int | None = None) -> dict:
    return {"id": _executar("INSERT INTO livros (titulo, autor, paginas, criado) VALUES (?, ?, ?, ?)",
                            (titulo, autor, paginas, hoje()))[0]["id"], "titulo": titulo}


def _achar_livro(titulo: str) -> dict | None:
    livros = _executar("SELECT * FROM livros ORDER BY status = 'lendo' DESC, id DESC")
    if not titulo:
        return livros[0] if livros else None
    procurado = _sem_acento(titulo)
    return next((l for l in livros if procurado in _sem_acento(l["titulo"])), None)


def registrar_leitura(paginas: int, titulo: str = "", ate_pagina: int | None = None) -> dict:
    livro = _achar_livro(titulo)
    if livro is None:
        if not titulo:
            return {"erro": "Nenhum livro cadastrado. Diga o título do livro."}
        livro = _executar("SELECT * FROM livros WHERE id = ?", (adicionar_livro(titulo)["id"],))[0]
    atual = ate_pagina if ate_pagina is not None else livro["pagina_atual"] + int(paginas)
    lidas = atual - livro["pagina_atual"] if ate_pagina is not None else int(paginas)
    status = "lido" if livro["paginas"] and atual >= livro["paginas"] else "lendo"
    _executar("UPDATE livros SET pagina_atual = ?, status = ? WHERE id = ?", (atual, status, livro["id"]))
    _executar("INSERT INTO leituras (livro_id, data, paginas) VALUES (?, ?, ?)", (livro["id"], hoje(), max(0, lidas)))
    return {"titulo": livro["titulo"], "pagina_atual": atual, "paginas": livro["paginas"], "status": status}


def status_leitura() -> dict:
    inicio_semana = (datetime.date.today() - datetime.timedelta(days=6)).isoformat()
    semana = _executar("SELECT COALESCE(SUM(paginas), 0) AS n FROM leituras WHERE data >= ?", (inicio_semana,))[0]["n"]
    return {"paginas_semana": semana, "livros": _executar("SELECT * FROM livros ORDER BY status = 'lendo' DESC, id DESC")}


# ---------- Aprendizado ----------

def anotar_estudo(tema: str, anotacao: str = "", minutos: int | None = None) -> dict:
    return {"id": _executar("INSERT INTO estudos (data, tema, minutos, anotacao) VALUES (?, ?, ?, ?)",
                            (hoje(), tema, minutos, anotacao))[0]["id"], "tema": tema}


def ensinar(titulo: str, conteudo: str) -> dict:
    """Guarda algo que o JARVIS deve saber para atender clientes (preços, regras, tom de voz...)."""
    existente = _executar("SELECT id FROM conhecimento WHERE titulo = ? COLLATE NOCASE", (titulo,))
    if existente:
        _executar("UPDATE conhecimento SET conteudo = ? WHERE id = ?", (conteudo, existente[0]["id"]))
        return {"id": existente[0]["id"], "titulo": titulo, "atualizado": True}
    return {"id": _executar("INSERT INTO conhecimento (titulo, conteudo, criado) VALUES (?, ?, ?)",
                            (titulo, conteudo, hoje()))[0]["id"], "titulo": titulo}


def conhecimento_texto() -> str:
    itens = _executar("SELECT titulo, conteudo FROM conhecimento ORDER BY id")
    return "\n".join(f"- {i['titulo']}: {i['conteudo']}" for i in itens) or "(nada ensinado ainda)"


def resumo_aprendizado() -> dict:
    return {"estudos": _executar("SELECT * FROM estudos ORDER BY data DESC, id DESC LIMIT 60"),
            "conhecimento": _executar("SELECT * FROM conhecimento ORDER BY id DESC")}


# ---------- CRM ----------

def _numero(telefone: str) -> str:
    return "".join(c for c in telefone if c.isdigit())


def achar_cliente(nome_ou_telefone: str) -> dict | None:
    if not nome_ou_telefone:
        return None
    digitos = _numero(nome_ou_telefone)
    clientes = _executar("SELECT * FROM clientes")
    if len(digitos) >= 8:
        achado = next((c for c in clientes if c["telefone"] and _numero(c["telefone"]).endswith(digitos[-8:])), None)
        if achado:
            return achado
    procurado = _sem_acento(nome_ou_telefone.strip())
    return (next((c for c in clientes if _sem_acento(c["nome"]) == procurado), None)
            or next((c for c in clientes if procurado in _sem_acento(c["nome"])), None))


def salvar_cliente(nome: str, telefone: str = "", empresa: str = "", etapa: str = "", valor: float | None = None,
                   notas: str = "") -> dict:
    etapa = _sem_acento(etapa) if etapa else ""
    if etapa and etapa not in ETAPAS_CRM:
        etapa = {"negociando": "negociacao", "fechado": "cliente", "ganho": "cliente"}.get(etapa, "lead")
    cliente = achar_cliente(telefone) or achar_cliente(nome)
    if cliente:
        mudancas = {"telefone": telefone, "empresa": empresa, "etapa": etapa, "valor": valor}
        mudancas = {k: v for k, v in mudancas.items() if v not in ("", None)}
        if notas:
            mudancas["notas"] = (cliente["notas"] + "\n" + notas).strip()
        for campo, valor_novo in mudancas.items():
            _executar(f"UPDATE clientes SET {campo} = ? WHERE id = ?", (valor_novo, cliente["id"]))
        return {"id": cliente["id"], "nome": cliente["nome"], "atualizado": list(mudancas)}
    novo = _executar("INSERT INTO clientes (nome, telefone, empresa, etapa, valor, notas, criado) VALUES (?, ?, ?, ?, ?, ?, ?)",
                     (nome, telefone, empresa, etapa or "lead", valor, notas, hoje()))[0]
    return {"id": novo["id"], "nome": nome, "criado": True}


def registrar_interacao(cliente: str, resumo: str, canal: str = "whatsapp") -> dict:
    achado = achar_cliente(cliente)
    if achado is None:
        achado = {"id": salvar_cliente(cliente)["id"], "nome": cliente}
    agora = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    _executar("INSERT INTO interacoes (cliente_id, data, canal, resumo) VALUES (?, ?, ?, ?)",
              (achado["id"], agora, canal, resumo))
    _executar("UPDATE clientes SET ultimo_contato = ? WHERE id = ?", (agora, achado["id"]))
    return {"cliente": achado["nome"]}


def resumo_crm() -> dict:
    clientes = _executar("SELECT * FROM clientes ORDER BY COALESCE(ultimo_contato, criado) DESC")
    for cliente in clientes:
        cliente["interacoes"] = _executar(
            "SELECT data, canal, resumo FROM interacoes WHERE cliente_id = ? ORDER BY id DESC LIMIT 8", (cliente["id"],))
    return {"etapas": ETAPAS_CRM, "clientes": clientes}


def ficha_cliente(nome_ou_telefone: str) -> str:
    cliente = achar_cliente(nome_ou_telefone)
    if not cliente:
        return "Cliente não cadastrado no CRM."
    historico = _executar("SELECT data, resumo FROM interacoes WHERE cliente_id = ? ORDER BY id DESC LIMIT 5",
                          (cliente["id"],))
    linhas = [f"{cliente['nome']} ({cliente['empresa'] or 'sem empresa'}) — etapa: {cliente['etapa']}"
              + (f", valor: R$ {cliente['valor']:.2f}" if cliente["valor"] else "")]
    if cliente["notas"]:
        linhas.append(f"Notas: {cliente['notas']}")
    linhas += [f"{h['data']}: {h['resumo']}" for h in historico]
    return "\n".join(linhas)


# ---------- Vocabulário para o reconhecimento de voz ----------

def vocabulario() -> str:
    """Nomes de hábitos, livros e clientes, para o reconhecimento de voz acertar."""
    nomes = [l["nome"] for l in _executar("SELECT nome FROM habitos")]
    nomes += [l["titulo"] for l in _executar("SELECT titulo FROM livros WHERE status = 'lendo'")]
    nomes += [l["nome"] for l in _executar("SELECT nome FROM clientes ORDER BY id DESC LIMIT 30")]
    return ", ".join(nomes[:60])


# ---------- Ponte com a interface ----------

def api_area(area: str, acao: str = "ler", params: dict | None = None):
    """Uma única porta de entrada para a interface: ler a área, salvar, marcar, excluir."""
    p = params or {}
    tabelas = {"financas": "lancamentos", "academia": "treinos", "leitura": "livros", "estudos": "estudos",
               "conhecimento": "conhecimento", "crm": "clientes", "habitos": "habitos"}
    if acao == "excluir":
        if area not in tabelas:
            raise ValueError(f"Área desconhecida: {area}")
        _executar(f"DELETE FROM {tabelas[area]} WHERE id = ?", (int(p["id"]),))
    elif acao == "salvar":
        {
            "financas": lambda: adicionar_lancamento(p["valor"], p.get("descricao", ""), p.get("tipo", "despesa"),
                                                     p.get("categoria", "")),
            "habitos": lambda: criar_habito(p["nome"]),
            "academia": lambda: registrar_treino(p["exercicio"], _int(p.get("series")), _int(p.get("repeticoes")),
                                                 _float(p.get("carga")), p.get("observacao", "")),
            "leitura": lambda: adicionar_livro(p["titulo"], p.get("autor", ""), _int(p.get("paginas"))),
            "estudos": lambda: anotar_estudo(p["tema"], p.get("anotacao", ""), _int(p.get("minutos"))),
            "conhecimento": lambda: ensinar(p["titulo"], p["conteudo"]),
            "crm": lambda: salvar_cliente(p["nome"], p.get("telefone", ""), p.get("empresa", ""), p.get("etapa", ""),
                                          _float(p.get("valor")), p.get("notas", "")),
        }[area]()
    elif acao == "marcar":
        habito = _executar("SELECT nome FROM habitos WHERE id = ?", (int(p["id"]),))[0]
        marcar_habito(habito["nome"], p.get("data", ""), bool(p.get("feito", True)))
    elif acao == "ler_paginas":
        livro = _executar("SELECT titulo FROM livros WHERE id = ?", (int(p["id"]),))[0]
        registrar_leitura(int(p["paginas"]), livro["titulo"])
    elif acao == "mover":
        _executar("UPDATE clientes SET etapa = ? WHERE id = ?", (p["etapa"], int(p["id"])))
    elif acao == "interacao":
        cliente = _executar("SELECT nome FROM clientes WHERE id = ?", (int(p["id"]),))[0]
        registrar_interacao(cliente["nome"], p["resumo"], p.get("canal", "anotação"))
    return ler_area(area)


def ler_area(area: str) -> dict:
    return {
        "financas": resumo_financas, "habitos": status_habitos, "academia": resumo_academia,
        "leitura": status_leitura, "aprendizado": resumo_aprendizado, "estudos": resumo_aprendizado,
        "conhecimento": resumo_aprendizado, "crm": resumo_crm,
    }[area]()


def _int(valor):
    try:
        return int(valor) if valor not in (None, "") else None
    except (TypeError, ValueError):
        return None


def _float(valor):
    try:
        return float(str(valor).replace(",", ".")) if valor not in (None, "") else None
    except (TypeError, ValueError):
        return None


iniciar()
