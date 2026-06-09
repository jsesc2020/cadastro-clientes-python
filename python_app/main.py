import sys
import os
from pathlib import Path

if getattr(sys, 'frozen', False):
    os.chdir(Path(sys.executable).parent)

from server.app import app, init_db
import webbrowser
import threading

PORT = int(os.environ.get('PORT', 5000))

def open_browser():
    import time
    time.sleep(1.5)
    # Abre com parametro ?boot=1 para que o frontend limpe sessao ao iniciar
    webbrowser.open(f'http://localhost:{PORT}/?boot=1')

if __name__ == '__main__':
    init_db()
    threading.Thread(target=open_browser, daemon=True).start()
    app.run(host='127.0.0.1', port=PORT, debug=False, use_reloader=False)
