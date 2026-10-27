@echo off
REM Desliga o detector de palmas e tira ele da inicializacao do Windows.
taskkill /IM JARVIS-Palmas.exe /F >nul 2>&1
del "%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup\JARVIS-Palmas.lnk" >nul 2>&1
echo Detector de palmas desligado. Para ligar de novo, rode instalar_windows.bat.
pause
