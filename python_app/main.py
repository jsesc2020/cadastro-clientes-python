import sys
import os
import threading
import time
import signal
from pathlib import Path

# ── Oculta janela CMD imediatamente (Windows) ─────────────────
# Deve ser a primeira coisa a executar, antes de qualquer import
if sys.platform == 'win32':
    try:
        import ctypes
        hwnd = ctypes.windll.kernel32.GetConsoleWindow()
        if hwnd:
            ctypes.windll.user32.ShowWindow(hwnd, 0)  # SW_HIDE
    except Exception:
        pass

# ── Corrige diretório de trabalho ─────────────────────────────
if getattr(sys, 'frozen', False):
    os.chdir(Path(sys.executable).parent)

from server.app import app, init_db
import webbrowser

PORT = int(os.environ.get('PORT', 5000))

# ── Watchdog: encerra quando navegador fecha ───────────────────
_last_ping = [time.time()]
_GRACE     = 60   # segundos iniciais antes de monitorar
_TIMEOUT   = 30   # segundos sem ping = navegador fechado

@app.route('/api/ping', methods=['GET', 'POST'])
def ping():
    _last_ping[0] = time.time()
    return ('', 204)

def _watchdog():
    time.sleep(_GRACE)
    while True:
        time.sleep(5)
        if time.time() - _last_ping[0] > _TIMEOUT:
            os.kill(os.getpid(), signal.SIGTERM)
            return

def _open_browser():
    time.sleep(1.5)
    webbrowser.open(f'http://localhost:{PORT}/?boot=1')

if __name__ == '__main__':
    init_db()
    threading.Thread(target=_open_browser, daemon=True).start()
    threading.Thread(target=_watchdog,     daemon=False).start()
    app.run(host='127.0.0.1', port=PORT, debug=False, use_reloader=False)
