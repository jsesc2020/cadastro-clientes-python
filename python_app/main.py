import sys
import os
import threading
import time
import signal
from pathlib import Path

# ── Oculta janela do CMD no Windows ───────────────────────────
if sys.platform == 'win32':
    import ctypes
    # SW_HIDE = 0: oculta a janela do console completamente
    ctypes.windll.user32.ShowWindow(ctypes.windll.kernel32.GetConsoleWindow(), 0)

# ── Corrige diretorio de trabalho ─────────────────────────────
if getattr(sys, 'frozen', False):
    os.chdir(Path(sys.executable).parent)

from server.app import app, init_db
import webbrowser

PORT = int(os.environ.get('PORT', 5000))

# ── Detecta encerramento do navegador ─────────────────────────
# Monitora o endpoint /api/ping: se o navegador parar de chamar
# por mais de 30 segundos, encerra o processo inteiro
_last_ping = time.time()
_TIMEOUT = 30  # segundos sem ping = navegador fechado

@app.route('/api/ping', methods=['GET'])
def ping():
    global _last_ping
    _last_ping = time.time()
    return ('', 204)

def _watchdog():
    """Thread que encerra o app quando o navegador fecha."""
    global _last_ping
    # Aguarda o navegador conectar pela primeira vez (60s de graca)
    time.sleep(60)
    while True:
        time.sleep(5)
        if time.time() - _last_ping > _TIMEOUT:
            # Navegador fechado: encerra o processo
            os.kill(os.getpid(), signal.SIGTERM)
            break

def _open_browser():
    time.sleep(1.5)
    webbrowser.open(f'http://localhost:{PORT}/?boot=1')

if __name__ == '__main__':
    init_db()

    # Injeta o script de ping no frontend via middleware seria complexo,
    # então o ping é chamado pelo frontend via JS (ver index.html)
    threading.Thread(target=_open_browser, daemon=True).start()
    threading.Thread(target=_watchdog,     daemon=False).start()

    app.run(
        host='127.0.0.1',
        port=PORT,
        debug=False,
        use_reloader=False
    )
