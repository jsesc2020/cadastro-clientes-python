import os
import sys
import sqlite3
import urllib.request
import urllib.parse
import json as _json
from flask import Flask, request, jsonify, send_from_directory
from werkzeug.security import generate_password_hash, check_password_hash
import jwt
import datetime
from functools import wraps
from pathlib import Path

# ── Detecta modo PyInstaller vs script normal ──────────────────
if getattr(sys, 'frozen', False):
    _BUNDLE  = Path(sys._MEIPASS)
    _EXE_DIR = Path(sys.executable).parent
    BASE_DIR   = _BUNDLE
    DATA_DIR   = _EXE_DIR / 'data'
    STATIC_DIR = _BUNDLE / 'server' / 'static'
else:
    BASE_DIR   = Path(__file__).resolve().parent.parent
    DATA_DIR   = BASE_DIR / 'data'
    STATIC_DIR = Path(__file__).resolve().parent / 'static'

DATA_DIR.mkdir(parents=True, exist_ok=True)
DB_PATH    = DATA_DIR / 'app.sqlite3'
JWT_SECRET = os.environ.get('JWT_SECRET', 'devsecret')

app = Flask(__name__, static_folder=str(STATIC_DIR))

# ── DB helpers ─────────────────────────────────────────────────
def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute('PRAGMA foreign_keys = ON')   # FIX: FK não era aplicada
    return conn

