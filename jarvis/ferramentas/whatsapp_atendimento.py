"""Atendimento no WhatsApp Web: ler conversas não lidas e responder clientes.

O JARVIS controla uma janela própria do Google Chrome (perfil separado, guardado em
whatsapp-sessao/). Na primeira vez, escaneie o QR Code com o celular; depois a sessão fica salva.
Toda execução do navegador acontece numa única thread (exigência do Playwright).
"""

import os
import re
import threading
from concurrent.futures import ThreadPoolExecutor

import dados
from config import PASTA_USUARIO

from .base import _schema
from .confirmacao import confirmar

PASTA_SESSAO = os.path.join(PASTA_USUARIO, "whatsapp-sessao")
# "confirmar" (padrão): o JARVIS lê a resposta e pergunta antes de enviar. "automatico": envia direto.
MODO = os.getenv("JARVIS_ATENDIMENTO", "confirmar").lower()
NAVEGADOR = os.getenv("JARVIS_NAVEGADOR_WHATSAPP", "")  # caminho de um Chrome/Chromium (opcional)
ENDERECO = os.getenv("JARVIS_WHATSAPP_URL", "https://web.whatsapp.com")

LOGADO = "#pane-side"
QR_CODE = 'canvas[aria-label*="QR" i], [data-ref] canvas'
LINHAS_CONVERSA = '#pane-side [role="listitem"], #pane-side [role="row"]'
SELO_NAO_LIDA = '[aria-label*="não lida" i], [aria-label*="nao lida" i], [aria-label*="unread" i]'
MENSAGENS_RECEBIDAS = "#main .message-in"
CAIXA_TEXTO = '#main footer div[contenteditable="true"]'
BUSCA = '#side div[contenteditable="true"]'

_executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="whatsapp")
_estado = {"playwright": None, "contexto": None, "pagina": None}
_trava = threading.Lock()


def _no_navegador(funcao, *args, **kwargs):
    """Roda a função na thread do navegador e espera o resultado."""
    return _executor.submit(funcao, *args, **kwargs).result(timeout=180)


def _pagina():
    if _estado["pagina"] is not None and not _estado["pagina"].is_closed():
        return _estado["pagina"]
    from playwright.sync_api import sync_playwright

    if _estado["playwright"] is None:
        _estado["playwright"] = sync_playwright().start()
    invisivel = os.getenv("JARVIS_WHATSAPP_INVISIVEL") == "1"  # usado nos testes
    opcoes = {"headless": invisivel, "viewport": None, "args": ["--start-maximized"]}
    if NAVEGADOR:
        opcoes["executable_path"] = NAVEGADOR
    else:
        opcoes["channel"] = "chrome"  # usa o Google Chrome instalado no computador
    _estado["contexto"] = _estado["playwright"].chromium.launch_persistent_context(PASTA_SESSAO, **opcoes)
    pagina = _estado["contexto"].pages[0] if _estado["contexto"].pages else _estado["contexto"].new_page()
    pagina.goto(ENDERECO)
    _estado["pagina"] = pagina
    return pagina


def _esperar_login(pagina, segundos: float = 60) -> str | None:
    """None se logado; senão, uma mensagem dizendo o que fazer."""
    try:
        pagina.wait_for_selector(f"{LOGADO}, {QR_CODE}", timeout=segundos * 1000)
    except Exception:
        return "O WhatsApp Web não carregou a tempo. Verifique a internet."
    if pagina.query_selector(LOGADO):
        return None
    try:
        pagina.wait_for_selector(LOGADO, timeout=90_000)  # tempo para escanear o QR Code
        return None
    except Exception:
        return ("Preciso que você conecte o WhatsApp: abri uma janela do Chrome com o QR Code. "
                "No celular, vá em Aparelhos conectados e escaneie. Só precisa fazer isso uma vez.")


def _telefone_da_conversa(pagina) -> str:
    """Tenta descobrir o número do contato pelos identificadores das mensagens."""
    for elemento in pagina.query_selector_all("#main [data-id]")[-10:]:
        achado = re.search(r"(\d{10,15})@c\.us", elemento.get_attribute("data-id") or "")
        if achado:
            return "+" + achado.group(1)
    return ""


def _ler_nao_lidas(maximo: int) -> list[dict] | str:
    pagina = _pagina()
    aviso = _esperar_login(pagina)
    if aviso:
        return aviso
    pagina.wait_for_timeout(1500)
    conversas = []
    for linha in pagina.query_selector_all(LINHAS_CONVERSA):
        if len(conversas) >= maximo:
            break
        if not linha.query_selector(SELO_NAO_LIDA):
            continue
        nome_el = linha.query_selector("span[title]")
        nome = (nome_el.get_attribute("title") if nome_el else "") or "Contato"
        linha.click()
        try:
            pagina.wait_for_selector(MENSAGENS_RECEBIDAS, timeout=8000)
        except Exception:
            continue
        pagina.wait_for_timeout(600)
        textos = []
        for mensagem in pagina.query_selector_all(MENSAGENS_RECEBIDAS)[-6:]:
            texto_el = mensagem.query_selector(".selectable-text") or mensagem
            texto = texto_el.inner_text().strip()
            if texto:
                textos.append(texto)
        conversas.append({"contato": nome, "telefone": _telefone_da_conversa(pagina), "mensagens": textos})
    return conversas


