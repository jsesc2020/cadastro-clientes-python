# Packaging e Instaladores

Este diretório contém scripts e templates para gerar instaladores Windows (EXE/MSI) e pacotes Debian (DEB) para o app local.

## Dependências

- Python 3.10+ e `pip`
- `pyinstaller` para gerar executáveis
- `makensis` para criar instalador NSIS (Windows)
- WiX Toolset (`candle`, `light`) para criar MSI (Windows)
- `dpkg-deb` e `fakeroot` para criar pacote DEB (Linux)

## Instalação rápida

```powershell
cd python_app
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

## 1. Gerar build do app

Use o PyInstaller para criar o binário:

```powershell
pyinstaller --onefile --add-data "data;data" --add-data "server/static;server/static" server/app.py
```

No Linux:

```bash
pyinstaller --onefile --add-data "data:data" --add-data "server/static:server/static" server/app.py
```

## 2. Instalador NSIS (Windows)

```powershell
.\create_installer.bat
```

ou se preferir:

```powershell
.
installer\build_windows_installer.ps1
```

## 3. MSI com WiX (Windows)

```powershell
.
installer\build_msi.ps1
```

Isso usa o template `installer/wix_sample.wxs` e gera um MSI em `dist/`.

## 4. DEB para Linux

```bash
./installer/build_deb.sh
```

O script gera um pacote `.deb` em `python_app/dist/` usando o binário Linux criado pelo PyInstaller.

## Observações

- O pacote DEB é um wrapper em torno do binário PyInstaller e inclui a pasta `data/`.
- Se usar frontend estático, copie `C:\workspace\dist` para `python_app/server/static/` antes de empacotar.
- Os scripts são exemplos e devem ser ajustados ao fluxo de distribuição do seu ambiente.

## GitHub Actions

O repositório também inclui um workflow em `.github/workflows/package.yml` que:
- gera o EXE Windows com PyInstaller
- cria o instalador NSIS e o MSI Windows
- gera o pacote DEB Linux
- executa os testes Python
- publica os artefatos de build