def init_db():
    conn = get_db()
    cur  = conn.cursor()

    cur.execute("""CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        email TEXT NOT NULL UNIQUE, password_hash TEXT NOT NULL,
        role TEXT NOT NULL DEFAULT 'admin', active INTEGER NOT NULL DEFAULT 1,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)""")

    cur.execute("""CREATE TABLE IF NOT EXISTS colaboradores (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        email TEXT NOT NULL UNIQUE, role TEXT NOT NULL DEFAULT 'colaborador',
        active INTEGER NOT NULL DEFAULT 1,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)""")

    cur.execute("""CREATE TABLE IF NOT EXISTS config (
        chave TEXT PRIMARY KEY, valor TEXT NOT NULL, descricao TEXT)""")

    cur.execute("""CREATE TABLE IF NOT EXISTS clientes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nome TEXT NOT NULL, documento TEXT, tipo_pessoa TEXT DEFAULT 'PF',
        telefone TEXT, email TEXT,
        cep TEXT, logradouro TEXT, numero TEXT, complemento TEXT,
        bairro TEXT, cidade TEXT, estado TEXT,
        banco_nome TEXT, banco_agencia TEXT, banco_conta TEXT,
        banco_tipo TEXT, banco_pix TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)""")

    cur.execute("""CREATE TABLE IF NOT EXISTS proprietarios (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nome TEXT NOT NULL, documento TEXT, tipo_pessoa TEXT DEFAULT 'PF',
        telefone TEXT, email TEXT,
        cep TEXT, logradouro TEXT, numero TEXT, complemento TEXT,
        bairro TEXT, cidade TEXT, estado TEXT,
        banco_nome TEXT, banco_agencia TEXT, banco_conta TEXT,
        banco_tipo TEXT, banco_pix TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)""")

    cur.execute("""CREATE TABLE IF NOT EXISTS pontos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nome TEXT NOT NULL, tipo TEXT NOT NULL DEFAULT 'OUTDOOR',
        cep TEXT, logradouro TEXT, numero TEXT, complemento TEXT,
        bairro TEXT, cidade TEXT, estado TEXT, endereco TEXT,
        latitude REAL, longitude REAL,
        status TEXT DEFAULT 'DISPONIVEL',
        proprietario_id INTEGER,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(proprietario_id) REFERENCES proprietarios(id))""")

    cur.execute("""CREATE TABLE IF NOT EXISTS contratos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        cliente_id INTEGER NOT NULL,
        ponto_id INTEGER NOT NULL,
        proprietario_id INTEGER,
        valor_cents INTEGER DEFAULT 0,
        num_parcelas INTEGER DEFAULT 1,
        repasse_percent REAL DEFAULT 0,
        repasse_cents INTEGER DEFAULT 0,
        tipo_repasse TEXT DEFAULT 'DINHEIRO',
        dia_vencimento INTEGER DEFAULT 25,
        dia_pagamento INTEGER DEFAULT 30,
        status TEXT DEFAULT 'ATIVO',
        data_inicio DATE, data_termino DATE, observacoes TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(cliente_id) REFERENCES clientes(id),
        FOREIGN KEY(ponto_id)   REFERENCES pontos(id),
        FOREIGN KEY(proprietario_id) REFERENCES proprietarios(id))""")

    cur.execute("""CREATE TABLE IF NOT EXISTS parcelas (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        contrato_id INTEGER NOT NULL,
        tipo TEXT NOT NULL CHECK(tipo IN ('RECEBIMENTO','REPASSE')),
        numero INTEGER NOT NULL,
        competencia TEXT NOT NULL,
        data_vencimento DATE NOT NULL,
        valor_cents INTEGER NOT NULL,
        status TEXT DEFAULT 'PENDENTE' CHECK(status IN ('PENDENTE','PAGO','CANCELADO','ATRASADO')),
        data_pagamento DATE, observacoes TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(contrato_id) REFERENCES contratos(id))""")

    # Config defaults
    cur.execute("INSERT OR IGNORE INTO config VALUES ('dia_vencimento_locatario','25','Dia do vencimento das parcelas dos clientes')")
    cur.execute("INSERT OR IGNORE INTO config VALUES ('dia_pagamento_locador','30','Dia do pagamento das parcelas aos proprietarios')")

    # ── Migrations para bancos existentes ──────────────────────
    def _col(t, c, tp='TEXT'):
        # Whitelist de tipos validos para prevenir injecao em migracao
        _safe_types = ('TEXT','INTEGER','REAL','BLOB','NUMERIC')
        if tp.upper() not in _safe_types: return
        try: cur.execute(f'ALTER TABLE {t} ADD COLUMN {c} {tp}')
        except: pass

    for c in ['cep','logradouro','numero','complemento','bairro','cidade','estado',
              'banco_nome','banco_agencia','banco_conta','banco_tipo','banco_pix','tipo_pessoa']:
        _col('clientes', c); _col('proprietarios', c)
    for c in ['cep','logradouro','numero','complemento','bairro','cidade','estado','endereco']:
        _col('pontos', c)
    for row in [('proprietario_id','INTEGER'),('num_parcelas','INTEGER'),
                ('repasse_percent','REAL'),('repasse_cents','INTEGER'),
                ('tipo_repasse','TEXT'),('dia_vencimento','INTEGER'),
                ('dia_pagamento','INTEGER'),('observacoes','TEXT')]:
        _col('contratos', row[0], row[1])
    # taxa bancaria em parcelas e lancamentos
    _col('parcelas',    'taxa_cents', 'INTEGER')
    _col('lancamentos', 'taxa_cents', 'INTEGER')

    conn.commit()
    conn.close()


# ── Domain helpers ─────────────────────────────────────────────
def row_exists(table, row_id):
    conn = get_db()
    r = conn.execute(f'SELECT 1 FROM {table} WHERE id=?', (row_id,)).fetchone()
    conn.close(); return bool(r)

def ponto_has_active_contract(ponto_id, ignore_contract_id=None):
    conn = get_db()
    if ignore_contract_id:
        r = conn.execute('SELECT 1 FROM contratos WHERE ponto_id=? AND status=? AND id!=?',
                         (ponto_id,'ATIVO',ignore_contract_id)).fetchone()
    else:
        r = conn.execute('SELECT 1 FROM contratos WHERE ponto_id=? AND status=?',
                         (ponto_id,'ATIVO')).fetchone()
    conn.close(); return bool(r)

def update_ponto_status_from_contracts(ponto_id):
    conn = get_db()
    active = conn.execute('SELECT 1 FROM contratos WHERE ponto_id=? AND status=?',
                          (ponto_id,'ATIVO')).fetchone()
    st = 'OCUPADO' if active else 'DISPONIVEL'
    conn.execute('UPDATE pontos SET status=? WHERE id=?', (st, ponto_id))
    conn.commit(); conn.close(); return st