def _abrir_conversa(pagina, contato: str) -> bool:
    digitos = re.sub(r"\D", "", contato)
    if len(digitos) >= 10:
        pagina.goto(f"{ENDERECO}/send?phone={digitos if len(digitos) > 11 else '55' + digitos}")
    else:
        # Primeiro procura na lista; senão, usa a busca do WhatsApp.
        alvo = pagina.query_selector(f'#pane-side span[title="{contato}"]')
        if alvo:
            alvo.click()
        else:
            busca = pagina.wait_for_selector(BUSCA, timeout=8000)
            busca.click()
            busca.fill(contato)
            pagina.wait_for_timeout(1200)
            pagina.keyboard.press("Enter")
    try:
        pagina.wait_for_selector(CAIXA_TEXTO, timeout=20_000)
        return True
    except Exception:
        return False


def _enviar(contato: str, texto: str) -> str:
    pagina = _pagina()
    aviso = _esperar_login(pagina)
    if aviso:
        return aviso
    if not _abrir_conversa(pagina, contato):
        return f"Não consegui abrir a conversa com {contato}."
    caixa = pagina.query_selector(CAIXA_TEXTO)
    caixa.click()
    linhas = texto.split("\n")
    for i, linha in enumerate(linhas):
        pagina.keyboard.insert_text(linha)  # aceita acentos e emojis
        if i < len(linhas) - 1:
            pagina.keyboard.press("Shift+Enter")
    pagina.keyboard.press("Enter")
    pagina.wait_for_timeout(800)
    return f"Mensagem enviada para {contato}."


# ---------- Ferramentas para o Claude ----------

def atender_whatsapp(maximo_conversas: int = 5) -> str:
    try:
        conversas = _no_navegador(_ler_nao_lidas, maximo_conversas)
    except Exception as erro:
        return f"Não consegui acessar o WhatsApp Web: {erro}"
    if isinstance(conversas, str):
        return conversas
    if not conversas:
        return "Nenhuma conversa não lida no WhatsApp."
    partes = ["Conversas não lidas:"]
    for c in conversas:
        # Quem ainda não está no CRM entra como lead, já com nome e telefone.
        if not dados.achar_cliente(c["telefone"]) and not dados.achar_cliente(c["contato"]):
            dados.salvar_cliente(c["contato"], c["telefone"], etapa="lead")
            from . import areas

            areas.ao_dados_mudaram("crm")
        ficha = dados.ficha_cliente(c["telefone"] or c["contato"])
        partes.append(f"\n## {c['contato']} {c['telefone']}\nÚltimas mensagens do cliente:\n"
                      + "\n".join(f"> {m}" for m in c["mensagens"]) + f"\nCRM: {ficha}")
    partes.append("\nO que o usuário te ensinou para atender clientes:\n" + dados.conhecimento_texto())
    partes.append("\nPara cada conversa: diga ao usuário em uma frase quem escreveu e o que quer, redija uma "
                  "resposta educada e curta seguindo SÓ o que foi ensinado (se não souber algo, diga que vai "
                  "verificar e retornar) e chame responder_whatsapp com o nome do contato. Atualize a etapa do cliente "
                  "com salvar_cliente quando fizer sentido.")
    return "\n".join(partes)


def responder_whatsapp(contato: str, texto: str, resumo_para_crm: str = "") -> str:
    if MODO != "automatico" and not confirmar(f"Responder {contato} com: {texto}. Posso enviar?"):
        return "O usuário não aprovou esta resposta. Pergunte o que ele quer mudar."
    try:
        resultado = _no_navegador(_enviar, contato, texto)
    except Exception as erro:
        return f"Falha ao enviar: {erro}"
    if resultado.startswith("Mensagem enviada"):
        dados.registrar_interacao(contato, resumo_para_crm or f"JARVIS respondeu: {texto[:200]}")
        from . import areas

        areas.ao_dados_mudaram("crm")
    return resultado


def enviar_mensagem(contato: str, texto: str) -> str:
    """Usado pelo enviar_whatsapp comum (contatos pessoais): sem registrar no CRM."""
    return _no_navegador(_enviar, contato, texto)


FERRAMENTAS = [
    (_schema("atender_whatsapp",
             "Lê as conversas não lidas do WhatsApp da empresa (com a ficha do CRM e o que o usuário te ensinou) "
             "para você responder os clientes. Use quando o usuário pedir para ver/atender/responder o WhatsApp.",
             {"maximo_conversas": {"type": "integer"}}), atender_whatsapp),
    (_schema("responder_whatsapp",
             "Envia uma resposta a um cliente no WhatsApp (o usuário aprova antes, a menos que o modo automático "
             "esteja ligado) e registra no CRM.",
             {"contato": {"type": "string", "description": "Nome exatamente como aparece no WhatsApp, ou o número."},
              "texto": {"type": "string"},
              "resumo_para_crm": {"type": "string", "description": "Uma linha: o que o cliente pediu e o que foi respondido."}},
             ["contato", "texto"]), responder_whatsapp),
]
