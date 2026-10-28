"""Laço do assistente: escuta contínua (ou palavra de ativação), conversa e confirmações.

Usado tanto pelo terminal (main.py) quanto pelo aplicativo com interface (app.py).
A escuta roda numa única thread: pedidos digitados na interface entram pela fila e
são atendidos entre uma escuta e outra do microfone. A fala roda em paralelo
(voz.Locutor), para o JARVIS começar a falar antes de terminar de pensar.
"""

import os
import queue
import re
import threading
import time

import voz
from atalhos import executar_atalho
from cerebro import MODOS, NOME_USUARIO, Cerebro
from ferramentas import confirmacao, navegador, spotify

DESPEDIDAS = ("desligar", "desliga", "encerrar", "encerra", "ate logo", "tchau jarvis", "desligar jarvis")
# "continua": ouve tudo o que você fala; "palavra": só depois de "Jarvis".
ESCUTA_CONTINUA = os.getenv("JARVIS_ESCUTA", "continua").lower() != "palavra"
FALAS_SOLTAS = {"obrigado", "obrigada", "hum", "hmm", "ah", "e", "eh", "ok", "tchau", "sim", "nao", "uhum", "ai"}
PADROES_MODO = {
    "curta": r"\b(curt[ao]s?|rapid[ao]s?|resumid[ao]s?)\b",
    "moderada": r"\b(moderad[ao]s?|medi[ao]s?|normal|normais)\b",
    "longa": r"\b(long[ao]s?|detalhad[ao]s?|complet[ao]s?)\b",
}
JANELA_CONVERSA = 8  # segundos esperando continuação sem precisar dizer "Jarvis" de novo
TEMPO_CONFIRMACAO = 12


def _nada(*_):
    pass


def saudacao() -> str:
    import datetime

    hora = datetime.datetime.now().hour
    periodo = "Bom dia" if hora < 12 else "Boa tarde" if hora < 18 else "Boa noite"
    return f"{periodo}, {NOME_USUARIO}. Todos os sistemas operacionais. Em que posso ajudar?"


