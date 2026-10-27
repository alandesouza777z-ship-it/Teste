"""Fala (texto -> voz) e escuta (voz -> texto) do JARVIS."""

import asyncio
import os
import tempfile

import speech_recognition as sr

VOZ = os.getenv("JARVIS_VOZ", "pt-BR-AntonioNeural")
VELOCIDADE = os.getenv("JARVIS_VELOCIDADE_VOZ", "+5%")
TOM = os.getenv("JARVIS_TOM_VOZ", "-4Hz")

_reconhecedor = sr.Recognizer()
_reconhecedor.pause_threshold = 0.8
_microfone = None


def _tocar_mp3(caminho: str) -> None:
    import pygame

    if not pygame.mixer.get_init():
        pygame.mixer.init()
    pygame.mixer.music.load(caminho)
    pygame.mixer.music.play()
    while pygame.mixer.music.get_busy():
        pygame.time.wait(50)
    pygame.mixer.music.unload()


def falar(texto: str) -> None:
    """Fala o texto com voz neural (edge-tts); cai para pyttsx3 se estiver offline."""
    print(f"JARVIS: {texto}")
    if not texto.strip():
        return
    try:
        import edge_tts

        arquivo = os.path.join(tempfile.gettempdir(), "jarvis_fala.mp3")
        comunicador = edge_tts.Communicate(texto, VOZ, rate=VELOCIDADE, pitch=TOM)
        asyncio.run(comunicador.save(arquivo))
        _tocar_mp3(arquivo)
    except Exception:
        import pyttsx3

        motor = pyttsx3.init()
        motor.say(texto)
        motor.runAndWait()


def ouvir(tempo_limite: float | None = None, limite_frase: float = 15) -> str:
    """Escuta o microfone e devolve o texto reconhecido (vazio se não entendeu)."""
    global _microfone
    if _microfone is None:
        _microfone = sr.Microphone()
        with _microfone as fonte:
            _reconhecedor.adjust_for_ambient_noise(fonte, duration=1)
    with _microfone as fonte:
        try:
            audio = _reconhecedor.listen(fonte, timeout=tempo_limite, phrase_time_limit=limite_frase)
        except sr.WaitTimeoutError:
            return ""
    try:
        return _reconhecedor.recognize_google(audio, language="pt-BR")
    except (sr.UnknownValueError, sr.RequestError):
        return ""
