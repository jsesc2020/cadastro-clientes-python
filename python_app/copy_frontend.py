import shutil
import sys
from pathlib import Path

# Copies frontend build from main workspace to python_app server static folder
# Usage: python copy_frontend.py [source_dist_path]

DEFAULT_SOURCE = Path('c:/workspace/dist')
TARGET = Path(__file__).resolve().parent / 'server' / 'static'

def copy_dist(src):
    src = Path(src)
    if not src.exists():
        print(f"Source not found: {src}")
        return 1
    if TARGET.exists():
        shutil.rmtree(TARGET)
    shutil.copytree(src, TARGET)
    print(f"Copied frontend from {src} to {TARGET}")
    return 0

if __name__ == '__main__':
    src = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_SOURCE
    sys.exit(copy_dist(src))
