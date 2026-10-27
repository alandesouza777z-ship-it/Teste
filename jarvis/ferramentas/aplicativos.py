"""Abrir, fechar e alternar aplicativos instalados.

No Windows, a lista vem do próprio menu Iniciar (Get-StartApps), que inclui
programas comuns e apps da Microsoft Store (WhatsApp, Spotify, Claude...).
"""

import json
import os
import platform
import re
import shutil
import subprocess
import threading
import unicodedata
from difflib import get_close_matches

SISTEMA = platform.system()

# Jeitos comuns de chamar um app -> nome como aparece no menu Iniciar.
APELIDOS = {
    "zap": "whatsapp", "whats": "whatsapp", "wpp": "whatsapp",
    "edge": "microsoft edge", "chrome": "google chrome", "navegador": "google chrome",
    "obs": "obs studio", "vscode": "visual studio code", "vs code": "visual studio code",
    "code": "visual studio code", "explorador": "explorador de arquivos", "arquivos": "explorador de arquivos",
    "calculadora": "calculadora", "bloco de notas": "bloco de notas", "configuracoes": "configurações",
    "gerenciador de tarefas": "gerenciador de tarefas", "word": "word", "excel": "excel",
}
# Processos de cada app, para fechar.
PROCESSOS = {
    "microsoft edge": "msedge", "google chrome": "chrome", "obs studio": "obs64",
    "visual studio code": "code", "word": "winword", "excel": "excel", "powerpoint": "powerpnt",
    "explorador de arquivos": "explorer", "bloco de notas": "notepad", "calculadora": "calculatorapp",
}
PROTEGIDOS = {"explorer", "svchost", "system", "winlogon", "csrss", "lsass", "services", "dwm", "jarvis", "python"}

_indice: dict[str, str] = {}
_carregando = threading.Lock()


def _normalizar(texto: str) -> str:
    texto = "".join(c for c in unicodedata.normalize("NFD", texto.lower()) if unicodedata.category(c) != "Mn")
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9 ]", " ", texto)).strip()


def _carregar_indice() -> dict[str, str]:
    """nome normalizado -> identificador para abrir (AppID no Windows)."""
    with _carregando:
        if _indice:
            return _indice
        if SISTEMA == "Windows":
            try:
                saida = subprocess.run(
                    ["powershell", "-NoProfile", "-Command",
                     "[Console]::OutputEncoding=[Text.Encoding]::UTF8; Get-StartApps | ConvertTo-Json -Compress"],
                    capture_output=True, text=True, encoding="utf-8", timeout=20,
                    creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
                ).stdout
                apps = json.loads(saida or "[]")
                for app in apps if isinstance(apps, list) else [apps]:
                    _indice.setdefault(_normalizar(app["Name"]), app["AppID"])
            except Exception as erro:
                print(f"Não consegui listar os apps do menu Iniciar: {erro}")
        elif SISTEMA == "Linux":
            for pasta in ("/usr/share/applications", os.path.expanduser("~/.local/share/applications")):
                if os.path.isdir(pasta):
                    for arquivo in os.listdir(pasta):
                        if arquivo.endswith(".desktop"):
                            _indice.setdefault(_normalizar(arquivo[:-8].split(".")[-1]), arquivo[:-8])
        return _indice


def preparar() -> None:
    """Monta o índice em segundo plano, para o primeiro pedido já ser rápido."""
    threading.Thread(target=_carregar_indice, daemon=True).start()


def _encontrar(nome: str) -> tuple[str, str] | None:
    indice = _carregar_indice()
    procurado = _normalizar(nome)
    procurado = _normalizar(APELIDOS.get(procurado, procurado))
    if procurado in indice:
        return procurado, indice[procurado]
    comeca = [n for n in indice if n.startswith(procurado)]
    contem = [n for n in indice if procurado in n.split() or procurado in n]
    for lista in (comeca, contem):
        if lista:
            melhor = min(lista, key=len)
            return melhor, indice[melhor]
    parecidos = get_close_matches(procurado, indice, n=1, cutoff=0.6)
    return (parecidos[0], indice[parecidos[0]]) if parecidos else None


