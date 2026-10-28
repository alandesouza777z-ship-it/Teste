// Áreas do JARVIS: finanças, hábitos, academia, leitura, aprendizado e CRM.
// Os dados vêm do Python (window.pywebview.api.area); tudo é montado com textContent (seguro contra HTML).

const api = () => window.pywebview?.api;
const painel = document.getElementById("area");
const conteudo = document.getElementById("area-conteudo");
let areaAtual = "inicio";

const TITULOS = {
  financas: "Finanças", habitos: "Hábitos", academia: "Academia", leitura: "Leitura",
  aprendizado: "Aprendizado", crm: "CRM",
};
const DIAS = ["dom", "seg", "ter", "qua", "qui", "sex", "sáb"];
const ETAPAS = { lead: "Lead", negociacao: "Negociação", cliente: "Cliente", perdido: "Perdido" };

// ---------- Utilitários de DOM ----------
function h(tag, props = {}, ...filhos) {
  const el = document.createElement(tag);
  for (const [chave, valor] of Object.entries(props)) {
    if (chave === "class") el.className = valor;
    else if (chave.startsWith("on")) el.addEventListener(chave.slice(2), valor);
    else if (valor !== undefined && valor !== null && valor !== false) el.setAttribute(chave, valor);
  }
  for (const filho of filhos.flat()) {
    if (filho === null || filho === undefined || filho === false) continue;
    el.append(filho instanceof Node ? filho : document.createTextNode(String(filho)));
  }
  return el;
}
const reais = (v) => (v ?? 0).toLocaleString("pt-BR", { style: "currency", currency: "BRL" });
const dataCurta = (iso) => (iso ? iso.slice(8, 10) + "/" + iso.slice(5, 7) : "");
const numero = (v) => Number(v).toLocaleString("pt-BR");
const CATEGORIAS = { alimentacao: "alimentação", saude: "saúde", educacao: "educação" };
const categoria = (c) => CATEGORIAS[c] || c;

function formulario(campos, aoEnviar, rotulo = "Adicionar") {
  const form = h("form", { class: "form-area" });
  for (const campo of campos) {
    if (campo.opcoes) {
      form.append(h("select", { name: campo.nome, title: campo.rotulo },
        campo.opcoes.map(([valor, texto]) => h("option", { value: valor }, texto))));
    } else if (campo.longo) {
      form.append(h("textarea", { name: campo.nome, placeholder: campo.rotulo, rows: 2, required: campo.obrigatorio }));
    } else {
      form.append(h("input", { name: campo.nome, placeholder: campo.rotulo, type: campo.tipo || "text",
        step: campo.tipo === "number" ? "any" : null, required: campo.obrigatorio, style: campo.largura ? `flex:${campo.largura}` : null }));
    }
  }
  form.append(h("button", { type: "submit", class: "botao-area" }, rotulo));
  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    const valores = Object.fromEntries(new FormData(form).entries());
    await aoEnviar(valores);
    form.reset();
  });
  return form;
}

const cartaoKpi = (rotulo, valor, detalhe) =>
  h("div", { class: "kpi" }, h("small", {}, rotulo), h("b", {}, valor), detalhe ? h("span", {}, detalhe) : null);
const secao = (titulo, ...filhos) => h("section", { class: "secao" }, h("h3", {}, titulo), ...filhos);
const botaoExcluir = (aoClicar) => h("button", { class: "excluir", title: "Excluir", onclick: aoClicar }, "×");
const vazio = (texto) => h("p", { class: "vazio-area" }, texto);

async function chamar(area, acao = "ler", params = {}) {
  try {
    return await api()?.area(area, acao, params);
  } catch (erro) {
    console.error(erro);
    return null;
  }
}

