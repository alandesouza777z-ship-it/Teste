"""Controle do computador: programas, sites, volume, sistema, comandos."""

import datetime
import os
import platform
import subprocess
import webbrowser

from . import aplicativos, controle
from .aplicativos import abrir_programa
from .base import _schema
from .confirmacao import confirmar

SISTEMA = platform.system()  # "Windows", "Darwin" (macOS) ou "Linux"


def abrir_site(url: str) -> str:
    if not url.startswith(("http://", "https://")):
        url = "https://" + url
    webbrowser.open(url)
    return f"Site aberto: {url}"


def pesquisar_no_navegador(termo: str, onde: str = "google") -> str:
    from urllib.parse import quote_plus

    enderecos = {
        "google": "https://www.google.com/search?q=",
        "youtube": "https://www.youtube.com/results?search_query=",
    }
    webbrowser.open(enderecos.get(onde, enderecos["google"]) + quote_plus(termo))
    return f"Pesquisa por '{termo}' aberta no {onde}."


def controlar_volume(acao: str, passos: int = 5) -> str:
    import pyautogui

    teclas = {"aumentar": "volumeup", "diminuir": "volumedown", "mudo": "volumemute"}
    if acao not in teclas:
        return "Ação inválida. Use aumentar, diminuir ou mudo."
    pyautogui.press(teclas[acao], presses=1 if acao == "mudo" else passos)
    return f"Volume: {acao}."


def midia(acao: str) -> str:
    """Teclas de mídia do sistema (funciona com qualquer player)."""
    import pyautogui

    teclas = {"tocar_pausar": "playpause", "proxima": "nexttrack", "anterior": "prevtrack"}
    if acao not in teclas:
        return "Ação inválida."
    pyautogui.press(teclas[acao])
    return f"Mídia: {acao}."


def tirar_print() -> str:
    import pyautogui

    pasta = os.path.join(os.path.expanduser("~"), "Pictures")
    os.makedirs(pasta, exist_ok=True)
    caminho = os.path.join(pasta, f"jarvis_{datetime.datetime.now():%Y%m%d_%H%M%S}.png")
    pyautogui.screenshot(caminho)
    return f"Captura salva em {caminho}."


def info_sistema() -> str:
    import psutil

    partes = [
        f"CPU em {psutil.cpu_percent(interval=0.5)}%",
        f"memória em {psutil.virtual_memory().percent}%",
        f"disco em {psutil.disk_usage(os.path.expanduser('~')).percent}%",
    ]
    bateria = psutil.sensors_battery()
    if bateria:
        partes.append(f"bateria em {bateria.percent:.0f}%" + (" carregando" if bateria.power_plugged else ""))
    return ", ".join(partes) + "."


DIAS = ["segunda-feira", "terça-feira", "quarta-feira", "quinta-feira", "sexta-feira", "sábado", "domingo"]


def data_hora() -> str:
    agora = datetime.datetime.now()
    return f"{DIAS[agora.weekday()]}, {agora:%d/%m/%Y, %H:%M}"


def executar_comando(comando: str) -> str:
    if not confirmar(f"Devo executar o comando: {comando}?"):
        return "O usuário não autorizou o comando."
    try:
        resultado = subprocess.run(comando, shell=True, capture_output=True, text=True, timeout=60)
        saida = (resultado.stdout + resultado.stderr).strip()
        return saida[-3000:] or f"Comando executado (código {resultado.returncode})."
    except subprocess.TimeoutExpired:
        return "O comando demorou mais de 60 segundos e foi interrompido."