def abrir_programa(nome: str) -> str:
    try:
        if SISTEMA == "Windows":
            achado = _encontrar(nome)
            if achado:
                titulo, app_id = achado
                subprocess.Popen(["explorer.exe", f"shell:AppsFolder\\{app_id}"])
                return f"Abrindo {titulo}."
            parecidos = get_close_matches(_normalizar(nome), _carregar_indice(), n=5, cutoff=0.4)
            return (f"Não achei '{nome}' entre os apps instalados. "
                    f"Parecidos: {', '.join(parecidos) or 'nenhum'}. Tente um desses nomes.")
        if SISTEMA == "Darwin":
            subprocess.Popen(["open", "-a", nome])
            return f"Abrindo {nome}."
        achado = _encontrar(nome)
        if achado:
            subprocess.Popen(["gtk-launch", achado[1]])
            return f"Abrindo {achado[0]}."
        executavel = shutil.which(nome) or shutil.which(nome.lower())
        if executavel:
            subprocess.Popen([executavel])
            return f"Abrindo {nome}."
        return f"Não achei o programa '{nome}'."
    except Exception as erro:
        return f"Não consegui abrir {nome}: {erro}"


def listar_aplicativos(filtro: str = "") -> str:
    nomes = sorted(_carregar_indice())
    if filtro:
        nomes = [n for n in nomes if _normalizar(filtro) in n]
    return ", ".join(nomes[:150]) or "Nenhum aplicativo encontrado."


def _processos_do_app(nome: str):
    import psutil

    procurado = _normalizar(APELIDOS.get(_normalizar(nome), nome))
    alvo = PROCESSOS.get(procurado, procurado.replace(" ", ""))
    encontrados = []
    for proc in psutil.process_iter(["name", "pid"]):
        processo = (proc.info["name"] or "").lower().removesuffix(".exe")
        if processo in PROTEGIDOS:
            continue
        if alvo and (alvo in processo or processo in alvo.split()):
            encontrados.append(proc)
    return encontrados


def fechar_programa(nome: str) -> str:
    processos = _processos_do_app(nome)
    if not processos:
        return f"Não encontrei '{nome}' aberto. Use listar_programas_abertos para ver os nomes."
    nomes = sorted({p.info["name"] for p in processos})
    for executavel in nomes:
        if SISTEMA == "Windows":
            # Sem /F: pede para o programa fechar normalmente (ele pode perguntar se quer salvar).
            subprocess.run(["taskkill", "/IM", executavel], capture_output=True,
                           creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        else:
            for p in processos:
                p.terminate()
    return f"Pedi para fechar: {', '.join(nomes)}."


def listar_programas_abertos() -> str:
    try:
        import pygetwindow

        titulos = sorted({t.strip() for t in pygetwindow.getAllTitles() if t.strip()})
        return "Janelas abertas: " + " | ".join(titulos[:60])
    except Exception:
        import psutil

        nomes = sorted({(p.info["name"] or "") for p in psutil.process_iter(["name"])} - {""})
        return "Processos: " + ", ".join(nomes[:120])


def focar_janela(titulo: str) -> str:
    try:
        import pygetwindow
    except ImportError:
        return "Alternar janelas só funciona no Windows."
    procurado = _normalizar(titulo)
    janelas = [j for j in pygetwindow.getAllWindows() if j.title.strip() and procurado in _normalizar(j.title)]
    if not janelas:
        return f"Nenhuma janela com '{titulo}' no título. Use listar_programas_abertos."
    janela = janelas[0]
    try:
        if janela.isMinimized:
            janela.restore()
        janela.activate()
    except Exception:
        # O Windows às vezes bloqueia trazer janela para frente; minimizar e restaurar resolve.
        janela.minimize()
        janela.restore()
    return f"Janela em primeiro plano: {janela.title}."


def controlar_janela(acao: str) -> str:
    """Age na janela que está em primeiro plano."""
    import pyautogui

    atalhos = {
        "maximizar": ("win", "up"), "minimizar": ("win", "down"), "fechar": ("alt", "f4"),
        "mostrar_area_de_trabalho": ("win", "d"), "alternar": ("alt", "tab"),
        "lado_esquerdo": ("win", "left"), "lado_direito": ("win", "right"),
    }
    if acao not in atalhos:
        return "Ação inválida."
    if acao != "mostrar_area_de_trabalho":
        from .controle import _tirar_jarvis_da_frente

        _tirar_jarvis_da_frente()  # nunca age (nem fecha) a janela do próprio JARVIS
    pyautogui.hotkey(*atalhos[acao])
    return f"Janela: {acao}."
