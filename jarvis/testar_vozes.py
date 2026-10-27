"""Toca a mesma frase com várias vozes para você escolher a mais natural.

Uso: python testar_vozes.py
Depois coloque o nome escolhido em JARVIS_VOZ no arquivo .env.
"""

import os

os.environ.setdefault("JARVIS_TOM_VOZ", "+0Hz")

import voz  # noqa: E402

FRASE = "Boa tarde senhor. Todos os sistemas estão operacionais e o seu café já deveria estar pronto."
VOZES = [
    "pt-BR-AntonioNeural",
    "pt-BR-ThalitaMultilingualNeural",
    "en-US-AndrewMultilingualNeural",
    "en-US-BrianMultilingualNeural",
    "fr-FR-RemyMultilingualNeural",
    "de-DE-FlorianMultilingualNeural",
]

for nome in VOZES:
    print(f"\n>>> {nome}")
    voz.VOZ = nome
    try:
        voz.tocar_mp3(voz.sintetizar(FRASE))
    except Exception as erro:
        print(f"    (não disponível: {erro})")
