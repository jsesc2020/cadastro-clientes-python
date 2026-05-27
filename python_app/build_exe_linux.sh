#!/bin/bash
set -euo pipefail
# Build Linux executable with PyInstaller (robust logging for CI)
echo "[build_exe_linux] Starting build on $(uname -a)"

python -m pip install --upgrade pip
python -m pip install -r requirements.txt

echo "[build_exe_linux] Running PyInstaller..."
# Prefer using the spec if present, otherwise run onefile with add-data
if [ -f server/app.spec ]; then
	python -m PyInstaller server/app.spec --clean --noconfirm || true
else
	python -m PyInstaller --onefile --add-data "data:data" --add-data "server/static:server/static" server/app.py || true
fi

echo "[build_exe_linux] PyInstaller finished. Listing dist/ and build/"
ls -la dist || true
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
