import os
import sys
import sqlite3
import urllib.request
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
    cur.execute('''CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        email TEXT NOT NULL UNIQUE,
        password_hash TEXT NOT NULL,
        role TEXT NOT NULL DEFAULT 'admin',
        active INTEGER NOT NULL DEFAULT 1,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    cur.execute('''CREATE TABLE IF NOT EXISTS colaboradores (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        email TEXT NOT NULL UNIQUE,
        role TEXT NOT NULL DEFAULT 'colaborador',
        active INTEGER NOT NULL DEFAULT 1,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    cur.execute('''CREATE TABLE IF NOT EXISTS clientes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nome TEXT NOT NULL,
        documento TEXT,
        tipo_pessoa TEXT DEFAULT 'PF',
        telefone TEXT,
        email TEXT,
        cep TEXT, logradouro TEXT, numero TEXT,
        complemento TEXT, bairro TEXT, cidade TEXT, estado TEXT,
        banco_nome TEXT, banco_agencia TEXT, banco_conta TEXT,
        banco_tipo TEXT, banco_pix TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    cur.execute('''CREATE TABLE IF NOT EXISTS proprietarios (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nome TEXT NOT NULL,
        documento TEXT,
        tipo_pessoa TEXT DEFAULT 'PF',
        telefone TEXT,
        email TEXT,
        cep TEXT, logradouro TEXT, numero TEXT,
        complemento TEXT, bairro TEXT, cidade TEXT, estado TEXT,
        banco_nome TEXT, banco_agencia TEXT, banco_conta TEXT,
        banco_tipo TEXT, banco_pix TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    cur.execute('''CREATE TABLE IF NOT EXISTS pontos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nome TEXT NOT NULL,
        tipo TEXT NOT NULL DEFAULT 'OUTDOOR',
        cep TEXT, logradouro TEXT, numero TEXT,
        complemento TEXT, bairro TEXT, cidade TEXT, estado TEXT,
        endereco TEXT,
        latitude REAL, longitude REAL,
        status TEXT DEFAULT 'DISPONIVEL',
        proprietario_id INTEGER,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(proprietario_id) REFERENCES proprietarios(id))''')
    cur.execute('''CREATE TABLE IF NOT EXISTS contratos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        cliente_id INTEGER NOT NULL,
        ponto_id INTEGER NOT NULL,
        valor_cents INTEGER DEFAULT 0,
        repasse_percent REAL DEFAULT 0,
        repasse_cents INTEGER DEFAULT 0,
        tipo_repasse TEXT DEFAULT 'DINHEIRO',
        status TEXT DEFAULT 'ATIVO',
        data_inicio DATE,
        data_termino DATE,
        observacoes TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(cliente_id) REFERENCES clientes(id),
        FOREIGN KEY(ponto_id) REFERENCES pontos(id))''')
    # ── Módulo financeiro ──────────────────────────────────────
    cur.execute('''CREATE TABLE IF NOT EXISTS lancamentos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        tipo TEXT NOT NULL CHECK(tipo IN ('ENTRADA','SAIDA')),
        categoria TEXT NOT NULL,
        descricao TEXT,
        valor_cents INTEGER NOT NULL,
        data_lancamento DATE NOT NULL,
        contrato_id INTEGER,
        cliente_id INTEGER,
        proprietario_id INTEGER,
        status TEXT DEFAULT 'PENDENTE' CHECK(status IN ('PENDENTE','PAGO','CANCELADO')),
        data_pagamento DATE,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(contrato_id) REFERENCES contratos(id),
        FOREIGN KEY(cliente_id) REFERENCES clientes(id),
        FOREIGN KEY(proprietario_id) REFERENCES proprietarios(id))''')
    # ── Migrations para bancos existentes ─────────────────────
    def _col(t, c, tp='TEXT'):
        try: cur.execute(f'ALTER TABLE {t} ADD COLUMN {c} {tp}')
        except: pass
    for c in ['cep','logradouro','numero','complemento','bairro','cidade','estado',
              'banco_nome','banco_agencia','banco_conta','banco_tipo','banco_pix','tipo_pessoa']:
        _col('clientes', c); _col('proprietarios', c)
    for c in ['cep','logradouro','numero','complemento','bairro','cidade','estado','endereco']:
        _col('pontos', c)
    for c in ['repasse_percent','repasse_cents','tipo_repasse','observacoes']:
        tp = 'REAL' if c == 'repasse_percent' else ('INTEGER' if c == 'repasse_cents' else 'TEXT')
        _col('contratos', c, tp)
    conn.commit(); conn.close()

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

def gerar_lancamentos_contrato(contrato_id, conn):
    """Gera automaticamente lançamentos de entrada e repasse para o contrato."""
    c = conn.execute(
        'SELECT id, cliente_id, ponto_id, valor_cents, repasse_cents, tipo_repasse, '
        'data_inicio, data_termino FROM contratos WHERE id=?', (contrato_id,)).fetchone()
    if not c: return
    ponto = conn.execute(
        'SELECT proprietario_id, nome FROM pontos WHERE id=?', (c['ponto_id'],)).fetchone()
    # Lançamento de entrada (recebimento do cliente)
    conn.execute('''INSERT INTO lancamentos
        (tipo, categoria, descricao, valor_cents, data_lancamento,
         contrato_id, cliente_id, status)
        VALUES (?,?,?,?,?,?,?,?)''',
        ('ENTRADA', 'ALUGUEL', f'Contrato #{contrato_id} - Aluguel mensal',
         c['valor_cents'], c['data_inicio'] or str(datetime.date.today()),
         contrato_id, c['cliente_id'], 'PENDENTE'))
    # Lançamento de repasse ao proprietário (se houver)
    if ponto and ponto['proprietario_id'] and c['repasse_cents'] and c['repasse_cents'] > 0:
        desc = (f'Repasse contrato #{contrato_id} - {ponto["nome"]}'
                if c['tipo_repasse'] == 'DINHEIRO'
                else f'Permuta contrato #{contrato_id} - {ponto["nome"]}')
        conn.execute('''INSERT INTO lancamentos
            (tipo, categoria, descricao, valor_cents, data_lancamento,
             contrato_id, proprietario_id, status)
            VALUES (?,?,?,?,?,?,?,?)''',
            ('SAIDA', 'REPASSE', desc,
             c['repasse_cents'], c['data_inicio'] or str(datetime.date.today()),
             contrato_id, ponto['proprietario_id'], 'PENDENTE'))

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

# ── Financeiro: lançamentos ────────────────────────────────────
@app.route('/api/financeiro/lancamentos', methods=['GET'])
@token_required
def list_lancamentos():
    conn  = get_db()
    tipo  = request.args.get('tipo')
    mes   = request.args.get('mes')   # YYYY-MM
    status = request.args.get('status')
    q  = '''SELECT l.*, c.nome as cliente_nome, p.nome as proprietario_nome
            FROM lancamentos l
            LEFT JOIN clientes c ON c.id = l.cliente_id
            LEFT JOIN proprietarios p ON p.id = l.proprietario_id
            WHERE 1=1'''
    params = []
    if tipo:   q += ' AND l.tipo=?';   params.append(tipo)
    if mes:    q += ' AND strftime("%Y-%m", l.data_lancamento)=?'; params.append(mes)
    if status: q += ' AND l.status=?'; params.append(status)
    q += ' ORDER BY l.data_lancamento DESC'
    rows = conn.execute(q, params).fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])

@app.route('/api/financeiro/lancamentos', methods=['POST'])
@token_required
def add_lancamento():
    d = request.get_json() or {}
    required = ['tipo','categoria','valor_cents','data_lancamento']
    for f in required:
        if not d.get(f): return jsonify({'error': f'{f} required'}), 400
    if d['tipo'] not in ('ENTRADA','SAIDA'):
        return jsonify({'error': 'tipo must be ENTRADA or SAIDA'}), 400
    conn = get_db(); cur = conn.cursor()
    cur.execute('''INSERT INTO lancamentos
        (tipo,categoria,descricao,valor_cents,data_lancamento,
         contrato_id,cliente_id,proprietario_id,status)
        VALUES (?,?,?,?,?,?,?,?,?)''',
        (d['tipo'], d['categoria'], d.get('descricao'), d['valor_cents'],
         d['data_lancamento'], d.get('contrato_id'), d.get('cliente_id'),
         d.get('proprietario_id'), d.get('status','PENDENTE')))
    conn.commit()
    row = conn.execute('SELECT * FROM lancamentos WHERE id=?',(cur.lastrowid,)).fetchone()
    conn.close(); return jsonify(dict(row))

@app.route('/api/financeiro/lancamentos/<int:lid>', methods=['PUT'])
@token_required
def update_lancamento(lid):
    if not row_exists('lancamentos', lid):
        return jsonify({'error': 'Not found'}), 404
    d = request.get_json() or {}
    conn = get_db()
    conn.execute('''UPDATE lancamentos SET
        status=COALESCE(?,status), data_pagamento=COALESCE(?,data_pagamento),
        descricao=COALESCE(?,descricao), valor_cents=COALESCE(?,valor_cents)
        WHERE id=?''',
        (d.get('status'), d.get('data_pagamento'),
         d.get('descricao'), d.get('valor_cents'), lid))
    conn.commit()
    row = conn.execute('SELECT * FROM lancamentos WHERE id=?',(lid,)).fetchone()
    conn.close(); return jsonify(dict(row))

@app.route('/api/financeiro/lancamentos/<int:lid>', methods=['DELETE'])
@token_required
def delete_lancamento(lid):
    if not row_exists('lancamentos', lid):
        return jsonify({'error': 'Not found'}), 404
    conn = get_db()
    conn.execute('DELETE FROM lancamentos WHERE id=?',(lid,))
    conn.commit(); conn.close()
    return jsonify({'deleted': lid})

@app.route('/api/financeiro/resumo', methods=['GET'])
@token_required
def resumo_financeiro():
    mes = request.args.get('mes')  # YYYY-MM, opcional
    conn = get_db()
    def _sum(tipo, status=None, mes=None):
        q = 'SELECT COALESCE(SUM(valor_cents),0) FROM lancamentos WHERE tipo=?'
        p = [tipo]
        if status: q += ' AND status=?'; p.append(status)
        if mes: q += ' AND strftime("%Y-%m",data_lancamento)=?'; p.append(mes)
        return conn.execute(q, p).fetchone()[0]
    resultado = {
        'entradas_total':    _sum('ENTRADA', mes=mes),
        'entradas_pagas':    _sum('ENTRADA', 'PAGO', mes),
        'entradas_pendentes':_sum('ENTRADA', 'PENDENTE', mes),
        'saidas_total':      _sum('SAIDA', mes=mes),
        'saidas_pagas':      _sum('SAIDA', 'PAGO', mes),
        'saidas_pendentes':  _sum('SAIDA', 'PENDENTE', mes),
        'saldo_realizado':   _sum('ENTRADA','PAGO',mes) - _sum('SAIDA','PAGO',mes),
        'saldo_previsto':    _sum('ENTRADA',mes=mes) - _sum('SAIDA',mes=mes),
        'mes': mes or 'todos',
    }
    conn.close(); return jsonify(resultado)

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