class Assistente:
    def __init__(self, tocar_audio=voz.tocar_mp3, tocar_offline=voz.falar_offline,
                 ao_estado=_nada, ao_mensagem=_nada, ao_confirmar=_nada, ao_encerrar=_nada,
                 ao_modo=_nada, ao_mudo=_nada, ao_tempos=print, veio_das_palmas=False):
        """
        tocar_audio(mp3): toca o áudio e só retorna quando terminar.
        tocar_offline(texto): fala sem internet (voz do sistema).
        ao_estado(estado): "ocioso", "ouvindo", "pensando" ou "falando".
        ao_mensagem(quem, texto): quem é "voce", "jarvis" (nova resposta) ou "jarvis+" (continuação).
        ao_confirmar(pergunta): a interface pode mostrar botões sim/não (resposta vem por enviar()).
        ao_modo(modo) / ao_mudo(bool): avisam a interface quando o modo de resposta ou o microfone mudam.
        """
        self.cerebro = Cerebro()
        self._ao_estado = ao_estado
        self._estado = None
        self.ao_mensagem = ao_mensagem
        self.ao_confirmar = ao_confirmar
        self.ao_encerrar = ao_encerrar
        self.ao_modo = ao_modo
        self.ao_mudo = ao_mudo
        self.ao_tempos = ao_tempos
        self._t_pedido = None
        self._t_transcricao = 0.0
        # Assim que você termina de falar, a esfera já mostra "processando" (antes mesmo de transcrever).
        voz.ao_fim_da_fala = lambda: self.ao_estado("pensando")
        voz.preparar_reconhecimento()  # o Whisper já começa a carregar enquanto ele dá bom dia
        self.veio_das_palmas = veio_das_palmas
        self.escuta_continua = ESCUTA_CONTINUA
        self.mudo = False
        self.fila: queue.Queue[str] = queue.Queue()
        self.microfone = True
        self.ocupado = False
        self._nova_resposta = True
        self.locutor = voz.Locutor(tocar_audio, tocar_offline,
                                   ao_iniciar=self._ao_comecar_frase, ao_terminar=self._ao_calar)
        confirmacao.perguntar = self._perguntar

    def ao_estado(self, estado: str) -> None:
        if estado != self._estado:  # só avisa a interface quando muda
            self._estado = estado
            self._ao_estado(estado)

    def enviar(self, texto: str) -> None:
        """Pedido digitado (ou resposta de confirmação) vindo da interface."""
        self.fila.put(texto)

    # ---------- Fala ----------

    def _ao_comecar_frase(self, texto: str) -> None:
        if self._t_pedido is not None:
            # Cronômetro: quanto tempo do fim da sua fala até ele começar a responder.
            resposta = time.time() - self._t_pedido
            self.ao_tempos(f"entender {self._t_transcricao:.1f}s · responder {resposta:.1f}s")
            self._t_pedido = None
        print(f"JARVIS: {texto}")
        self.ao_mensagem("jarvis" if self._nova_resposta else "jarvis+", texto)
        self._nova_resposta = False
        self.ao_estado("falando")

    def _ao_calar(self) -> None:
        if self.ocupado:
            self.ao_estado("pensando")

    def _dizer(self, texto: str) -> None:
        self.locutor.dizer(texto)

    def _dizer_e_esperar(self, texto: str) -> None:
        self._nova_resposta = True
        self.locutor.dizer(texto)
        self.locutor.esperar()

    # ---------- Escuta ----------

    def _ouvir(self, tempo_limite, limite_frase=25) -> list[str]:
        if not self.microfone:
            return []
        try:
            return voz.ouvir_alternativas(tempo_limite=tempo_limite, limite_frase=limite_frase)
        except Exception as erro:
            self.microfone = False
            self.ao_mensagem("jarvis", f"Microfone indisponível ({erro}). Digite seus pedidos.")
            return []

    def _perguntar(self, pergunta: str) -> str:
        self._dizer_e_esperar(pergunta)
        self.ao_confirmar(pergunta)
        self.ao_estado("ouvindo")
        prazo = time.time() + TEMPO_CONFIRMACAO
        while time.time() < prazo:
            try:
                resposta = self.fila.get_nowait()
            except queue.Empty:
                alternativas = self._ouvir(tempo_limite=2, limite_frase=8)
                resposta = alternativas[0] if alternativas else ""
                if not self.microfone:
                    time.sleep(0.2)
            if resposta:
                self.ao_mensagem("voce", resposta)
                self.ao_estado("pensando")
                self._nova_resposta = True
                return resposta
        self.ao_estado("pensando")
        return ""

    # ---------- Laço principal ----------

    def _processar(self, pedido: str) -> None:
        self.ocupado = True
        self._nova_resposta = True
        self.ao_estado("pensando")
        try:
            self.cerebro.responder(pedido, self._dizer)
            self.locutor.esperar()
        finally:
            self.ocupado = False
            self.ao_estado("mudo" if self.mudo else "ocioso")

    # ---------- Comandos rápidos (sem passar pelo Claude) ----------

    def definir_modo(self, modo: str) -> None:
        if modo in MODOS:
            self.cerebro.modo = modo
            self.ao_modo(modo)

    def definir_mudo(self, mudo: bool) -> None:
        self.mudo = mudo
        self.ao_mudo(mudo)
        self.ao_estado("mudo" if mudo else "ocioso")

    def _comando_rapido(self, pedido: str) -> bool:
        texto = voz._sem_acento(pedido)
        for modo, padrao in PADROES_MODO.items():
            curto = len(texto.split()) <= 7  # "modo curto", "quero respostas longas"...
            if curto and re.search(padrao, texto) and re.search(r"\b(modo|respost)", texto):
                self.definir_modo(modo)
                self._dizer_e_esperar(f"Modo de respostas {modo} ativado, {NOME_USUARIO}.")
                return True
        if re.search(r"(pare|para|parar) de (me )?(ouvir|escutar)|desliga(r)? o microfone", texto):
            self._dizer_e_esperar(f"Microfone desligado, {NOME_USUARIO}. Clique no microfone para me chamar.")
            self.definir_mudo(True)
            return True
        return False

    # ---------- Laço principal ----------

    def _entender(self, alternativas: list[str], em_conversa: bool) -> str | None:
        """Devolve o pedido contido na fala, "" se só chamaram "Jarvis", ou None se não era com ele."""
        for frase in alternativas:
            pedido = voz.separar_ativacao(frase)
            if pedido is not None:
                return pedido
        frase = alternativas[0].strip()
        if em_conversa:
            return frase
        if not self.escuta_continua:
            return None
        # Com música tocando, o microfone ouve as letras: aí só atende quem chama "Jarvis".
        if spotify.spotify_tocando():
            return None
        # Ruídos que o reconhecimento transforma em palavras soltas ("Obrigado.", "Hum").
        if len(frase) < 4 or voz._sem_acento(frase).strip(" .!?") in FALAS_SOLTAS:
            return None
        return frase

    def _avisar_whatsapp(self) -> None:
        """Depois das palmas: espera o WhatsApp Web carregar e diz quantas conversas não lidas há."""
        quantidade = navegador.contar_nao_lidas(espera_maxima=25)
        if quantidade is None:
            aviso = f"Não consegui abrir o WhatsApp Web, {NOME_USUARIO}."
        elif quantidade == 0:
            aviso = f"Nenhuma mensagem não lida no WhatsApp da empresa, {NOME_USUARIO}."
        elif quantidade == 1:
            aviso = f"Você tem uma conversa com mensagens não lidas no WhatsApp da empresa, {NOME_USUARIO}."
        else:
            aviso = f"Você tem {quantidade} conversas com mensagens não lidas no WhatsApp da empresa, {NOME_USUARIO}."
        self._nova_resposta = True
        self.locutor.dizer(aviso)

    def rodar(self) -> None:
        if self.veio_das_palmas:
            self._dizer_e_esperar(f"Bem-vindo de volta, {NOME_USUARIO}. Abrindo seus sistemas.")
            threading.Thread(target=self._avisar_whatsapp, daemon=True).start()
        else:
            self._dizer_e_esperar(saudacao())
        self.ao_estado("ocioso")
        conversa_ate = 0.0
        while True:
            em_conversa = time.time() < conversa_ate
            try:
                digitado = self.fila.get_nowait()
            except queue.Empty:
                digitado = ""

            if digitado:
                pedido = voz.separar_ativacao(digitado) or digitado
                self.ao_mensagem("voce", digitado)
            else:
                if not self.microfone or self.mudo:
                    time.sleep(0.2)
                    continue
                self.ao_estado("ouvindo" if (em_conversa or self.escuta_continua) else "ocioso")
                alternativas = self._ouvir(tempo_limite=2)
                if not alternativas or self.mudo:
                    continue
                print(f"Você: {alternativas[0]}")
                pedido = self._entender(alternativas, em_conversa)
                if pedido is None:
                    continue
                self.ao_mensagem("voce", alternativas[0])
                if not pedido:
                    self._dizer_e_esperar(f"Pois não, {NOME_USUARIO}?")
                    self.ao_estado("ouvindo")
                    alternativas = self._ouvir(tempo_limite=8)
                    if not alternativas:
                        self.ao_estado("ocioso")
                        continue
                    pedido = alternativas[0]
                    self.ao_mensagem("voce", pedido)

            if voz._sem_acento(pedido).strip(" .!") in DESPEDIDAS:
                self._dizer_e_esperar(f"Desligando. Até logo, {NOME_USUARIO}.")
                self.ao_encerrar()
                return
            self._t_pedido = time.time()
            self._t_transcricao = 0.0 if digitado else voz.ultimo_tempo_transcricao
            if self._comando_rapido(pedido):
                continue
            # Pedidos simples (abrir app, música, volume, hora) são feitos na hora, sem esperar o Claude.
            try:
                confirmacao_rapida = executar_atalho(pedido)
            except Exception as erro:
                print(f"Atalho falhou: {erro}")
                confirmacao_rapida = None
            if confirmacao_rapida:
                self._dizer_e_esperar(confirmacao_rapida)
                self.ao_estado("mudo" if self.mudo else "ocioso")
                conversa_ate = time.time() + JANELA_CONVERSA
                continue

            self._processar(pedido)
            conversa_ate = time.time() + JANELA_CONVERSA
