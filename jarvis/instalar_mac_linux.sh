#!/usr/bin/env bash
# Cria o aplicativo JARVIS (pasta dist/JARVIS). Uso: bash instalar_mac_linux.sh
set -euo pipefail
cd "$(dirname "$0")"

[ -d .venv ] || python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip >/dev/null
pip install -r requirements.txt pyinstaller

pyinstaller --noconfirm --clean --windowed --name JARVIS --icon icone.ico \
  --add-data "web:web" \
  --collect-data speech_recognition \
  --collect-submodules pyttsx3 \
  --hidden-import edge_tts \
  --hidden-import webrtcvad --additional-hooks-dir hooks \
  app.py

# No macOS o PyInstaller gera dist/JARVIS.app; no Linux, dist/JARVIS/JARVIS.
if [ -d dist/JARVIS.app ]; then destino=dist/JARVIS.app/Contents/MacOS; else destino=dist/JARVIS; fi
cp -n .env "$destino/.env" 2>/dev/null || cp -n .env.example "$destino/.env"
[ -f contatos.json ] && cp contatos.json "$destino/" || true

echo "Pronto! Aplicativo em: $(pwd)/dist  (a chave da API fica em $destino/.env)"
