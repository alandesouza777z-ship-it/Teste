"""Ferramentas de voz para as áreas do JARVIS: finanças, hábitos, academia, leitura, aprendizado e CRM."""

import dados

from .base import _schema

AREAS = {"inicio", "financas", "habitos", "academia", "leitura", "aprendizado", "crm"}

# A interface (app.py) troca estas funções para abrir a área na tela e atualizar o que mudou.
ao_abrir_area = lambda area: None  # noqa: E731
ao_dados_mudaram = lambda area: None  # noqa: E731


def _mudou(area: str, resultado) -> str:
    ao_dados_mudaram(area)
    return str(resultado)


def abrir_area(area: str) -> str:
    if area not in AREAS:
        return f"Área desconhecida. Opções: {', '.join(sorted(AREAS))}."
    ao_abrir_area(area)
    return f"Área {area} aberta na tela."


def registrar_lancamento(valor: float, descricao: str, tipo: str = "despesa", categoria: str = "") -> str:
    return _mudou("financas", dados.adicionar_lancamento(valor, descricao, tipo, categoria))


def resumo_financas(mes: str = "") -> str:
    r = dados.resumo_financas(mes)
    categorias = ", ".join(f"{c['categoria']} R$ {c['total']:.2f}" for c in r["categorias"][:5])
    return (f"Mês {r['mes']}: receitas R$ {r['receitas']:.2f}, despesas R$ {r['despesas']:.2f}, "
            f"saldo R$ {r['saldo']:.2f}. Maiores gastos: {categorias or 'nenhum'}.")


def marcar_habito(nome: str, feito: bool = True) -> str:
    return _mudou("habitos", dados.marcar_habito(nome, feito=feito))


def criar_habito(nome: str) -> str:
    return _mudou("habitos", dados.criar_habito(nome))


def status_habitos() -> str:
    s = dados.status_habitos()
    if not s["habitos"]:
        return "Nenhum hábito cadastrado."
    return "; ".join(f"{h['nome']}: {'feito' if h['hoje'] else 'pendente'} hoje, sequência de {h['sequencia']} dias"
                     for h in s["habitos"])


def registrar_treino(exercicio: str, series: int | None = None, repeticoes: int | None = None,
                     carga: float | None = None, observacao: str = "") -> str:
    return _mudou("academia", dados.registrar_treino(exercicio, series, repeticoes, carga, observacao))


def resumo_academia() -> str:
    r = dados.resumo_academia()
    recordes = ", ".join(f"{x['exercicio']} {x['carga']:g} kg" for x in r["recordes"][:8])
    return f"Treinou {r['dias_semana']} dias nos últimos 7. Recordes: {recordes or 'nenhum'}."


def adicionar_livro(titulo: str, autor: str = "", paginas: int | None = None) -> str:
    return _mudou("leitura", dados.adicionar_livro(titulo, autor, paginas))


def registrar_leitura(paginas: int = 0, titulo: str = "", ate_pagina: int | None = None) -> str:
    return _mudou("leitura", dados.registrar_leitura(paginas, titulo, ate_pagina))


def status_leitura() -> str:
    s = dados.status_leitura()
    livros = "; ".join(f"{l['titulo']}: página {l['pagina_atual']}" + (f" de {l['paginas']}" if l["paginas"] else "")
                       + f" ({l['status']})" for l in s["livros"][:6])
    return f"{s['paginas_semana']} páginas lidas nos últimos 7 dias. {livros or 'Nenhum livro cadastrado.'}"


def anotar_estudo(tema: str, anotacao: str = "", minutos: int | None = None) -> str:
    return _mudou("aprendizado", dados.anotar_estudo(tema, anotacao, minutos))


def ensinar(titulo: str, conteudo: str) -> str:
    return _mudou("aprendizado", dados.ensinar(titulo, conteudo))


def consultar_conhecimento() -> str:
    return dados.conhecimento_texto()


def salvar_cliente(nome: str, telefone: str = "", empresa: str = "", etapa: str = "", valor: float | None = None,
                   notas: str = "") -> str:
    return _mudou("crm", dados.salvar_cliente(nome, telefone, empresa, etapa, valor, notas))


def registrar_interacao(cliente: str, resumo: str) -> str:
    return _mudou("crm", dados.registrar_interacao(cliente, resumo))


def ficha_cliente(cliente: str) -> str:
    return dados.ficha_cliente(cliente)


