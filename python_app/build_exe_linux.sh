#!/bin/bash
set -euo pipefail
# Build Linux executable with PyInstaller (robust logging for CI)
echo "[build_exe_linux] Starting build on $(uname -a)"

echo "[build_exe_linux] Installing Python dependencies..."
python -m pip install --upgrade pip
python -m pip install -r requirements.txt

echo "[build_exe_linux] Running PyInstaller..."
PYINSTALLER_CMD=(python -m PyInstaller --onefile)
if [ -d server/static ] && [ "$(ls -A server/static)" ]; then
  PYINSTALLER_CMD+=(--add-data "server/static:server/static")
fi
# data/ is created at runtime and must not be included during build
PYINSTALLER_CMD+=(server/app.py)
"${PYINSTALLER_CMD[@]}" || true
ls -la build || true

if [ -f dist/app ] || [ -f dist/app.exe ]; then
	echo "Build complete. Output in dist/"
	exit 0
else
	echo "ERROR: Binário Linux não encontrado em dist/app. Imprimindo logs..."
	# show last pyinstaller log if exists
	if [ -d build ]; then
		find build -maxdepth 2 -type f -name "*.log" -print -exec sed -n '1,200p' {} \; || true
	fi
	echo "---- End of logs ----"
	exit 1
fi
