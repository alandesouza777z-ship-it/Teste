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

# "whisper" (padrão, roda no computador, muito mais preciso) ou "google" (online, mais leve).
RECONHECIMENTO = os.getenv("JARVIS_RECONHECIMENTO", "whisper").lower()
# Modelos do Whisper: "base" (rápido), "small" (equilíbrio, padrão), "medium" (mais preciso e mais lento).
MODELO_WHISPER = os.getenv("JARVIS_WHISPER_MODELO", "small")
# Palavras que o Whisper deve esperar ouvir (ajuda com nomes próprios).
VOCABULARIO = ("Jarvis, Spotify, WhatsApp, YouTube, Google Chrome, Microsoft Edge, OBS Studio, "
               "Obsidian, Claude, Discord, Steam, Word, Excel, VS Code.")
# Frases que o Whisper às vezes "inventa" em silêncio ou ruído.
ALUCINACOES = ("legendas pela comunidade", "amara.org", "obrigado por assistir", "inscreva-se",
               "legenda adriana", "sous-titres", "subtitles by")

_reconhecedor = sr.Recognizer()
_reconhecedor.dynamic_energy_threshold = True   # se adapta ao barulho do ambiente
_reconhecedor.pause_threshold = 1.1             # silêncio que encerra a frase: pausas curtas não cortam a fala
_reconhecedor.non_speaking_duration = 0.5
_reconhecedor.phrase_threshold = 0.15
_fonte = None
_whisper = None
_whisper_status = "parado"


def _carregar_whisper() -> None:
    global _whisper, _whisper_status
    try:
        from faster_whisper import WhisperModel

        _whisper_status = "carregando"
        # Na primeira vez baixa o modelo (centenas de MB); depois fica guardado no computador.
        _whisper = WhisperModel(MODELO_WHISPER, device=os.getenv("JARVIS_WHISPER_DISPOSITIVO", "cpu"),
                                compute_type="int8")
        _whisper_status = "pronto"
    except Exception as erro:
        print(f"Whisper indisponível ({erro}); usando o reconhecimento do Google.")
        _whisper_status = "erro"


def preparar_reconhecimento() -> None:
    """Começa a carregar o Whisper em segundo plano (enquanto isso, usa o Google)."""
    if RECONHECIMENTO == "whisper" and _whisper_status == "parado":
        threading.Thread(target=_carregar_whisper, daemon=True).start()


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


def _transcrever_whisper(audio: sr.AudioData) -> list[str]:
    import numpy as np

    bruto = np.frombuffer(audio.get_raw_data(convert_rate=16000, convert_width=2), dtype=np.int16)
    segmentos, _ = _whisper.transcribe(
        bruto.astype(np.float32) / 32768.0,
        language="pt",
        beam_size=3,
        vad_filter=True,
        condition_on_previous_text=False,
        initial_prompt=VOCABULARIO,
    )
    partes = [s.text.strip() for s in segmentos if s.no_speech_prob < 0.6 and s.avg_logprob > -1.2]
    texto = " ".join(partes).strip()
    if not texto or any(a in texto.lower() for a in ALUCINACOES):
        return []
    return [texto]


def _transcrever_google(audio: sr.AudioData) -> list[str]:
    try:
        resultado = _reconhecedor.recognize_google(audio, language="pt-BR", show_all=True)
    except (sr.UnknownValueError, sr.RequestError):
        return []
    if not resultado or not isinstance(resultado, dict):
        return []
    return [alt["transcript"] for alt in resultado.get("alternative", []) if alt.get("transcript")]


def ouvir_alternativas(tempo_limite: float | None = None, limite_frase: float = 25) -> list[str]:
    """Escuta o microfone e devolve as interpretações possíveis da frase (a mais provável primeiro)."""
    global _fonte
    if _fonte is None:
        preparar_reconhecimento()
        # O microfone fica aberto o tempo todo: reabrir a cada escuta perdia o começo das frases.
        _fonte = sr.Microphone(sample_rate=16000).__enter__()
        _reconhecedor.adjust_for_ambient_noise(_fonte, duration=1.5)
    try:
        audio = _reconhecedor.listen(_fonte, timeout=tempo_limite, phrase_time_limit=limite_frase)
    except sr.WaitTimeoutError:
        return []
    if _whisper_status == "pronto":
        try:
            return _transcrever_whisper(audio)
        except Exception as erro:
            print(f"Erro no Whisper: {erro}")
    return _transcrever_google(audio)


def ouvir(tempo_limite: float | None = None, limite_frase: float = 25) -> str:
    alternativas = ouvir_alternativas(tempo_limite, limite_frase)
    return alternativas[0] if alternativas else ""


# ---------- Fala ----------

def preparar_para_fala(texto: str) -> str:
    """Tira a pontuação que faz a voz parar no meio da frase (vírgulas, travessões etc.)."""
    texto = re.sub(r"[*_#`]", "", texto)
    # Mantém vírgula e dois-pontos entre dígitos ("5,34", "17:30").
    texto = re.sub(r"\s*(?:,(?!\d)|(?<!\d),|:(?!\d)|[;—–()])\s*", " ", texto)
    return re.sub(r"\s{2,}", " ", texto).strip()


ELEVENLABS_CHAVE = os.getenv("ELEVENLABS_API_KEY", "")
ELEVENLABS_VOZ = os.getenv("ELEVENLABS_VOZ", "")
ELEVENLABS_MODELO = os.getenv("ELEVENLABS_MODELO", "eleven_flash_v2_5")


def _sintetizar_elevenlabs(texto: str) -> bytes:
    import requests

    resposta = requests.post(
        f"https://api.elevenlabs.io/v1/text-to-speech/{ELEVENLABS_VOZ}",
        params={"output_format": "mp3_44100_128"},
        headers={"xi-api-key": ELEVENLABS_CHAVE},
        json={"text": preparar_para_fala(texto), "model_id": ELEVENLABS_MODELO, "language_code": "pt"},
        timeout=20,
    )
    resposta.raise_for_status()
    return resposta.content


def sintetizar(texto: str) -> bytes:
    """Gera o áudio MP3 da fala: ElevenLabs se configurado, senão voz neural da Microsoft (edge-tts)."""
    if ELEVENLABS_CHAVE and ELEVENLABS_VOZ:
        try:
            return _sintetizar_elevenlabs(texto)
        except Exception as erro:
            print(f"ElevenLabs falhou ({erro}); usando a voz da Microsoft.")
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
