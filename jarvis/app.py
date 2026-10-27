"""J.A.R.V.I.S. — aplicativo com interface: janela preta e esfera 3D que reage à voz.

Uso:
    python app.py

A fala é tocada pela própria interface, que analisa o áudio em tempo real para
fazer a esfera pulsar com os graves.
"""

import base64
import json
import os
import sys
import threading

import config  # carrega o .env antes dos outros módulos

import webview  # noqa: E402

from assistente import Assistente  # noqa: E402

janela = None
assistente = None
fala_terminou = threading.Event()


def _js(funcao: str, *argumentos) -> None:
    if janela is not None:
        janela.evaluate_js(f"jarvis.{funcao}({', '.join(json.dumps(a) for a in argumentos)})")


def tocar_na_interface(audio: bytes) -> None:
    """Manda o MP3 para a interface tocar (e animar a esfera) e espera acabar."""
    fala_terminou.clear()
    _js("falar", base64.b64encode(audio).decode())
    # A interface avisa quando o áudio acaba; o limite evita travar se algo falhar.
    # (edge-tts gera MP3 a 48 kbps: ~6000 bytes por segundo de fala.)
    fala_terminou.wait(timeout=len(audio) / 6000 + 3)


def falar_offline_na_interface(texto: str) -> None:
    """Sem internet: voz do sistema, com a esfera simulando a fala."""
    import voz

    _js("falarSemAudio", max(1.5, len(texto) / 14))
    voz.falar_offline(texto)


class Api:
    """Funções que a interface (JavaScript) pode chamar via window.pywebview.api."""

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
        )
        threading.Thread(target=assistente.rodar, daemon=True).start()

    def enviar(self, texto):
        if assistente is not None and texto.strip():
            assistente.enviar(texto.strip())

    def audio_terminou(self):
        fala_terminou.set()


def main() -> None:
    global janela
    janela = webview.create_window(
        "J.A.R.V.I.S.",
        os.path.join(config.PASTA_PROGRAMA, "web", "index.html"),
        js_api=Api(),
        width=1200,
        height=800,
        min_size=(700, 500),
        background_color="#000000",
    )
    webview.start(debug="--debug" in sys.argv)


if __name__ == "__main__":
    main()
