"""Navegar pelo computador: ver a tela, clicar, usar atalhos, abrir pastas e arquivos."""

import base64
import io
import os
import platform
import subprocess
import time

SISTEMA = platform.system()
LARGURA_IMAGEM = 1280  # a tela é reduzida para esta largura antes de ir para o Claude
_escala = 1.0          # fator para converter coordenadas da imagem -> tela real

PASTAS = {
    "downloads": "Downloads", "documentos": "Documents", "area de trabalho": "Desktop",
    "área de trabalho": "Desktop", "desktop": "Desktop", "imagens": "Pictures", "fotos": "Pictures",
    "musicas": "Music", "músicas": "Music", "videos": "Videos", "vídeos": "Videos",
}


def _janela_ativa_e_jarvis() -> bool:
    try:
        import pygetwindow

        ativa = pygetwindow.getActiveWindow()
        return bool(ativa and "J.A.R.V.I.S" in ativa.title)
    except Exception:
        return False


def _tirar_jarvis_da_frente() -> None:
    """Se o JARVIS estiver em primeiro plano, passa para a janela de trás antes de agir."""
    if _janela_ativa_e_jarvis():
        import pyautogui

        pyautogui.hotkey("alt", "tab")
        time.sleep(0.4)


def ver_tela():
    """Captura a tela e devolve como imagem para o Claude enxergar."""
    global _escala
    import pyautogui

    _tirar_jarvis_da_frente()
    imagem = pyautogui.screenshot()
    _escala = imagem.width / LARGURA_IMAGEM
    imagem = imagem.resize((LARGURA_IMAGEM, round(imagem.height / _escala)))
    buffer = io.BytesIO()
    imagem.convert("RGB").save(buffer, format="JPEG", quality=70)
    return [
        {"type": "image", "source": {"type": "base64", "media_type": "image/jpeg",
                                     "data": base64.b64encode(buffer.getvalue()).decode()}},
        {"type": "text", "text": f"Tela capturada ({LARGURA_IMAGEM}x{imagem.height}). "
                                 "Use essas coordenadas em clicar."},
    ]


def clicar(x: int, y: int, botao: str = "esquerdo", duplo: bool = False) -> str:
    import pyautogui

    real_x, real_y = round(x * _escala), round(y * _escala)
    pyautogui.click(real_x, real_y, clicks=2 if duplo else 1,
                    button={"esquerdo": "left", "direito": "right", "meio": "middle"}.get(botao, "left"))
    return f"Cliquei em ({x}, {y})."


def pressionar_teclas(teclas: str) -> str:
    """Ex.: "enter", "ctrl+t", "alt+tab", "win+d", "ctrl+shift+esc"."""
    import pyautogui

    _tirar_jarvis_da_frente()
    partes = [p.strip().lower() for p in teclas.replace(" ", "").split("+") if p.strip()]
    nomes = {"windows": "win", "control": "ctrl", "esc": "escape", "del": "delete", "apagar": "backspace"}
    partes = [nomes.get(p, p) for p in partes]
    if len(partes) == 1:
        pyautogui.press(partes[0])
    else:
        pyautogui.hotkey(*partes)
    return f"Teclas pressionadas: {teclas}."


def digitar_texto(texto: str) -> str:
    """Digita onde o cursor estiver (cola pela área de transferência para aceitar acentos)."""
    import pyautogui
    import pyperclip

    _tirar_jarvis_da_frente()
    pyperclip.copy(texto)
    pyautogui.hotkey("command" if SISTEMA == "Darwin" else "ctrl", "v")
    return "Texto digitado."


def rolar(direcao: str = "baixo", quantidade: int = 5) -> str:
    import pyautogui

    pyautogui.scroll((-1 if direcao == "baixo" else 1) * quantidade * 120)
    return f"Rolei para {direcao}."


def abrir_caminho(caminho: str) -> str:
    """Abre uma pasta ou arquivo (aceita nomes como "downloads" ou "documentos")."""
    casa = os.path.expanduser("~")
    alvo = PASTAS.get(caminho.strip().lower())
    alvo = os.path.join(casa, alvo) if alvo else os.path.expandvars(os.path.expanduser(caminho))
    if not os.path.exists(alvo):
        return f"Não encontrei '{caminho}'. Use procurar_arquivos para achar o caminho certo."
    if SISTEMA == "Windows":
        os.startfile(alvo)
    else:
        subprocess.Popen(["open" if SISTEMA == "Darwin" else "xdg-open", alvo])
    return f"Abrindo {alvo}."


def procurar_arquivos(nome: str, pasta: str = "") -> str:
    """Procura arquivos e pastas pelo nome dentro da pasta do usuário."""
    casa = os.path.expanduser("~")
    raiz = os.path.join(casa, PASTAS.get(pasta.lower(), pasta)) if pasta else casa
    procurado = nome.lower()
    achados, inicio = [], time.time()
    for atual, pastas, arquivos in os.walk(raiz):
        pastas[:] = [p for p in pastas if not p.startswith(".") and p not in ("AppData", "node_modules", "$Recycle.Bin")]
        for item in pastas + arquivos:
            if procurado in item.lower():
                achados.append(os.path.join(atual, item))
        if len(achados) >= 20 or time.time() - inicio > 8:
            break
    return "\n".join(achados) if achados else f"Nada com '{nome}' encontrado em {raiz}."
