import os
import sqlite3
from flask import Flask, request, jsonify, send_from_directory
from werkzeug.security import generate_password_hash, check_password_hash
import jwt
import datetime
from functools import wraps
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / 'data'
DATA_DIR.mkdir(exist_ok=True)
DB_PATH = DATA_DIR / 'app.sqlite3'
JWT_SECRET = os.environ.get('JWT_SECRET', 'devsecret')

app = Flask(__name__, static_folder=str(BASE_DIR / 'static'))

# DB helpers - must be defined BEFORE importing routes to avoid circular imports
def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    cur = conn.cursor()
    cur.execute('''
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        email TEXT NOT NULL UNIQUE,
        password_hash TEXT NOT NULL,
        role TEXT NOT NULL DEFAULT 'admin',
        active INTEGER NOT NULL DEFAULT 1,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    cur.execute('''
    CREATE TABLE IF NOT EXISTS colaboradores (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        email TEXT NOT NULL UNIQUE,
        role TEXT NOT NULL DEFAULT 'colaborador',
        active INTEGER NOT NULL DEFAULT 1,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    cur.execute('''
    CREATE TABLE IF NOT EXISTS clientes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nome TEXT NOT NULL,
        documento TEXT,
        telefone TEXT,
        email TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    cur.execute('''
    CREATE TABLE IF NOT EXISTS contratos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        cliente_id INTEGER NOT NULL,
        ponto_id INTEGER NOT NULL,
        valor_cents INTEGER DEFAULT 0,
        status TEXT DEFAULT 'ATIVO',
        data_inicio DATE,
        data_termino DATE,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(cliente_id) REFERENCES clientes(id)
    )
    ''')
    cur.execute('''
    CREATE TABLE IF NOT EXISTS pontos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nome TEXT NOT NULL,
        tipo TEXT NOT NULL DEFAULT 'OUTDOOR',
        endereco TEXT,
        latitude REAL,
        longitude REAL,
        status TEXT DEFAULT 'DISPONIVEL',
        proprietario_id INTEGER,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    cur.execute('''
    CREATE TABLE IF NOT EXISTS proprietarios (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nome TEXT NOT NULL,
        documento TEXT,
        telefone TEXT,
        email TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    conn.commit()
    conn.close()

# Domain helpers

def row_exists(table, row_id):
    conn = get_db()
    row = conn.execute(f'SELECT 1 FROM {table} WHERE id = ?', (row_id,)).fetchone()
    conn.close()
    return bool(row)


def ponto_has_active_contract(ponto_id, ignore_contract_id=None):
    conn = get_db()
    if ignore_contract_id:
        row = conn.execute(
            'SELECT 1 FROM contratos WHERE ponto_id = ? AND status = ? AND id != ?',
            (ponto_id, 'ATIVO', ignore_contract_id)
        ).fetchone()
    else:
        row = conn.execute('SELECT 1 FROM contratos WHERE ponto_id = ? AND status = ?', (ponto_id, 'ATIVO')).fetchone()
    conn.close()
    return bool(row)


def update_ponto_status_from_contracts(ponto_id):
    conn = get_db()
    active = conn.execute('SELECT 1 FROM contratos WHERE ponto_id = ? AND status = ?', (ponto_id, 'ATIVO')).fetchone()
    new_status = 'OCUPADO' if active else 'DISPONIVEL'
    conn.execute('UPDATE pontos SET status = ? WHERE id = ?', (new_status, ponto_id))
    conn.commit()
    conn.close()
    return new_status

# Auth helpers
def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        if 'Authorization' in request.headers:
            auth = request.headers.get('Authorization')
            if auth and auth.startswith('Bearer '):
                token = auth.split(' ')[1]
        if not token:
            return jsonify({'error': 'Token is missing'}), 401
        try:
            data = jwt.decode(token, JWT_SECRET, algorithms=['HS256'])
            user_id = data.get('sub')
            conn = get_db()
            user = conn.execute('SELECT id, email, role, active FROM users WHERE id = ?', (user_id,)).fetchone()
            conn.close()
            if not user or not user['active']:
                return jsonify({'error': 'User not found or inactive'}), 401
            request.user = dict(user)
        except Exception as e:
            return jsonify({'error': 'Token invalid', 'details': str(e)}), 401
        return f(*args, **kwargs)
    return decorated

@app.route('/api/auth/register', methods=['POST'])
def register():
    data = request.get_json() or {}
    email = data.get('email')
    password = data.get('password')
    if not email or not password:
        return jsonify({'error': 'Email and password required'}), 400
    conn = get_db()
    cur = conn.cursor()
    try:
        pw_hash = generate_password_hash(password)
        cur.execute('INSERT INTO users (email, password_hash, role, active) VALUES (?, ?, ?, ?)', (email, pw_hash, 'admin', 1))
        conn.commit()
        uid = cur.lastrowid
        return jsonify({'id': uid, 'email': email}), 200
    except sqlite3.IntegrityError:
        return jsonify({'error': 'User already exists'}), 400
    finally:
        conn.close()

@app.route('/api/auth/login', methods=['POST'])
def login():
    data = request.get_json() or {}
    email = data.get('email')
    password = data.get('password')
    if not email or not password:
        return jsonify({'error': 'Email and password required'}), 400
    conn = get_db()
    user = conn.execute('SELECT id, email, password_hash, role, active FROM users WHERE email = ?', (email,)).fetchone()
    conn.close()
    if not user:
        return jsonify({'error': 'Invalid credentials'}), 401
    if not check_password_hash(user['password_hash'], password):
        return jsonify({'error': 'Invalid credentials'}), 401
    token = jwt.encode({'sub': user['id'], 'email': user['email'], 'role': user['role'], 'exp': datetime.datetime.utcnow() + datetime.timedelta(days=7)}, JWT_SECRET, algorithm='HS256')
    return jsonify({'token': token})

# Collaborator endpoints
@app.route('/api/collaborators', methods=['GET'])
@token_required
def list_collaborators():
    conn = get_db()
    rows = conn.execute('SELECT id, email, role, active, created_at FROM colaboradores ORDER BY created_at DESC').fetchall()
    conn.close()
    data = [dict(r) for r in rows]
    return jsonify(data)

@app.route('/api/collaborators', methods=['POST'])
@token_required
def add_collaborator():
    body = request.get_json() or {}
    email = body.get('email')
    role = body.get('role') or 'colaborador'
    if not email:
        return jsonify({'error': 'Email required'}), 400
    conn = get_db()
    cur = conn.cursor()
    try:
        cur.execute('INSERT INTO colaboradores (email, role, active) VALUES (?, ?, ?)', (email, role, 1))
        conn.commit()
        cid = cur.lastrowid
        created = conn.execute('SELECT id, email, role, active, created_at FROM colaboradores WHERE id = ?', (cid,)).fetchone()
        return jsonify(dict(created))
    except sqlite3.IntegrityError:
        return jsonify({'error': 'Colaborador already exists'}), 400
    finally:
        conn.close()

@app.route('/api/collaborators/<int:cid>/active', methods=['PUT'])
@token_required
def toggle_collaborator_active(cid):
    body = request.get_json() or {}
    active = 1 if body.get('active') else 0
    conn = get_db()
    conn.execute('UPDATE colaboradores SET active = ? WHERE id = ?', (active, cid))
    conn.commit()
    updated = conn.execute('SELECT id, email, role, active, created_at FROM colaboradores WHERE id = ?', (cid,)).fetchone()
    conn.close()
    if not updated:
        return jsonify({'error': 'Not found'}), 404
    return jsonify(dict(updated))

# Serve static (optional)
@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def serve(path):
    static_dir = app.static_folder
    if path and (Path(static_dir) / path).exists():
        return send_from_directory(static_dir, path)
    index = Path(static_dir) / 'index.html'
    if index.exists():
        return send_from_directory(static_dir, 'index.html')
    return jsonify({'status': 'Flask server running'})

# Register API blueprints (must be done AFTER utility functions are defined to avoid circular imports)
from .routes.clients import bp as clients_bp
from .routes.contracts import bp as contracts_bp
from .routes.pontos import bp as pontos_bp
from .routes.proprietarios import bp as proprietarios_bp

app.register_blueprint(clients_bp, url_prefix='/api/clients')
app.register_blueprint(contracts_bp, url_prefix='/api/contracts')
app.register_blueprint(pontos_bp, url_prefix='/api/pontos')
app.register_blueprint(proprietarios_bp, url_prefix='/api/proprietarios')

if __name__ == '__main__':
    init_db()
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)), debug=True)
