@echo off
REM Build Windows executable with PyInstaller
REM Este script e chamado pelo GitHub Actions workflow

echo [build_exe_windows] Instalando PyInstaller...
pip install pyinstaller

echo [build_exe_windows] Gerando executavel...
pyinstaller --onefile ^
    --name app ^
    --noconsole ^
    --add-data "server/static;server/static" ^
    --hidden-import flask ^
    --hidden-import flask.json ^
    --hidden-import flask.logging ^
    --hidden-import werkzeug ^
    --hidden-import werkzeug.security ^
    --hidden-import werkzeug.routing ^
    --hidden-import werkzeug.exceptions ^
    --hidden-import werkzeug.middleware.proxy_fix ^
    --hidden-import jwt ^
    --hidden-import bcrypt ^
    --hidden-import dotenv ^
    --hidden-import sqlite3 ^
    --hidden-import server ^
    --hidden-import server.app ^
    --hidden-import server.routes ^
    --hidden-import server.routes.clients ^
    --hidden-import server.routes.contracts ^
    --hidden-import server.routes.pontos ^
    --hidden-import server.routes.proprietarios ^
    --collect-all flask ^
    --collect-all werkzeug ^
    --collect-all bcrypt ^
    --collect-all jwt ^
    main.py

if exist dist\app.exe (
    echo [build_exe_windows] Executavel gerado com sucesso: dist\app.exe
) else (
    echo [build_exe_windows] ERRO: dist\app.exe nao foi gerado
    exit /b 1
)
