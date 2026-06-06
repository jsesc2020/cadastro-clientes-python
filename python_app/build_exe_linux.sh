#!/bin/bash
set -euo pipefail

echo "[build_exe_linux] Instalando dependencias..."
python -m pip install --upgrade pip
python -m pip install -r requirements.txt

echo "[build_exe_linux] Gerando executavel com PyInstaller..."
python -m PyInstaller --onefile \
    --name app \
    --add-data "server/static:server/static" \
    --hidden-import flask \
    --hidden-import flask.json \
    --hidden-import flask.logging \
    --hidden-import werkzeug \
    --hidden-import werkzeug.security \
    --hidden-import werkzeug.routing \
    --hidden-import werkzeug.exceptions \
    --hidden-import werkzeug.middleware.proxy_fix \
    --hidden-import jwt \
    --hidden-import bcrypt \
    --hidden-import dotenv \
    --hidden-import sqlite3 \
    --hidden-import server \
    --hidden-import server.app \
    --hidden-import server.routes \
    --hidden-import server.routes.clients \
    --hidden-import server.routes.contracts \
    --hidden-import server.routes.pontos \
    --hidden-import server.routes.proprietarios \
    --collect-all flask \
    --collect-all werkzeug \
    --collect-all bcrypt \
    --collect-all jwt \
    main.py

if [ -f dist/app ]; then
    echo "[build_exe_linux] Executavel gerado: dist/app"
else
    echo "[build_exe_linux] ERRO: dist/app nao foi gerado"
    exit 1
fi