# ── Auth decorator ─────────────────────────────────────────────
def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth  = request.headers.get('Authorization', '')
        token = auth.split(' ')[1] if auth.startswith('Bearer ') else None
        if not token:
            return jsonify({'error': 'Token is missing'}), 401
        try:
            data = jwt.decode(token, JWT_SECRET, algorithms=['HS256'])
            conn = get_db()
            user = conn.execute(
                'SELECT id,email,role,active FROM users WHERE id=?',
                (data.get('sub'),)).fetchone()
            conn.close()
            if not user or not user['active']:
                return jsonify({'error': 'User not found or inactive'}), 401
            request.user = dict(user)
        except Exception as e:
            return jsonify({'error': 'Token invalid', 'details': str(e)}), 401
        return f(*args, **kwargs)
    return decorated

# ── Auth routes ────────────────────────────────────────────────
@app.route('/api/auth/register', methods=['POST'])
def register():
    d = request.get_json() or {}
    email, pwd = d.get('email','').strip(), d.get('password','')
    if not email or not pwd:
        return jsonify({'error': 'Email and password required'}), 400
    if len(pwd) < 6:
        return jsonify({'error': 'Password must be at least 6 characters'}), 400
    conn = get_db(); cur = conn.cursor()
    try:
        cur.execute('INSERT INTO users (email,password_hash,role,active) VALUES (?,?,?,?)',
                    (email, generate_password_hash(pwd), 'admin', 1))
        conn.commit()
        return jsonify({'id': cur.lastrowid, 'email': email})
    except sqlite3.IntegrityError:
        return jsonify({'error': 'User already exists'}), 400
    finally: conn.close()

@app.route('/api/auth/login', methods=['POST'])
def login():
    d = request.get_json() or {}
    email, pwd = d.get('email','').strip(), d.get('password','')
    if not email or not pwd:
        return jsonify({'error': 'Email and password required'}), 400
    conn = get_db()
    user = conn.execute(
        'SELECT id,email,password_hash,role,active FROM users WHERE email=?',(email,)).fetchone()
    conn.close()
    if not user or not check_password_hash(user['password_hash'], pwd):
        return jsonify({'error': 'Invalid credentials'}), 401
    if not user['active']:
        return jsonify({'error': 'User inactive'}), 401
    token = jwt.encode(
        {'sub': user['id'], 'email': user['email'], 'role': user['role'],
         'exp': datetime.datetime.utcnow() + datetime.timedelta(days=7)},
        JWT_SECRET, algorithm='HS256')
    return jsonify({'token': token, 'email': user['email'], 'role': user['role']})

@app.route('/api/collaborators', methods=['GET'])
@token_required
def list_collaborators():
    conn = get_db()
    rows = conn.execute(
        'SELECT id,email,role,active,created_at FROM colaboradores ORDER BY created_at DESC'
    ).fetchall()
    conn.close(); return jsonify([dict(r) for r in rows])

@app.route('/api/collaborators', methods=['POST'])
@token_required
def add_collaborator():
    body  = request.get_json() or {}
    email = body.get('email','').strip()
    if not email: return jsonify({'error': 'Email required'}), 400
    conn = get_db(); cur = conn.cursor()
    try:
        cur.execute('INSERT INTO colaboradores (email,role,active) VALUES (?,?,?)',
                    (email, body.get('role','colaborador'), 1))
        conn.commit()
        row = conn.execute('SELECT id,email,role,active,created_at FROM colaboradores WHERE id=?',
                           (cur.lastrowid,)).fetchone()
        return jsonify(dict(row))
    except sqlite3.IntegrityError:
        return jsonify({'error': 'Colaborador already exists'}), 400
    finally: conn.close()

# ── Schema: tabela gastos (lancamentos manuais) ──────────────
# A tabela lancamentos do repo armazena gastos operacionais manuais
# As parcelas de contratos ficam na tabela parcelas
# O resumo consolida ambas

