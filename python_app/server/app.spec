# PyInstaller spec for building single-file app
# Adjust paths if necessary

from PyInstaller.utils.hooks import collect_data_files
from PyInstaller.building.datastruct import Tree
import os

block_cipher = None

datas = [
    Tree('data', prefix='data'),
    Tree(os.path.join('server', 'static'), prefix=os.path.join('server', 'static')),
]

a = Analysis(['server/app.py'],
             pathex=['.'],
             binaries=[],
             datas=datas,
             hiddenimports=[],
             hookspath=[],
             runtime_hooks=[],
             excludes=[],
             win_no_prefer_redirects=False,
             win_private_assemblies=False,
             cipher=block_cipher)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(pyz,
          a.scripts,
          [],
          exclude_binaries=True,
          name='app',
          debug=False,
          bootloader_ignore_signals=False,
          strip=False,
          upx=False,
          console=False)

coll = COLLECT(exe,
               a.binaries,
               a.zipfiles,
               a.datas,
               strip=False,
               upx=False,
               name='app')
