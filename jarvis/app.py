"""J.A.R.V.I.S. — aplicativo com interface: janela sem bordas e esfera 3D que reage à voz.

Uso:
    python app.py

A fala é tocada pela própria interface, que analisa o áudio em tempo real para
fazer a esfera e o espectro reagirem à voz.
"""

import atexit
import base64
import json
import os
import sys
import threading

import config  # carrega o .env antes dos outros módulos

# Deixa a interface tocar a voz sem precisar de um clique (o JARVIS pode abrir pelas palmas).
os.environ.setdefault("WEBVIEW2_ADDITIONAL_BROWSER_ARGUMENTS", "--autoplay-policy=no-user-gesture-required")

import webview  # noqa: E402

from assistente import Assistente  # noqa: E402
from ferramentas import aplicativos  # noqa: E402

ARQUIVO_PID = os.path.join(config.PASTA_USUARIO, ".jarvis.pid")
EFEITO_VOZ = os.getenv("JARVIS_EFEITO_VOZ", "1") != "0"

janela = None
assistente = None
modo_pendente = None
fala_terminou = threading.Event()


def _js(funcao: str, *argumentos) -> None:
    if janela is not None:
        janela.evaluate_js(f"jarvis.{funcao}({', '.join(json.dumps(a) for a in argumentos)})")


def tocar_na_interface(audio: bytes) -> None:
    """Manda o MP3 para a interface tocar (e animar a esfera) e espera acabar."""
    fala_terminou.clear()
    _js("falar", base64.b64encode(audio).decode())
    # A interface avisa quando o áudio acaba; o limite evita travar se algo falhar.
    # (MP3 de voz tem pelo menos ~6000 bytes por segundo.)
    fala_terminou.wait(timeout=len(audio) / 6000 + 3)


def falar_offline_na_interface(texto: str) -> None:
    """Sem internet: voz do sistema, com a esfera simulando a fala."""
    import voz

    _js("falarSemAudio", max(1.5, len(texto) / 14))
    voz.falar_offline(texto)


def _registrar_aberto() -> None:
    """Avisa o detector de palmas que o JARVIS está aberto (ele para de ouvir palmas)."""
    try:
        with open(ARQUIVO_PID, "w") as arquivo:
            arquivo.write(str(os.getpid()))
        atexit.register(lambda: os.path.exists(ARQUIVO_PID) and os.remove(ARQUIVO_PID))
    except OSError:
        pass


class Api:
    """Funções que a interface (JavaScript) pode chamar via window.pywebview.api."""

    def configuracao(self):
        from cerebro import MODOS

        modo = os.getenv("JARVIS_MODO_RESPOSTA", "curta")
        return {"efeitoVoz": EFEITO_VOZ, "modo": modo if modo in MODOS else "curta"}

    def definir_modo(self, modo):
        """Curta, moderada ou longa (botões da interface)."""
        global modo_pendente
        modo_pendente = modo
        if assistente is not None:
            assistente.definir_modo(modo)

    def definir_mudo(self, mudo):
        """Botão do microfone: True = parar de ouvir."""
        if assistente is not None:
            assistente.definir_mudo(bool(mudo))

    def iniciar(self):
        global assistente
        if assistente is not None:
            return
        if not os.getenv("ANTHROPIC_API_KEY"):
            _js("mensagem", "jarvis", f"Chave da API não encontrada. Crie o arquivo .env em {config.PASTA_USUARIO}.")
            return
        assistente = Assistente(
            tocar_audio=tocar_na_interface,
            tocar_offline=falar_offline_na_interface,
            ao_estado=lambda estado: _js("estado", estado),
            ao_mensagem=lambda quem, texto: _js("mensagem", quem, texto),
            ao_confirmar=lambda pergunta: _js("confirmar", pergunta),
            ao_encerrar=lambda: janela.destroy(),
            ao_modo=lambda modo: _js("modo", modo),
            ao_mudo=lambda mudo: _js("mudo", mudo),
            ao_tempos=lambda texto: (print(texto), _js("tempos", texto)),
            veio_das_palmas="--palmas" in sys.argv,
        )
        if modo_pendente:
            assistente.definir_modo(modo_pendente)
        threading.Thread(target=assistente.rodar, daemon=True).start()

    def enviar(self, texto):
        if assistente is not None and texto.strip():
            assistente.enviar(texto.strip())

    def audio_terminou(self):
        fala_terminou.set()

    def sistema(self):
        """Números para o painel de sistema da interface."""
        import psutil

        bateria = psutil.sensors_battery()
        return {
            "cpu": psutil.cpu_percent(),
            "memoria": psutil.virtual_memory().percent,
            "disco": psutil.disk_usage(os.path.expanduser("~")).percent,
            "bateria": round(bateria.percent) if bateria else None,
            "carregando": bool(bateria and bateria.power_plugged),
        }

    def minimizar(self):
        janela.minimize()

    def maximizar(self):
        janela.toggle_fullscreen()

    def fechar(self):
        janela.destroy()


def main() -> None:
    global janela
    _registrar_aberto()
    aplicativos.preparar()
    janela = webview.create_window(
        "J.A.R.V.I.S.",
        os.path.join(config.PASTA_PROGRAMA, "web", "index.html"),
        js_api=Api(),
        width=1280,
        height=820,
        min_size=(760, 540),
        background_color="#000000",
        frameless=True,
        easy_drag=False,
    )
    webview.start(debug="--debug" in sys.argv)


if __name__ == "__main__":
    main()
