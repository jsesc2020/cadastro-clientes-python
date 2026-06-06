# cadastro-clientes-python

Repositório para a versão local do sistema de cadastro de clientes em Python.

## Estrutura principal

- `python_app/` - aplicação standalone baseada em Flask + SQLite
- `python_app/server/` - backend Flask e rotas de API
- `python_app/installer/` - scripts e templates de instalador
- `python_app/README.md` - documentação do app local
- `.github/workflows/package.yml` - GitHub Actions para build de EXE/MSI/DEB

## Como usar

1. Entre em `python_app/`
2. Instale dependências:
   ```bash
   python -m venv .venv
   .venv\Scripts\activate
   pip install -r requirements.txt
   ```
3. Veja `python_app/README.md` e `python_app/installer/README.md` para instruções completas de build e empacotamento.
