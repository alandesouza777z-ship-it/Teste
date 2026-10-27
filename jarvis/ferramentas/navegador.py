"""Google Chrome e WhatsApp Web: abrir sites e contar conversas não lidas."""

import os
import platform
import re
import shutil
import subprocess
import time
import webbrowser

from .base import _schema

SISTEMA = platform.system()
WHATSAPP_WEB = "https://web.whatsapp.com"
# O WhatsApp Web mostra no título da aba "(5) WhatsApp" quando há 5 conversas não lidas.
TITULO_WHATSAPP = re.compile(r"^\((\d+)\)\s*WhatsApp", re.I)


def _caminho_chrome() -> str | None:
    if SISTEMA != "Windows":
        return shutil.which("google-chrome") or shutil.which("chromium")
    for base in (os.getenv("PROGRAMFILES"), os.getenv("PROGRAMFILES(X86)"), os.getenv("LOCALAPPDATA")):
        if base:
            caminho = os.path.join(base, "Google", "Chrome", "Application", "chrome.exe")
            if os.path.exists(caminho):
                return caminho
    return shutil.which("chrome")


def abrir_no_chrome(urls: list[str] | str, nova_janela: bool = False) -> str:
    """Abre um ou mais sites no Google Chrome (ou no navegador padrão, se não houver Chrome)."""
    urls = [urls] if isinstance(urls, str) else list(urls)
    urls = [u if u.startswith(("http://", "https://")) else "https://" + u for u in urls]
    chrome = _caminho_chrome()
    if chrome:
        subprocess.Popen([chrome, *(["--new-window"] if nova_janela else []), *urls])
        return f"Abri no Chrome: {', '.join(urls)}."
    for url in urls:
        webbrowser.open(url)
    return f"Chrome não encontrado; abri no navegador padrão: {', '.join(urls)}."


def _titulos_whatsapp() -> list[str]:
    try:
        import pygetwindow

        return [t for t in pygetwindow.getAllTitles() if "whatsapp" in t.lower()]
    except Exception:
        return []


def contar_nao_lidas(espera_maxima: float = 0) -> int | None:
    """Conversas não lidas no WhatsApp Web (pelo título da aba). None se não estiver aberto.

    Com espera_maxima, aguarda o WhatsApp Web carregar (ele leva alguns segundos).
    """
    limite = time.time() + espera_maxima
    visto = False
    while True:
        for titulo in _titulos_whatsapp():
            visto = True
            achado = TITULO_WHATSAPP.match(titulo.strip())
            if achado:
                return int(achado.group(1))
        if time.time() >= limite:
            return 0 if visto else None
        time.sleep(1)


def whatsapp_nao_lidas() -> str:
    quantidade = contar_nao_lidas()
    if quantidade is None:
        return ("O WhatsApp Web não está aberto (ou não é a aba ativa do Chrome). "
                "Abra com abrir_whatsapp_web e pergunte de novo em alguns segundos.")
    return f"{quantidade} conversas com mensagens não lidas no WhatsApp."


def abrir_whatsapp_web() -> str:
    return abrir_no_chrome(WHATSAPP_WEB, nova_janela=True)


FERRAMENTAS = [
    (_schema("abrir_no_chrome", "Abre um ou mais sites no Google Chrome.",
             {"urls": {"type": "array", "items": {"type": "string"}},
              "nova_janela": {"type": "boolean"}}, ["urls"]), abrir_no_chrome),
    (_schema("abrir_whatsapp_web", "Abre o WhatsApp Web (WhatsApp da empresa) numa janela do Chrome."),
     abrir_whatsapp_web),
    (_schema("whatsapp_nao_lidas",
             "Diz quantas conversas têm mensagens não lidas no WhatsApp Web (precisa estar aberto)."),
     whatsapp_nao_lidas),
]
