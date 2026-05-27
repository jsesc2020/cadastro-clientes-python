#!/bin/bash
# Build Linux executable with PyInstaller
pip install pyinstaller
pyinstaller --onefile --add-data "data:data" server/app.py
echo "Build complete. Output in dist/app"