# ── Financeiro: lancamentos manuais (gastos e receitas avulsas) ─
@app.route('/api/financeiro/lancamentos', methods=['GET'])
@token_required
def list_lancamentos():
    conn   = get_db()
    tipo   = request.args.get('tipo')
    mes    = request.args.get('mes')
    status = request.args.get('status')
    q = """SELECT l.*,
               c.nome  as cliente_nome,
               pr.nome as proprietario_nome
           FROM lancamentos l
           LEFT JOIN clientes c      ON c.id  = l.cliente_id
           LEFT JOIN proprietarios pr ON pr.id = l.proprietario_id
           WHERE 1=1"""
    params = []
    if tipo:   q += ' AND l.tipo=?';   params.append(tipo)
    if status: q += ' AND l.status=?'; params.append(status)
    if mes:    q += ' AND strftime("%Y-%m", l.data_lancamento)=?'; params.append(mes)
    q += ' ORDER BY l.data_lancamento DESC'
    rows = conn.execute(q, params).fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])

@app.route('/api/financeiro/lancamentos', methods=['POST'])
@token_required
def add_lancamento():
    d = request.get_json() or {}
    if not d.get('tipo') or not d.get('categoria') or not d.get('valor_cents'):
        return jsonify({'error': 'tipo, categoria e valor_cents obrigatorios'}), 400
    if d['tipo'] not in ('ENTRADA', 'SAIDA'):
        return jsonify({'error': 'tipo deve ser ENTRADA ou SAIDA'}), 400
    conn = get_db(); cur = conn.cursor()
    cur.execute("""INSERT INTO lancamentos
        (tipo, categoria, descricao, valor_cents, taxa_cents,
         data_lancamento, contrato_id, cliente_id, proprietario_id, status)
        VALUES (?,?,?,?,?,?,?,?,?,?)""",
        (d['tipo'], d['categoria'], d.get('descricao'),
         int(d['valor_cents']), int(d.get('taxa_cents') or 0),
         d.get('data_lancamento') or datetime.date.today().isoformat(),
         d.get('contrato_id'), d.get('cliente_id'), d.get('proprietario_id'),
         d.get('status', 'PAGO')))
    conn.commit()
    row = conn.execute('SELECT * FROM lancamentos WHERE id=?', (cur.lastrowid,)).fetchone()
    conn.close()
    return jsonify(dict(row))

@app.route('/api/financeiro/lancamentos/<int:lid>', methods=['PUT'])
@token_required
def update_lancamento(lid):
    if not row_exists('lancamentos', lid):
        return jsonify({'error': 'Not found'}), 404
    d = request.get_json() or {}
    conn = get_db()
    conn.execute("""UPDATE lancamentos SET
        status=COALESCE(?,status),
        data_pagamento=COALESCE(?,data_pagamento),
        descricao=COALESCE(?,descricao),
        valor_cents=COALESCE(?,valor_cents),
        taxa_cents=COALESCE(?,taxa_cents)
        WHERE id=?""",
        (d.get('status'), d.get('data_pagamento'),
         d.get('descricao'), d.get('valor_cents'),
         d.get('taxa_cents'), lid))
    conn.commit()
    row = conn.execute('SELECT * FROM lancamentos WHERE id=?', (lid,)).fetchone()
    conn.close()
    return jsonify(dict(row))

@app.route('/api/financeiro/lancamentos/<int:lid>', methods=['DELETE'])
@token_required
def delete_lancamento(lid):
    if not row_exists('lancamentos', lid):
        return jsonify({'error': 'Not found'}), 404
    conn = get_db()
    conn.execute('DELETE FROM lancamentos WHERE id=?', (lid,))
    conn.commit(); conn.close()
    return jsonify({'deleted': lid})

# ── Parcelas: baixa com data retroativa ───────────────────────
@app.route('/api/financeiro/parcelas', methods=['GET'])
@token_required
def list_parcelas_fin():
    conn   = get_db()
    tipo   = request.args.get('tipo')
    mes    = request.args.get('mes')
    status = request.args.get('status')
    q = """SELECT p.*,
               ct.cliente_id, ct.proprietario_id,
               cl.nome  as cliente_nome,
               pr.nome  as proprietario_nome,
               po.nome  as ponto_nome
           FROM parcelas p
           JOIN contratos ct         ON ct.id = p.contrato_id
           LEFT JOIN clientes cl     ON cl.id = ct.cliente_id
           LEFT JOIN proprietarios pr ON pr.id = ct.proprietario_id
           LEFT JOIN pontos po        ON po.id = ct.ponto_id
           WHERE 1=1"""
    params = []
    if tipo:   q += ' AND p.tipo=?';   params.append(tipo)
    if status: q += ' AND p.status=?'; params.append(status)
    if mes:    q += ' AND strftime("%Y-%m", p.data_vencimento)=?'; params.append(mes)
    q += ' ORDER BY p.data_vencimento ASC'
    rows = conn.execute(q, params).fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])