FERRAMENTAS = [
    (_schema("abrir_programa",
             "Abre QUALQUER aplicativo instalado pelo nome como aparece no menu Iniciar "
             "(ex.: WhatsApp, Spotify, OBS Studio, Obsidian, Claude, Discord, Microsoft Edge, Steam).",
             {"nome": {"type": "string", "description": "Nome do aplicativo."}}, ["nome"]), abrir_programa),
    (_schema("listar_aplicativos", "Lista os aplicativos instalados (opcionalmente filtrando pelo nome).",
             {"filtro": {"type": "string"}}), aplicativos.listar_aplicativos),
    (_schema("fechar_programa", "Fecha um aplicativo aberto (pede para fechar normalmente).",
             {"nome": {"type": "string"}}, ["nome"]), aplicativos.fechar_programa),
    (_schema("listar_programas_abertos", "Lista as janelas abertas no computador."),
     aplicativos.listar_programas_abertos),
    (_schema("focar_janela", "Traz para a frente uma janela aberta pelo título (ex.: 'Spotify', 'WhatsApp').",
             {"titulo": {"type": "string"}}, ["titulo"]), aplicativos.focar_janela),
    (_schema("controlar_janela", "Maximiza, minimiza, fecha, encaixa ou alterna a janela da frente; "
             "ou mostra a área de trabalho.",
             {"acao": {"type": "string", "enum": ["maximizar", "minimizar", "fechar", "mostrar_area_de_trabalho",
                                                  "alternar", "lado_esquerdo", "lado_direito"]}}, ["acao"]),
     aplicativos.controlar_janela),
    (_schema("ver_tela",
             "Tira uma foto da tela para você enxergar o que está aberto. Use antes de clicar em algo, "
             "para navegar em apps e sites, ou quando o usuário perguntar o que está na tela."),
     controle.ver_tela),
    (_schema("clicar", "Clica num ponto da tela, usando as coordenadas da última imagem de ver_tela.",
             {"x": {"type": "integer"}, "y": {"type": "integer"},
              "botao": {"type": "string", "enum": ["esquerdo", "direito", "meio"]},
              "duplo": {"type": "boolean"}}, ["x", "y"]), controle.clicar),
    (_schema("pressionar_teclas", "Pressiona uma tecla ou atalho, ex.: 'enter', 'ctrl+t', 'ctrl+w', 'win+d', 'space'.",
             {"teclas": {"type": "string"}}, ["teclas"]), controle.pressionar_teclas),
    (_schema("rolar", "Rola a página/janela da frente.",
             {"direcao": {"type": "string", "enum": ["cima", "baixo"]}, "quantidade": {"type": "integer"}}),
     controle.rolar),
    (_schema("abrir_caminho", "Abre uma pasta ou arquivo: caminho completo ou nomes como "
             "'downloads', 'documentos', 'área de trabalho', 'imagens'.",
             {"caminho": {"type": "string"}}, ["caminho"]), controle.abrir_caminho),
    (_schema("procurar_arquivos", "Procura arquivos ou pastas pelo nome na pasta do usuário.",
             {"nome": {"type": "string"}, "pasta": {"type": "string", "description": "Opcional: downloads, documentos..."}},
             ["nome"]), controle.procurar_arquivos),
    (_schema("abrir_site", "Abre um site no navegador padrão.",
             {"url": {"type": "string"}}, ["url"]), abrir_site),
    (_schema("pesquisar_no_navegador", "Abre uma pesquisa no Google ou YouTube no navegador para o usuário ver.",
             {"termo": {"type": "string"}, "onde": {"type": "string", "enum": ["google", "youtube"]}}, ["termo"]),
     pesquisar_no_navegador),
    (_schema("controlar_volume", "Aumenta, diminui ou silencia o volume do sistema.",
             {"acao": {"type": "string", "enum": ["aumentar", "diminuir", "mudo"]},
              "passos": {"type": "integer", "description": "Quantos níveis (cada um ~2%). Padrão 5."}}, ["acao"]),
     controlar_volume),
    (_schema("midia", "Teclas de mídia do sistema: tocar/pausar, próxima, anterior (qualquer player).",
             {"acao": {"type": "string", "enum": ["tocar_pausar", "proxima", "anterior"]}}, ["acao"]), midia),
    (_schema("digitar_texto", "Digita um texto onde o cursor estiver (aceita acentos).",
             {"texto": {"type": "string"}}, ["texto"]), controle.digitar_texto),
    (_schema("tirar_print", "Tira uma captura de tela e salva na pasta Imagens."), tirar_print),
    (_schema("info_sistema", "Mostra uso de CPU, memória, disco e bateria."), info_sistema),
    (_schema("data_hora", "Data e hora atuais do computador."), data_hora),
    (_schema("executar_comando",
             "Executa um comando de terminal no computador do usuário (o usuário confirma antes). "
             "Use para tarefas que as outras ferramentas não cobrem: desligar, bloquear, listar arquivos etc.",
             {"comando": {"type": "string"}}, ["comando"]), executar_comando),
]