def listar_clientes(etapa: str = "") -> str:
    clientes = dados.resumo_crm()["clientes"]
    if etapa:
        clientes = [c for c in clientes if c["etapa"] == etapa]
    return "; ".join(f"{c['nome']} ({c['etapa']})" for c in clientes[:30]) or "Nenhum cliente."


FERRAMENTAS = [
    (_schema("abrir_area", "Abre uma área do JARVIS na tela.",
             {"area": {"type": "string", "enum": sorted(AREAS)}}, ["area"]), abrir_area),
    (_schema("registrar_lancamento", "Anota uma despesa ou receita nas finanças (ex.: 'gastei 50 no almoço').",
             {"valor": {"type": "number"}, "descricao": {"type": "string"},
              "tipo": {"type": "string", "enum": ["despesa", "receita"]},
              "categoria": {"type": "string", "description": "Opcional: alimentacao, transporte, moradia, saude, "
                                                             "lazer, compras, educacao, trabalho, outros."}},
             ["valor", "descricao"]), registrar_lancamento),
    (_schema("resumo_financas", "Resumo financeiro do mês: receitas, despesas, saldo e maiores gastos.",
             {"mes": {"type": "string", "description": "AAAA-MM; vazio = mês atual."}}), resumo_financas),
    (_schema("marcar_habito", "Marca (ou desmarca) um hábito como feito hoje; cria o hábito se não existir.",
             {"nome": {"type": "string"}, "feito": {"type": "boolean"}}, ["nome"]), marcar_habito),
    (_schema("criar_habito", "Cadastra um novo hábito para acompanhar.", {"nome": {"type": "string"}}, ["nome"]),
     criar_habito),
    (_schema("status_habitos", "Quais hábitos foram feitos hoje e as sequências de dias."), status_habitos),
    (_schema("registrar_treino", "Anota um exercício da academia.",
             {"exercicio": {"type": "string"}, "series": {"type": "integer"}, "repeticoes": {"type": "integer"},
              "carga": {"type": "number", "description": "kg"}, "observacao": {"type": "string"}}, ["exercicio"]),
     registrar_treino),
    (_schema("resumo_academia", "Frequência da semana e recordes de carga."), resumo_academia),
    (_schema("adicionar_livro", "Cadastra um livro para acompanhar a leitura.",
             {"titulo": {"type": "string"}, "autor": {"type": "string"}, "paginas": {"type": "integer"}}, ["titulo"]),
     adicionar_livro),
    (_schema("registrar_leitura", "Anota páginas lidas (ou até que página leu) no livro atual ou no livro citado.",
             {"paginas": {"type": "integer"}, "titulo": {"type": "string"}, "ate_pagina": {"type": "integer"}}),
     registrar_leitura),
    (_schema("status_leitura", "Livros em andamento e páginas lidas na semana."), status_leitura),
    (_schema("anotar_estudo", "Anota um estudo do usuário (tema, o que aprendeu, minutos).",
             {"tema": {"type": "string"}, "anotacao": {"type": "string"}, "minutos": {"type": "integer"}}, ["tema"]),
     anotar_estudo),
    (_schema("ensinar", "Guarda algo que o usuário te ensinou para atender clientes (preços, regras, respostas, "
             "tom). Use quando ele disser 'aprenda que...', 'quando perguntarem X responda Y'.",
             {"titulo": {"type": "string"}, "conteudo": {"type": "string"}}, ["titulo", "conteudo"]), ensinar),
    (_schema("consultar_conhecimento", "Tudo o que o usuário te ensinou para atender clientes."),
     consultar_conhecimento),
    (_schema("salvar_cliente", "Cadastra ou atualiza um cliente no CRM.",
             {"nome": {"type": "string"}, "telefone": {"type": "string"}, "empresa": {"type": "string"},
              "etapa": {"type": "string", "enum": dados.ETAPAS_CRM}, "valor": {"type": "number"},
              "notas": {"type": "string"}}, ["nome"]), salvar_cliente),
    (_schema("registrar_interacao", "Anota no CRM um contato com o cliente.",
             {"cliente": {"type": "string"}, "resumo": {"type": "string"}}, ["cliente", "resumo"]),
     registrar_interacao),
    (_schema("ficha_cliente", "Ficha do cliente no CRM: etapa, valor, notas e últimos contatos.",
             {"cliente": {"type": "string", "description": "Nome ou telefone."}}, ["cliente"]), ficha_cliente),
    (_schema("listar_clientes", "Lista clientes do CRM (opcionalmente de uma etapa).",
             {"etapa": {"type": "string", "enum": dados.ETAPAS_CRM}}), listar_clientes),
]
