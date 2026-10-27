"""Laço do assistente: palavra de ativação, conversa e confirmações.

Usado tanto pelo terminal (main.py) quanto pelo aplicativo com interface (app.py).
Tudo roda numa única thread: pedidos digitados na interface entram pela fila e
são atendidos entre uma escuta e outra do microfone.
"""

import os
import queue
import time

from cerebro import NOME_USUARIO, Cerebro
from ferramentas import confirmacao

PALAVRA_ATIVACAO = os.getenv("JARVIS_PALAVRA_ATIVACAO", "jarvis").lower()
DESPEDIDAS = ("desligar jarvis", "jarvis desligar", "até logo jarvis", "encerrar jarvis")
JANELA_CONVERSA = 6  # segundos esperando continuação sem precisar dizer "Jarvis" de novo
TEMPO_CONFIRMACAO = 12


def _nada(*_):
    pass


def saudacao() -> str:
    import datetime

    hora = datetime.datetime.now().hour
    periodo = "Bom dia" if hora < 12 else "Boa tarde" if hora < 18 else "Boa noite"
    return f"{periodo}, {NOME_USUARIO}. Todos os sistemas operacionais. Em que posso ajudar?"


class Assistente:
    def __init__(self, falar, ao_estado=_nada, ao_mensagem=_nada, ao_confirmar=_nada, ao_encerrar=_nada):
        """
        falar(texto): fala em voz alta e só retorna quando terminar.
        ao_estado(estado): "ocioso", "ouvindo", "pensando" ou "falando".
        ao_mensagem(quem, texto): quem é "voce" ou "jarvis".
        ao_confirmar(pergunta): a interface pode mostrar botões sim/não (resposta vem por enviar()).
        """
        self.cerebro = Cerebro()
        self.falar = falar
        self.ao_estado = ao_estado
        self.ao_mensagem = ao_mensagem
        self.ao_confirmar = ao_confirmar
        self.ao_encerrar = ao_encerrar
        self.fila: queue.Queue[str] = queue.Queue()
        self.microfone = True
        confirmacao.perguntar = self._perguntar

    def enviar(self, texto: str) -> None:
        """Pedido digitado (ou resposta de confirmação) vindo da interface."""
        self.fila.put(texto)

    def _ouvir(self, tempo_limite, limite_frase=15) -> str:
        if not self.microfone:
            return ""
        try:
            import voz

            return voz.ouvir(tempo_limite=tempo_limite, limite_frase=limite_frase)
        except Exception as erro:
            self.microfone = False
            self.ao_mensagem("jarvis", f"Microfone indisponível ({erro}). Digite seus pedidos.")
            return ""

    def _dizer(self, texto: str) -> None:
        self.ao_mensagem("jarvis", texto)
        self.ao_estado("falando")
        self.falar(texto)
        self.ao_estado("pensando")

    def _perguntar(self, pergunta: str) -> str:
        self._dizer(pergunta)
        self.ao_confirmar(pergunta)
        self.ao_estado("ouvindo")
        prazo = time.time() + TEMPO_CONFIRMACAO
        while time.time() < prazo:
            try:
                resposta = self.fila.get_nowait()
            except queue.Empty:
                resposta = self._ouvir(tempo_limite=2, limite_frase=5) if self.microfone else ""
                if not resposta and not self.microfone:
                    time.sleep(0.2)
            if resposta:
                self.ao_mensagem("voce", resposta)
                self.ao_estado("pensando")
                return resposta
        self.ao_estado("pensando")
        return ""

    def _processar(self, pedido: str) -> None:
        self.ao_estado("pensando")
        self.cerebro.responder(pedido, self._dizer)
        self.ao_estado("ocioso")

    def rodar(self) -> None:
        self._dizer(saudacao())
        self.ao_estado("ocioso")
        conversa_ate = 0.0
        while True:
            em_conversa = time.time() < conversa_ate
            try:
                digitado = self.fila.get_nowait()
            except queue.Empty:
                digitado = ""

            if digitado:
                frase = digitado
                self.ao_mensagem("voce", frase)
            else:
                if not self.microfone:
                    time.sleep(0.2)
                    continue
                self.ao_estado("ouvindo" if em_conversa else "ocioso")
                frase = self._ouvir(tempo_limite=2)
                if not frase:
                    if em_conversa and time.time() >= conversa_ate:
                        self.ao_estado("ocioso")
                    continue
                print(f"Você: {frase}")

            minuscula = frase.lower()
            if any(d in minuscula for d in DESPEDIDAS):
                self._dizer(f"Desligando. Até logo, {NOME_USUARIO}.")
                self.ao_encerrar()
                return

            if digitado or em_conversa:
                pedido = frase
            elif PALAVRA_ATIVACAO in minuscula:
                pedido = minuscula.split(PALAVRA_ATIVACAO, 1)[1].strip(" ,.!?")
                self.ao_mensagem("voce", frase)
                if not pedido:
                    self._dizer(f"Pois não, {NOME_USUARIO}?")
                    self.ao_estado("ouvindo")
                    pedido = self._ouvir(tempo_limite=8)
                    if pedido:
                        self.ao_mensagem("voce", pedido)
            else:
                continue

            if pedido:
                if not digitado and em_conversa:
                    self.ao_mensagem("voce", pedido)
                self._processar(pedido)
                conversa_ate = time.time() + JANELA_CONVERSA
