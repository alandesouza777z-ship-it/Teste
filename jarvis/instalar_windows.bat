@echo off
REM Cria o aplicativo JARVIS.exe, o detector de palmas e os atalhos.
REM Basta dar dois cliques neste arquivo (precisa do Python 3.12 instalado).
chcp 65001 >nul
cd /d "%~dp0"

echo [1/6] Fechando e apagando a versao antiga do JARVIS...
taskkill /IM JARVIS-Palmas.exe /F >nul 2>&1
taskkill /IM JARVIS.exe /F >nul 2>&1
timeout /t 2 /nobreak >nul
if exist dist\JARVIS\.env copy /y dist\JARVIS\.env .env.anterior >nul
if exist dist rmdir /s /q dist
if exist build rmdir /s /q build
if not exist .env if exist .env.anterior copy /y .env.anterior .env >nul

echo [2/6] Preparando ambiente Python...
if not exist .venv python -m venv .venv || goto erro
call .venv\Scripts\activate.bat

echo [3/6] Instalando dependencias (pode demorar alguns minutos)...
python -m pip install --upgrade pip >nul
pip install -r requirements.txt pyinstaller || goto erro

echo [4/6] Baixando o reconhecimento de voz Whisper (so na primeira vez, ~500 MB)...
python -c "from faster_whisper import WhisperModel; WhisperModel('small', device='cpu', compute_type='int8')" || echo Aviso: nao consegui baixar agora; o JARVIS baixa sozinho depois.

echo [5/6] Montando o aplicativo...
pyinstaller --noconfirm --clean --windowed --name JARVIS --icon icone.ico ^
  --add-data "web;web" ^
  --collect-data speech_recognition ^
  --collect-submodules pyttsx3 ^
  --collect-all faster_whisper ^
  --collect-all ctranslate2 ^
  --collect-all playwright ^
  --hidden-import edge_tts ^
  --hidden-import webrtcvad ^
  --additional-hooks-dir hooks ^
  app.py || goto erro
pyinstaller --noconfirm --onefile --windowed --name JARVIS-Palmas --icon icone.ico ^
  --distpath dist\JARVIS --workpath build\palmas --additional-hooks-dir hooks ^
  palmas.py || goto erro

if exist .env copy /y .env dist\JARVIS\.env >nul
if not exist dist\JARVIS\.env copy /y .env.example dist\JARVIS\.env >nul
if exist contatos.json copy /y contatos.json dist\JARVIS\contatos.json >nul

echo [6/6] Criando atalhos e ligando o detector de palmas...
powershell -NoProfile -Command ^
  "$w=New-Object -ComObject WScript.Shell;" ^
  "$s=$w.CreateShortcut([Environment]::GetFolderPath('Desktop')+'\JARVIS.lnk');" ^
  "$s.TargetPath='%~dp0dist\JARVIS\JARVIS.exe'; $s.WorkingDirectory='%~dp0dist\JARVIS'; $s.IconLocation='%~dp0icone.ico'; $s.Save();" ^
  "$p=$w.CreateShortcut([Environment]::GetFolderPath('Startup')+'\JARVIS-Palmas.lnk');" ^
  "$p.TargetPath='%~dp0dist\JARVIS\JARVIS-Palmas.exe'; $p.WorkingDirectory='%~dp0dist\JARVIS'; $p.Save()"
start "" "%~dp0dist\JARVIS\JARVIS-Palmas.exe"

echo.
echo Pronto!
echo  - Abra o JARVIS pelo atalho na Area de Trabalho, ou bata palmas duas vezes.
echo  - O detector de palmas inicia sozinho junto com o Windows.
echo Se ainda nao colocou sua chave, edite: %~dp0dist\JARVIS\.env
pause
exit /b 0

:erro
echo.
echo Algo deu errado. Leia a mensagem acima.
pause
exit /b 1
