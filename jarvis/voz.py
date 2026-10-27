"""Fala (texto -> voz) e escuta (voz -> texto) do JARVIS."""

import asyncio
import io
import os
import queue
import re
import threading
import unicodedata
from difflib import SequenceMatcher

import speech_recognition as sr

VOZ = os.getenv("JARVIS_VOZ", "pt-BR-AntonioNeural")
VELOCIDADE = os.getenv("JARVIS_VELOCIDADE_VOZ", "+8%")
TOM = os.getenv("JARVIS_TOM_VOZ", "+0Hz")
PALAVRA_ATIVACAO = os.getenv("JARVIS_PALAVRA_ATIVACAO", "jarvis").lower()

# Como o reconhecedor costuma ouvir "Jarvis" errado.
APELIDOS_ATIVACAO = {PALAVRA_ATIVACAO, "jarvis", "jarvas", "jarbas", "javis", "jarves", "jarviz",
                     "djarvis", "jervis", "jarvi", "jaques", "jarvys", "garvis", "harvis"}

# ---------- Escuta ----------

_reconhecedor = sr.Recognizer()
_reconhecedor.dynamic_energy_threshold = True   # se adapta ao barulho do ambiente
_reconhecedor.pause_threshold = 0.9             # silêncio que encerra a frase (não corta no meio)
_reconhecedor.non_speaking_duration = 0.4
_reconhecedor.phrase_threshold = 0.2
_microfone = None


def _sem_acento(texto: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", texto.lower()) if unicodedata.category(c) != "Mn")


def separar_ativacao(frase: str) -> str | None:
    """Se a frase chama o JARVIS, devolve o pedido que vem depois (pode ser ""). Senão, None."""
    palavras = frase.split()
    for i, palavra in enumerate(palavras):
        limpa = re.sub(r"[^a-z]", "", _sem_acento(palavra))
        if not limpa:
            continue
        if limpa in APELIDOS_ATIVACAO or SequenceMatcher(None, limpa, PALAVRA_ATIVACAO).ratio() >= 0.8:
            return " ".join(palavras[i + 1:]).strip(" ,.!?")
    return None


def ouvir_alternativas(tempo_limite: float | None = None, limite_frase: float = 15) -> list[str]:
    """Escuta o microfone e devolve as interpretações possíveis da frase (a mais provável primeiro)."""
    global _microfone
    if _microfone is None:
        _microfone = sr.Microphone()
        with _microfone as fonte:
            _reconhecedor.adjust_for_ambient_noise(fonte, duration=1.5)
    with _microfone as fonte:
        try:
            audio = _reconhecedor.listen(fonte, timeout=tempo_limite, phrase_time_limit=limite_frase)
        except sr.WaitTimeoutError:
            return []
    try:
        resultado = _reconhecedor.recognize_google(audio, language="pt-BR", show_all=True)
    except (sr.UnknownValueError, sr.RequestError):
        return []
    if not resultado or not isinstance(resultado, dict):
        return []
    return [alt["transcript"] for alt in resultado.get("alternative", []) if alt.get("transcript")]


def ouvir(tempo_limite: float | None = None, limite_frase: float = 15) -> str:
    alternativas = ouvir_alternativas(tempo_limite, limite_frase)
    return alternativas[0] if alternativas else ""


# ---------- Fala ----------

def preparar_para_fala(texto: str) -> str:
    """Tira a pontuação que faz a voz parar no meio da frase (vírgulas, travessões etc.)."""
    texto = re.sub(r"[*_#`]", "", texto)
    # Mantém vírgula e dois-pontos entre dígitos ("5,34", "17:30").
    texto = re.sub(r"\s*(?:,(?!\d)|(?<!\d),|:(?!\d)|[;—–()])\s*", " ", texto)
    return re.sub(r"\s{2,}", " ", texto).strip()


def sintetizar(texto: str) -> bytes:
    """Gera o áudio MP3 da fala com voz neural (edge-tts, precisa de internet)."""
    import edge_tts

    async def _gerar() -> bytes:
        audio = b""
        comunicador = edge_tts.Communicate(preparar_para_fala(texto), VOZ, rate=VELOCIDADE, pitch=TOM)
        async for pedaco in comunicador.stream():
            if pedaco["type"] == "audio":
                audio += pedaco["data"]
        return audio

    return asyncio.run(_gerar())


def tocar_mp3(audio: bytes) -> None:
    import pygame

    if not pygame.mixer.get_init():
        pygame.mixer.init()
    pygame.mixer.music.load(io.BytesIO(audio), "mp3")
    pygame.mixer.music.play()
    while pygame.mixer.music.get_busy():
        pygame.time.wait(30)
    pygame.mixer.music.unload()


def falar_offline(texto: str) -> None:
    import pyttsx3

    motor = pyttsx3.init()
    motor.say(preparar_para_fala(texto))
    motor.runAndWait()


def falar(texto: str) -> None:
    """Fala o texto e espera terminar (cai para a voz do sistema se estiver offline)."""
    print(f"JARVIS: {texto}")
    if not texto.strip():
        return
    try:
        tocar_mp3(sintetizar(texto))
    except Exception:
        falar_offline(texto)


class Locutor:
    """Fala frases em sequência sem travar quem chama.

    Enquanto uma frase toca, a próxima já está sendo gerada, então o JARVIS
    começa a falar assim que a primeira frase da resposta fica pronta.
    """

    def __init__(self, tocar_audio=tocar_mp3, tocar_offline=falar_offline, ao_iniciar=None, ao_terminar=None):
        self.tocar_audio = tocar_audio
        self.tocar_offline = tocar_offline
        self.ao_iniciar = ao_iniciar or (lambda texto: print(f"JARVIS: {texto}"))
        self.ao_terminar = ao_terminar or (lambda: None)
        self._textos: queue.Queue[str] = queue.Queue()
        self._audios: queue.Queue = queue.Queue(maxsize=2)
        self._pendentes = 0
        self._condicao = threading.Condition()
        threading.Thread(target=self._sintetizar, daemon=True).start()
        threading.Thread(target=self._reproduzir, daemon=True).start()

    def dizer(self, texto: str) -> None:
        if not texto.strip():
            return
        with self._condicao:
            self._pendentes += 1
        self._textos.put(texto)

    def esperar(self) -> None:
        """Bloqueia até terminar de falar tudo o que foi pedido."""
        with self._condicao:
            while self._pendentes:
                self._condicao.wait()

    def _sintetizar(self) -> None:
        while True:
            texto = self._textos.get()
            try:
                audio = sintetizar(texto)
            except Exception:
                audio = None
            self._audios.put((texto, audio))

    def _reproduzir(self) -> None:
        while True:
            texto, audio = self._audios.get()
            try:
                self.ao_iniciar(texto)
                if audio:
                    self.tocar_audio(audio)
                else:
                    self.tocar_offline(texto)
            except Exception as erro:
                print(f"Erro ao falar: {erro}")
            with self._condicao:
                self._pendentes -= 1
                if not self._pendentes:
                    self.ao_terminar()
                    self._condicao.notify_all()
