@echo off
REM Cria o aplicativo JARVIS.exe e um atalho na Area de Trabalho.
REM Basta dar dois cliques neste arquivo (precisa do Python 3.10+ instalado).
chcp 65001 >nul
cd /d "%~dp0"

echo [1/4] Preparando ambiente Python...
if not exist .venv python -m venv .venv || goto erro
call .venv\Scripts\activate.bat

echo [2/4] Instalando dependencias (pode demorar alguns minutos)...
python -m pip install --upgrade pip >nul
pip install -r requirements.txt pyinstaller || goto erro

echo [3/4] Montando o aplicativo...
pyinstaller --noconfirm --clean --windowed --name JARVIS --icon icone.ico ^
  --add-data "web;web" ^
  --collect-data speech_recognition ^
  --collect-submodules pyttsx3 ^
  --hidden-import edge_tts ^
  app.py || goto erro

if exist .env copy /y .env dist\JARVIS\.env >nul
if not exist dist\JARVIS\.env copy /y .env.example dist\JARVIS\.env >nul
if exist contatos.json copy /y contatos.json dist\JARVIS\contatos.json >nul

echo [4/4] Criando atalho na Area de Trabalho...
powershell -NoProfile -Command ^
  "$s=(New-Object -ComObject WScript.Shell).CreateShortcut([Environment]::GetFolderPath('Desktop')+'\JARVIS.lnk');" ^
  "$s.TargetPath='%~dp0dist\JARVIS\JARVIS.exe'; $s.WorkingDirectory='%~dp0dist\JARVIS';" ^
  "$s.IconLocation='%~dp0icone.ico'; $s.Save()"

echo.
echo Pronto! Abra o JARVIS pelo atalho na Area de Trabalho.
echo Se ainda nao colocou sua chave, edite: %~dp0dist\JARVIS\.env
pause
exit /b 0

:erro
echo.
echo Algo deu errado. Leia a mensagem acima.
pause
exit /b 1