// ---------- Renderização de cada área ----------
const RENDER = {
  async financas() {
    const d = await chamar("financas");
    if (!d) return [];
    const salvar = (v) => chamar("financas", "salvar", v).then(() => abrirArea("financas"));
    const maior = Math.max(1, ...d.categorias.map((c) => c.total));
    return [
      h("div", { class: "kpis" },
        cartaoKpi("Receitas do mês", reais(d.receitas)), cartaoKpi("Despesas do mês", reais(d.despesas)),
        cartaoKpi("Saldo", reais(d.saldo), d.saldo >= 0 ? "positivo" : "negativo")),
      h("div", { class: "colunas" },
        h("div", {},
          secao("Novo lançamento", formulario([
            { nome: "tipo", rotulo: "Tipo", opcoes: [["despesa", "Despesa"], ["receita", "Receita"]] },
            { nome: "valor", rotulo: "Valor (R$)", tipo: "number", obrigatorio: true },
            { nome: "descricao", rotulo: "Descrição", largura: 2 },
          ], salvar)),
          secao("Gastos por categoria", d.categorias.length ? d.categorias.map((c) =>
            h("div", { class: "barra-cat" }, h("span", {}, categoria(c.categoria)), h("i", { style: `width:${(c.total / maior) * 100}%` }), h("b", {}, reais(c.total))))
            : vazio("Nenhuma despesa neste mês."))),
        secao("Lançamentos", d.lancamentos.length ? h("ul", { class: "lista" }, d.lancamentos.map((l) =>
          h("li", {}, h("span", { class: "data" }, dataCurta(l.data)),
            h("span", { class: "desc" }, l.descricao || categoria(l.categoria), h("small", {}, categoria(l.categoria))),
            h("b", { class: l.tipo }, (l.tipo === "despesa" ? "− " : "+ ") + reais(l.valor)),
            botaoExcluir(() => chamar("financas", "excluir", { id: l.id }).then(() => abrirArea("financas"))))))
          : vazio("Diga “gastei 50 reais no almoço” para anotar."))),
    ];
  },

  async habitos() {
    const d = await chamar("habitos");
    if (!d) return [];
    const marcar = (id, data, feito) => chamar("habitos", "marcar", { id, data, feito }).then(() => abrirArea("habitos"));
    return [
      secao("Novo hábito", formulario([{ nome: "nome", rotulo: "Ex.: beber 2 litros de água", obrigatorio: true, largura: 3 }],
        (v) => chamar("habitos", "salvar", v).then(() => abrirArea("habitos")))),
      secao("Últimos 7 dias", d.habitos.length ? h("div", { class: "habitos" },
        h("div", { class: "habito cabecalho" }, h("span", {}), d.dias.map((dia) => h("small", {}, DIAS[new Date(dia + "T12:00").getDay()]))),
        d.habitos.map((hab) => h("div", { class: "habito" },
          h("span", { class: "nome" }, hab.nome, h("small", {}, hab.sequencia === 1 ? "1 dia seguido" : `${hab.sequencia} dias seguidos`)),
          d.dias.map((dia, i) => h("button", { class: "dia" + (hab.semana[i] ? " feito" : ""), title: dataCurta(dia),
            onclick: () => marcar(hab.id, dia, !hab.semana[i]) })),
          botaoExcluir(() => chamar("habitos", "excluir", { id: hab.id }).then(() => abrirArea("habitos"))))))
        : vazio("Nenhum hábito ainda. Diga “marquei o hábito de meditar”.")),
    ];
  },

  async academia() {
    const d = await chamar("academia");
    if (!d) return [];
    const porDia = {};
    d.treinos.forEach((t) => (porDia[t.data] ||= []).push(t));
    return [
      h("div", { class: "kpis" }, cartaoKpi("Treinos nos últimos 7 dias", String(d.dias_semana)),
        cartaoKpi("Exercícios com recorde", String(d.recordes.length))),
      h("div", { class: "colunas" },
        h("div", {},
          secao("Registrar exercício", formulario([
            { nome: "exercicio", rotulo: "Exercício", obrigatorio: true, largura: 2 },
            { nome: "series", rotulo: "Séries", tipo: "number" }, { nome: "repeticoes", rotulo: "Reps", tipo: "number" },
            { nome: "carga", rotulo: "Kg", tipo: "number" },
          ], (v) => chamar("academia", "salvar", v).then(() => abrirArea("academia")))),
          secao("Recordes", d.recordes.length ? h("ul", { class: "lista" }, d.recordes.map((r) =>
            h("li", {}, h("span", { class: "desc" }, r.exercicio), h("b", {}, `${numero(r.carga)} kg`)))) : vazio("Sem cargas registradas."))),
        secao("Histórico", Object.keys(porDia).length ? Object.entries(porDia).map(([dia, lista]) =>
          h("div", { class: "grupo" }, h("small", { class: "grupo-titulo" }, dataCurta(dia)), h("ul", { class: "lista" }, lista.map((t) =>
            h("li", {}, h("span", { class: "desc" }, t.exercicio),
              h("span", {}, [t.series && `${t.series}x${t.repeticoes ?? ""}`, t.carga && `${numero(t.carga)} kg`].filter(Boolean).join(" · ")),
              botaoExcluir(() => chamar("academia", "excluir", { id: t.id }).then(() => abrirArea("academia"))))))))
          : vazio("Diga “fiz supino, 3 séries de 10 com 40 quilos”."))),
    ];
  },

  async leitura() {
    const d = await chamar("leitura");
    if (!d) return [];
    return [
      h("div", { class: "kpis" }, cartaoKpi("Páginas nos últimos 7 dias", String(d.paginas_semana)),
        cartaoKpi("Livros em andamento", String(d.livros.filter((l) => l.status === "lendo").length))),
      secao("Novo livro", formulario([
        { nome: "titulo", rotulo: "Título", obrigatorio: true, largura: 3 }, { nome: "autor", rotulo: "Autor", largura: 2 },
        { nome: "paginas", rotulo: "Páginas", tipo: "number" },
      ], (v) => chamar("leitura", "salvar", v).then(() => abrirArea("leitura")))),
      secao("Estante", d.livros.length ? h("div", { class: "livros" }, d.livros.map((l) => {
        const pct = l.paginas ? Math.min(100, (l.pagina_atual / l.paginas) * 100) : 0;
        const campo = h("input", { type: "number", placeholder: "+ págs", class: "mini" });
        return h("div", { class: "livro" + (l.status === "lido" ? " lido" : "") },
          h("b", {}, l.titulo), h("small", {}, l.autor || " "),
          h("div", { class: "progresso" }, h("i", { style: `width:${pct}%` })),
          h("small", {}, l.paginas ? `página ${l.pagina_atual} de ${l.paginas} · ${Math.round(pct)}%` : `página ${l.pagina_atual}`),
          h("div", { class: "acoes" }, campo,
            h("button", { class: "botao-area", onclick: () => campo.value && chamar("leitura", "ler_paginas", { id: l.id, paginas: campo.value }).then(() => abrirArea("leitura")) }, "Ler"),
            botaoExcluir(() => chamar("leitura", "excluir", { id: l.id }).then(() => abrirArea("leitura")))));
      })) : vazio("Diga “comecei a ler Hábitos Atômicos, 320 páginas”.")),
    ];
  },

  async aprendizado() {
    const d = await chamar("aprendizado");
    if (!d) return [];
    return [
      h("div", { class: "colunas" },
        secao("O que o JARVIS sabe para atender clientes",
          h("p", { class: "dica" }, "Ensine preços, regras, horários e o jeito de falar. Ele usa isso para responder no WhatsApp. Pela voz: “aprenda que o plano básico custa 99 reais”."),
          formulario([{ nome: "titulo", rotulo: "Assunto (ex.: Preço do plano básico)", obrigatorio: true },
            { nome: "conteudo", rotulo: "O que ele deve saber/responder", longo: true, obrigatorio: true }],
          (v) => chamar("conhecimento", "salvar", v).then(() => abrirArea("aprendizado")), "Ensinar"),
          d.conhecimento.length ? h("ul", { class: "lista notas" }, d.conhecimento.map((c) =>
            h("li", {}, h("span", { class: "desc" }, c.titulo, h("small", {}, c.conteudo)),
              botaoExcluir(() => chamar("conhecimento", "excluir", { id: c.id }).then(() => abrirArea("aprendizado"))))))
            : vazio("Nada ensinado ainda.")),
        secao("Meus estudos",
          formulario([{ nome: "tema", rotulo: "Tema", obrigatorio: true, largura: 2 }, { nome: "minutos", rotulo: "Min", tipo: "number" },
            { nome: "anotacao", rotulo: "O que aprendi", longo: true }],
          (v) => chamar("estudos", "salvar", v).then(() => abrirArea("aprendizado")), "Anotar"),
          d.estudos.length ? h("ul", { class: "lista notas" }, d.estudos.map((e) =>
            h("li", {}, h("span", { class: "data" }, dataCurta(e.data)),
              h("span", { class: "desc" }, e.tema + (e.minutos ? ` · ${e.minutos} min` : ""), h("small", {}, e.anotacao)),
              botaoExcluir(() => chamar("estudos", "excluir", { id: e.id }).then(() => abrirArea("aprendizado"))))))
            : vazio("Diga “estudei 30 minutos de inglês hoje”."))),
    ];
  },

  async crm() {
    const d = await chamar("crm");
    if (!d) return [];
    const recarregar = () => abrirArea("crm");
    const cartao = (c) => {
      const indice = d.etapas.indexOf(c.etapa);
      const detalhes = h("div", { class: "detalhes" },
        c.telefone ? h("small", {}, c.telefone) : null,
        c.notas ? h("p", {}, c.notas) : null,
        c.interacoes.length ? h("ul", {}, c.interacoes.map((i) => h("li", {}, h("small", {}, i.data.slice(5, 16)), i.resumo))) : null,
        (() => {
          const nota = h("input", { placeholder: "Anotar contato…", class: "mini largo" });
          return h("div", { class: "acoes" }, nota,
            h("button", { class: "botao-area", onclick: (e) => { e.stopPropagation(); nota.value && chamar("crm", "interacao", { id: c.id, resumo: nota.value }).then(recarregar); } }, "Anotar"),
            indice > 0 ? h("button", { class: "botao-area", title: "Etapa anterior", onclick: (e) => { e.stopPropagation(); chamar("crm", "mover", { id: c.id, etapa: d.etapas[indice - 1] }).then(recarregar); } }, "←") : null,
            indice < d.etapas.length - 1 ? h("button", { class: "botao-area", title: "Próxima etapa", onclick: (e) => { e.stopPropagation(); chamar("crm", "mover", { id: c.id, etapa: d.etapas[indice + 1] }).then(recarregar); } }, "→") : null,
            botaoExcluir((e) => { e.stopPropagation(); chamar("crm", "excluir", { id: c.id }).then(recarregar); }));
        })());
      const el = h("div", { class: "cliente", onclick: (e) => { if (!e.target.closest(".acoes")) el.classList.toggle("aberto"); } },
        h("b", {}, c.nome), h("small", {}, [c.empresa, c.valor && reais(c.valor)].filter(Boolean).join(" · ") || " "),
        c.ultimo_contato ? h("small", { class: "contato" }, "último contato " + c.ultimo_contato.slice(5, 16)) : null, detalhes);
      return el;
    };
    return [
      h("div", { class: "barra-crm" },
        formulario([{ nome: "nome", rotulo: "Nome", obrigatorio: true, largura: 2 }, { nome: "telefone", rotulo: "Telefone" },
          { nome: "empresa", rotulo: "Empresa" }, { nome: "valor", rotulo: "Valor R$", tipo: "number" },
          { nome: "etapa", rotulo: "Etapa", opcoes: d.etapas.map((e) => [e, ETAPAS[e]]) }],
        (v) => chamar("crm", "salvar", v).then(recarregar), "Novo cliente"),
        h("button", { class: "botao-area destaque", onclick: () => api()?.enviar("atenda o WhatsApp") }, "Atender WhatsApp")),
      h("div", { class: "funil" }, d.etapas.map((etapa) => {
        const lista = d.clientes.filter((c) => c.etapa === etapa);
        const total = lista.reduce((s, c) => s + (c.valor || 0), 0);
        return h("div", { class: "coluna-funil" },
          h("h3", {}, ETAPAS[etapa], h("span", {}, `${lista.length}${total ? " · " + reais(total) : ""}`)),
          lista.length ? lista.map(cartao) : vazio("—"));
      })),
    ];
  },
};

// ---------- Abrir / atualizar ----------
export async function abrirArea(nome) {
  areaAtual = TITULOS[nome] ? nome : "inicio";
  document.querySelectorAll("#navegacao button").forEach((b) => b.classList.toggle("ativo", b.dataset.area === areaAtual));
  document.body.classList.toggle("com-area", areaAtual !== "inicio");
  if (areaAtual === "inicio") return;
  document.getElementById("area-titulo").textContent = TITULOS[areaAtual];
  const rolagem = conteudo.scrollTop;
  const blocos = await RENDER[areaAtual]();
  conteudo.replaceChildren(...blocos);
  conteudo.scrollTop = rolagem;
}

export function atualizarArea(nome) {
  if (nome === areaAtual || (nome === "estudos" || nome === "conhecimento") && areaAtual === "aprendizado") abrirArea(areaAtual);
}

document.querySelectorAll("#navegacao button").forEach((botao) =>
  botao.addEventListener("click", () => abrirArea(botao.dataset.area)));
document.getElementById("area-fechar").addEventListener("click", () => abrirArea("inicio"));
window.addEventListener("keydown", (e) => { if (e.key === "Escape" && areaAtual !== "inicio") abrirArea("inicio"); });
