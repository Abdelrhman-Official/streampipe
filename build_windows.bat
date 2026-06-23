@echo off
echo ====================================================
echo  StreamPipe - Windows EXE Builder (PyInstaller)
echo ====================================================
echo.

REM Install build deps if needed
pip install pyinstaller customtkinter --quiet

REM Build the EXE
pyinstaller ^
  --onefile ^
  --windowed ^
  --name "StreamPipe" ^
  --icon "assets\icon.ico" ^
  --add-data "streampipe;streampipe" ^
  --add-data "gui;gui" ^
  --hidden-import customtkinter ^
  --hidden-import yt_dlp ^
  --hidden-import rich ^
  --hidden-import yaml ^
  --hidden-import click ^
  gui\windows_app.py

echo.
echo Build complete! Find StreamPipe.exe in the dist\ folder.
pause