@app.route('/api/financeiro/parcelas/<int:pid>/pagar', methods=['POST'])
@token_required
def pagar_parcela_fin(pid):
    d    = request.get_json() or {}
    # Permite data retroativa: usa a data informada ou hoje
    data = d.get('data_pagamento') or datetime.date.today().isoformat()
    taxa = int(d.get('taxa_cents') or 0)
    conn = get_db()
    row  = conn.execute('SELECT * FROM parcelas WHERE id=?', (pid,)).fetchone()
    if not row:
        conn.close(); return jsonify({'error': 'Parcela nao encontrada'}), 404
    conn.execute("""UPDATE parcelas SET
        status='PAGO', data_pagamento=?,
        taxa_cents=COALESCE(?,taxa_cents), observacoes=COALESCE(?,observacoes)
        WHERE id=?""",
        (data, taxa if taxa else None, d.get('observacoes'), pid))
    conn.commit()
    updated = conn.execute('SELECT * FROM parcelas WHERE id=?', (pid,)).fetchone()
    conn.close()
    return jsonify(dict(updated))

@app.route('/api/financeiro/parcelas/<int:pid>', methods=['PUT'])
@token_required
def update_parcela_fin(pid):
    d    = request.get_json() or {}
    conn = get_db()
    row  = conn.execute('SELECT * FROM parcelas WHERE id=?', (pid,)).fetchone()
    if not row:
        conn.close(); return jsonify({'error': 'Parcela nao encontrada'}), 404
    conn.execute("""UPDATE parcelas SET
        status=COALESCE(?,status),
        data_vencimento=COALESCE(?,data_vencimento),
        data_pagamento=COALESCE(?,data_pagamento),
        valor_cents=COALESCE(?,valor_cents),
        taxa_cents=COALESCE(?,taxa_cents),
        observacoes=COALESCE(?,observacoes)
        WHERE id=?""",
        (d.get('status'), d.get('data_vencimento'), d.get('data_pagamento'),
         d.get('valor_cents'), d.get('taxa_cents'), d.get('observacoes'), pid))
    conn.commit()
    updated = conn.execute('SELECT * FROM parcelas WHERE id=?', (pid,)).fetchone()
    conn.close()
    return jsonify(dict(updated))

