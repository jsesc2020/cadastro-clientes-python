# Ponto de entrada para o PyInstaller
# Evita problemas com importacoes relativas ao empacotar com --onefile

import sys
import os

# Garante que o diretorio do executavel esteja no path
if getattr(sys, 'frozen', False):
    # Rodando como executavel PyInstaller
    base_dir = sys._MEIPASS
    sys.path.insert(0, base_dir)

# Muda o diretorio de trabalho para junto do executavel
# (importante para que os caminhos de data/ e static/ funcionem)
if getattr(sys, 'frozen', False):
    os.chdir(os.path.dirname(sys.executable))

from server.app import app, init_db
import webbrowser
import threading

PORT = int(os.environ.get('PORT', 5000))

def open_browser():
    import time
    time.sleep(1.5)
    webbrowser.open(f'http://localhost:{PORT}')

if __name__ == '__main__':
    init_db()
    threading.Thread(target=open_browser, daemon=True).start()
    app.run(host='127.0.0.1', port=PORT, debug=False, use_reloader=False)
