"""Controle do computador: programas, sites, volume, sistema, comandos."""

import datetime
import os
import platform
import shutil
import subprocess
import webbrowser

from .confirmacao import confirmar

SISTEMA = platform.system()  # "Windows", "Darwin" (macOS) ou "Linux"


def abrir_programa(nome: str) -> str:
    try:
        if SISTEMA == "Windows":
            # "start" acha programas registrados (chrome, spotify, notepad, calc...)
            subprocess.Popen(f'start "" "{nome}"', shell=True)
        elif SISTEMA == "Darwin":
            subprocess.Popen(["open", "-a", nome])
        else:
            executavel = shutil.which(nome) or shutil.which(nome.lower())
            if executavel:
                subprocess.Popen([executavel])
            else:
                subprocess.Popen(["gtk-launch", nome.lower()])
        return f"Abrindo {nome}."
    except Exception as erro:
        return f"Não consegui abrir {nome}: {erro}"


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


def digitar_texto(texto: str) -> str:
    import pyautogui

    pyautogui.write(texto, interval=0.02)
    return "Texto digitado."


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


def _schema(nome, descricao, propriedades=None, obrigatorios=None):
    return {
        "name": nome,
        "description": descricao,
        "input_schema": {
            "type": "object",
            "properties": propriedades or {},
            "required": obrigatorios or [],
        },
    }


FERRAMENTAS = [
    (_schema("abrir_programa", "Abre um programa instalado no computador (ex.: chrome, spotify, notepad, calculadora, vscode).",
             {"nome": {"type": "string", "description": "Nome do programa/executável."}}, ["nome"]), abrir_programa),
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
    (_schema("digitar_texto", "Digita um texto onde o cursor estiver.",
             {"texto": {"type": "string"}}, ["texto"]), digitar_texto),
    (_schema("tirar_print", "Tira uma captura de tela e salva na pasta Imagens."), tirar_print),
    (_schema("info_sistema", "Mostra uso de CPU, memória, disco e bateria."), info_sistema),
    (_schema("data_hora", "Data e hora atuais do computador."), data_hora),
    (_schema("executar_comando",
             "Executa um comando de terminal no computador do usuário (o usuário confirma antes). "
             "Use para tarefas que as outras ferramentas não cobrem: desligar, bloquear, listar arquivos etc.",
             {"comando": {"type": "string"}}, ["comando"]), executar_comando),
]