# ── Resumo financeiro consolidado ────────────────────────────
@app.route('/api/financeiro/resumo', methods=['GET'])
@token_required
def resumo_financeiro():
    mes  = request.args.get('mes')
    conn = get_db()

    def _parc(tipo, status=None, m=None):
        q = 'SELECT COALESCE(SUM(valor_cents+COALESCE(taxa_cents,0)),0) FROM parcelas WHERE tipo=?'
        p = [tipo]
        if status: q += ' AND status=?'; p.append(status)
        if m:      q += ' AND strftime("%Y-%m",data_vencimento)=?'; p.append(m)
        return conn.execute(q, p).fetchone()[0]

    def _lanc(tipo, status=None, m=None):
        q = 'SELECT COALESCE(SUM(valor_cents+COALESCE(taxa_cents,0)),0) FROM lancamentos WHERE tipo=?'
        p = [tipo]
        if status: q += ' AND status=?'; p.append(status)
        if m:      q += ' AND strftime("%Y-%m",data_lancamento)=?'; p.append(m)
        return conn.execute(q, p).fetchone()[0]

    resultado = {
        # Recebimentos de contratos (parcelas)
        'recebimentos_total':     _parc('RECEBIMENTO', m=mes),
        'recebimentos_pagos':     _parc('RECEBIMENTO', 'PAGO', mes),
        'recebimentos_pendentes': _parc('RECEBIMENTO', 'PENDENTE', mes),
        # Repasses a proprietarios (parcelas)
        'repasses_total':         _parc('REPASSE', m=mes),
        'repasses_pagos':         _parc('REPASSE', 'PAGO', mes),
        'repasses_pendentes':     _parc('REPASSE', 'PENDENTE', mes),
        # Entradas avulsas (lancamentos manuais)
        'entradas_total':         _lanc('ENTRADA', m=mes),
        'entradas_pagas':         _lanc('ENTRADA', 'PAGO', mes),
        # Saidas avulsas: gastos operacionais, taxas bancarias, etc.
        'saidas_total':           _lanc('SAIDA', m=mes),
        'saidas_pagas':           _lanc('SAIDA', 'PAGO', mes),
        # Saldos
        'saldo_realizado': (
            _parc('RECEBIMENTO','PAGO',mes) + _lanc('ENTRADA','PAGO',mes)
            - _parc('REPASSE','PAGO',mes) - _lanc('SAIDA','PAGO',mes)
        ),
        'saldo_previsto': (
            _parc('RECEBIMENTO',m=mes) + _lanc('ENTRADA',m=mes)
            - _parc('REPASSE',m=mes) - _lanc('SAIDA',m=mes)
        ),
        'mes': mes or 'todos',
    }
    conn.close()
    return jsonify(resultado)

# ── Proxy CNPJ (BrasilAPI) ────────────────────────────────────
# Proxy interno evita bloqueio CORS/TLS quando rodando como .exe
@app.route('/api/util/cnpj/<cnpj>', methods=['GET'])
@token_required
def proxy_cnpj(cnpj):
    cnpj_digits = ''.join(c for c in cnpj if c.isdigit())
    if len(cnpj_digits) != 14:
        return jsonify({'error': 'CNPJ deve ter 14 digitos'}), 400
    url = f'https://brasilapi.com.br/api/cnpj/v1/{cnpj_digits}'
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'MidiaControl/1.0'})
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = _json.loads(resp.read().decode('utf-8'))
        # Normaliza telefone: remove DDD duplicado se necessário
        tel_raw = data.get('ddd_telefone_1', '')
        if tel_raw:
            digits = ''.join(c for c in tel_raw if c.isdigit())
            if len(digits) >= 10:
                data['telefone'] = f'({digits[:2]}) {digits[2:]}'
            else:
                data['telefone'] = tel_raw
        return jsonify(data)
    except urllib.error.HTTPError as e:
        return jsonify({'error': f'CNPJ nao encontrado (HTTP {e.code})'}), 404
    except Exception as e:
        return jsonify({'error': f'Erro ao consultar CNPJ: {str(e)}'}), 502

# ── Frontend ───────────────────────────────────────────────────
@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def serve(path):
    sd = Path(app.static_folder)
    if path and (sd / path).exists():
        return send_from_directory(str(sd), path)
    idx = sd / 'index.html'
    if idx.exists():
        return send_from_directory(str(sd), 'index.html')
    return jsonify({'status': 'frontend not found', 'static_folder': str(sd),
                    'frozen': str(getattr(sys, 'frozen', False))})

# ── Blueprints ─────────────────────────────────────────────────
try:
    from .routes.clients      import bp as clients_bp
    from .routes.contracts    import bp as contracts_bp
    from .routes.pontos       import bp as pontos_bp
    from .routes.proprietarios import bp as proprietarios_bp
except ImportError:
    from server.routes.clients      import bp as clients_bp
    from server.routes.contracts    import bp as contracts_bp
    from server.routes.pontos       import bp as pontos_bp
    from server.routes.proprietarios import bp as proprietarios_bp

app.register_blueprint(clients_bp,       url_prefix='/api/clients')
app.register_blueprint(contracts_bp,     url_prefix='/api/contracts')
app.register_blueprint(pontos_bp,        url_prefix='/api/pontos')
app.register_blueprint(proprietarios_bp, url_prefix='/api/proprietarios')

if __name__ == '__main__':
    init_db()
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)), debug=True)
