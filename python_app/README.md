# Cadastro de Clientes - Versão Local (Python)

Esta é uma versão standalone do sistema para execução local em Windows/Linux.
Usa Flask (API) e SQLite (banco de dados local) e pode ser empacotada com `PyInstaller`.

## Requisitos
- Python 3.10+
- pip

## Instalação rápida
```bash
cd workspace2/python_app
python -m venv .venv
.venv\Scripts\activate    # Windows
# or
source .venv/bin/activate # Linux/macOS
pip install -r requirements.txt
```

## Inicializar banco de dados e criar admin
```bash
python -c "from server.app import init_db; init_db()"
python server/create_admin.py admin@local.test S3nh@Adm1n
```

## Executar localmente
```bash
export JWT_SECRET=suachavesecreta
python server/app.py
# A API estará em http://localhost:5000
```

## Endpoints principais
- `POST /api/auth/register` - cria admin (email, password)
- `POST /api/auth/login` - retorna JWT (email, password)
- `GET /api/collaborators` - lista colaboradores (Bearer token)
- `POST /api/collaborators` - adicionar colaborador (Bearer token)
- `PUT /api/collaborators/:id/active` - alternar ativo (Bearer token)
 - `GET /api/clients/` - lista clientes (Bearer token)
 - `POST /api/clients/` - criar cliente (Bearer token)
 - `GET /api/contracts/` - lista contratos (Bearer token)
 - `POST /api/contracts/` - criar contrato (Bearer token)

## Empacotando como executável
### Windows (PyInstaller)
```bash
pip install pyinstaller
pyinstaller --onefile --add-data "data;data" server/app.py
```
Isso gera `dist/app.exe` que contém o servidor e o banco local `data/app.sqlite3`.

### Linux
```bash
pip install pyinstaller
pyinstaller --onefile --add-data "data:data" server/app.py
```
Gera `dist/app` executável.

Observação: para incluir dependências nativas e arquivos estáticos, ajuste `--add-data` e flags.

## Testes automatizados (pytest)

Instale dependências e rode os testes:
```bash
pip install -r requirements.txt
pytest -q
```

## Seed de dados

Popule exemplo de dados:
```bash
python -m server.seed
```

## Docker (opção local)

Build e run:
```bash
docker compose build
docker compose up
```

## Como integrar o frontend (parity com workspace original)

Se você tiver o build do frontend (a pasta `dist` do workspace principal), copie para o servidor estático:

```bash
cd c:\workspace2\python_app
python copy_frontend.py C:\workspace\dist
```

Isso colocará os arquivos estáticos em `server/static/` e a aplicação servirá o frontend automaticamente.

## Empacotamento e instaladores

Para informações completas de build e empacotamento, consulte `python_app/installer/README.md`.

Lá estão descritos os fluxos para:
- PyInstaller (Windows e Linux)
- instalador NSIS (Windows)
- MSI com WiX (Windows)
- pacote DEB (Linux)

## Observações
- Esta versão não inclui integração com Supabase nem Google OAuth (local-only).
- É intencionalmente simples para permitir instalação local e manutenção de colaboradores.
- Para converter a interface React existente em estática, copie o `dist/` do projeto original para `python_app/static/`.
