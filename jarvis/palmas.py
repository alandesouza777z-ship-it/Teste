"""Detector de palmas: bata palmas duas vezes para abrir o JARVIS.

Roda escondido em segundo plano (o instalador o coloca para iniciar com o Windows).
Enquanto o JARVIS está aberto, o detector solta o microfone e não reage a palmas.

Uso:
    python palmas.py          # roda o detector
    python palmas.py --teste  # mostra o nível do som, para ajustar a sensibilidade
"""

import math
import os
import subprocess
import sys
import time
from array import array

import config
import psutil

TAXA = 44100
BLOCO = 1024                      # ~23 ms por bloco
SENSIBILIDADE = float(os.getenv("JARVIS_PALMAS_SENSIBILIDADE", "1.0"))  # maior = mais sensível
NIVEL_MINIMO = 1100 / SENSIBILIDADE   # pico mínimo (de 32767) para contar como palma
SALTO_MINIMO = 3.5 / SENSIBILIDADE    # quantas vezes acima do barulho de fundo
INTERVALO_PALMAS = (0.1, 0.9)   # segundos entre a 1ª e a 2ª palma
ESPERA_APOS_ABRIR = 4.0

ARQUIVO_PID = os.path.join(config.PASTA_USUARIO, ".jarvis.pid")

# Música que começa a tocar junto com o JARVIS (deixe JARVIS_PALMAS_MUSICA vazio para desligar).
MUSICA = os.getenv("JARVIS_PALMAS_MUSICA", "spotify:track:08mG3Y1vljYA6bvDt4Wqkj")  # AC/DC - Back In Black
MUSICA_NOME = os.getenv("JARVIS_PALMAS_MUSICA_NOME", "Back In Black")


def jarvis_aberto() -> bool:
    try:
        with open(ARQUIVO_PID) as arquivo:
            pid = int(arquivo.read().strip())
        if psutil.pid_exists(pid):
            nome = psutil.Process(pid).name().lower()
            if "jarvis" in nome or "python" in nome:
                return True
    except (OSError, ValueError, psutil.Error):
        pass
    return any((p.info["name"] or "").lower() == "jarvis.exe" for p in psutil.process_iter(["name"]))


def abrir_jarvis() -> None:
    pasta = os.path.dirname(sys.executable) if config.EMPACOTADO else config.PASTA_PROGRAMA
    exe = os.path.join(pasta, "JARVIS.exe")
    if os.path.exists(exe):
        subprocess.Popen([exe], cwd=pasta)
    else:
        subprocess.Popen([sys.executable, os.path.join(config.PASTA_PROGRAMA, "app.py")], cwd=config.PASTA_PROGRAMA)


def trazer_jarvis_para_frente() -> None:
    try:
        import pygetwindow

        for _ in range(30):
            janelas = pygetwindow.getWindowsWithTitle("J.A.R.V.I.S.")
            if janelas:
                janelas[0].activate()
                return
            time.sleep(0.5)
    except Exception:
        pass


def ao_bater_palmas() -> None:
    """Abre o JARVIS e, ao mesmo tempo, coloca a música para tocar no Spotify."""
    abrir_jarvis()
    if not MUSICA:
        return
    try:
        from ferramentas import spotify

        tocando = spotify.tocar_no_aplicativo(MUSICA, MUSICA_NOME)
        print("Música tocando." if tocando else "Não consegui dar play na música.")
    except Exception as erro:
        print(f"Erro ao tocar a música: {erro}")
    trazer_jarvis_para_frente()


class Detector:
    """Reconhece palmas: som curto, muito acima do fundo, que some rápido (fala e música não somem)."""

    def __init__(self):
        self.fundo = 300.0
        self.candidata = None      # (instante, blocos desde o início)
        self.ultima_palma = 0.0
        self.anterior = 0.0

    def processar(self, dados: bytes, agora: float) -> bool:
        amostras = array("h", dados)
        pico = max(abs(min(amostras)), abs(max(amostras)))
        rms = math.sqrt(sum(a * a for a in amostras) / len(amostras))

        palma_dupla = False
        if self.candidata is not None:
            inicio, pico_palma, blocos = self.candidata
            blocos += 1
            if blocos <= 2 and rms > pico_palma:  # ainda subindo (a palma caiu no meio do bloco)
                pico_palma = rms
            if rms < pico_palma * 0.35:          # sumiu rápido: é palma
                self.candidata = None
                if INTERVALO_PALMAS[0] <= inicio - self.ultima_palma <= INTERVALO_PALMAS[1]:
                    palma_dupla = True
                    self.ultima_palma = 0.0
                else:
                    self.ultima_palma = inicio
            elif blocos > 8:                      # som longo (fala, música, batida na mesa arrastada)
                self.candidata = None
            else:
                self.candidata = (inicio, pico_palma, blocos)
        # Palma: pico seco (bem acima da média do bloco), alto e muito acima do barulho de fundo.
        elif (pico > NIVEL_MINIMO and pico > rms * 3.0 and rms > self.fundo * SALTO_MINIMO
              and rms > self.anterior * 2):
            self.candidata = (agora, rms, 0)

        if self.candidata is None:
            self.fundo = self.fundo * 0.97 + min(rms, self.fundo * 3) * 0.03
        self.anterior = rms
        return palma_dupla


def ouvir_palmas(teste: bool = False) -> None:
    import pyaudio

    audio = pyaudio.PyAudio()
    detector = Detector()
    stream = None
    print("Detector de palmas ativo. Bata palmas duas vezes para abrir o JARVIS.")
    ultima_checagem = 0.0
    while True:
        agora = time.time()
        # Verifica de vez em quando se o JARVIS está aberto (enquanto estiver, solta o microfone).
        if not teste and agora - ultima_checagem > 2:
            ultima_checagem = agora
            if jarvis_aberto():
                if stream:
                    stream.stop_stream()
                    stream.close()
                    stream = None
                time.sleep(2)
                continue
        if stream is None:
            stream = audio.open(format=pyaudio.paInt16, channels=1, rate=TAXA, input=True, frames_per_buffer=BLOCO)
            detector = Detector()
        dados = stream.read(BLOCO, exception_on_overflow=False)
        agora = time.time()
        if teste:
            amostras = array("h", dados)
            pico = max(abs(min(amostras)), abs(max(amostras)))
            print(f"pico {pico:6d}  fundo {detector.fundo:7.0f}  " + "#" * min(60, pico // 500))
        if detector.processar(dados, agora):
            print("Palmas detectadas!")
            if teste:
                continue
            stream.stop_stream()
            stream.close()
            stream = None
            ao_bater_palmas()
            time.sleep(ESPERA_APOS_ABRIR)
            ultima_checagem = 0.0

if __name__ == "__main__":
    ouvir_palmas(teste="--teste" in sys.argv)
