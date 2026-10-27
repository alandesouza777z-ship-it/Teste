"""Caminhos do JARVIS, iguais rodando pelo Python ou pelo JARVIS.exe empacotado."""

import os
import sys

from dotenv import load_dotenv

EMPACOTADO = getattr(sys, "frozen", False)

# Arquivos do programa (interface web etc.). No .exe ficam numa pasta temporária.
PASTA_PROGRAMA = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))

# Arquivos do usuário (.env, contatos.json): ao lado do JARVIS.exe ou desta pasta.
PASTA_USUARIO = os.path.dirname(sys.executable) if EMPACOTADO else os.path.dirname(os.path.abspath(__file__))

# utf-8-sig: aceita o .env salvo pelo Bloco de Notas com BOM.
load_dotenv(os.path.join(PASTA_USUARIO, ".env"), encoding="utf-8-sig")
