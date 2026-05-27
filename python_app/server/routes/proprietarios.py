from flask import Blueprint, request, jsonify
from ..app import get_db, token_required, row_exists

bp = Blueprint('proprietarios', __name__)

@bp.route('/', methods=['GET'])
@token_required
def list_proprietarios():
    conn = get_db()
    rows = conn.execute('SELECT id, nome, documento, telefone, email, created_at FROM proprietarios ORDER BY created_at DESC').fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])

@bp.route('/', methods=['POST'])
@token_required
def add_proprietario():
    data = request.get_json() or {}
    nome = data.get('nome')
    documento = data.get('documento')
    telefone = data.get('telefone')
    email = data.get('email')
    if not nome:
        return jsonify({'error': 'Nome required'}), 400
    conn = get_db()
    cur = conn.cursor()
    cur.execute('INSERT INTO proprietarios (nome, documento, telefone, email) VALUES (?, ?, ?, ?)', (nome, documento, telefone, email))
    conn.commit()
    pid = cur.lastrowid
    created = conn.execute('SELECT id, nome, documento, telefone, email, created_at FROM proprietarios WHERE id = ?', (pid,)).fetchone()
    conn.close()
    return jsonify(dict(created))

@bp.route('/<int:pid>', methods=['GET'])
@token_required
def get_proprietario(pid):
    conn = get_db()
    row = conn.execute('SELECT id, nome, documento, telefone, email, created_at FROM proprietarios WHERE id = ?', (pid,)).fetchone()
    conn.close()
    if not row:
        return jsonify({'error': 'Proprietário not found'}), 404
    return jsonify(dict(row))

@bp.route('/<int:pid>', methods=['PUT'])
@token_required
def update_proprietario(pid):
    data = request.get_json() or {}
    nome = data.get('nome')
    documento = data.get('documento')
    telefone = data.get('telefone')
    email = data.get('email')
    if not row_exists('proprietarios', pid):
        return jsonify({'error': 'Proprietário not found'}), 404
    conn = get_db()
    conn.execute('UPDATE proprietarios SET nome = ?, documento = ?, telefone = ?, email = ? WHERE id = ?', (nome, documento, telefone, email, pid))
    conn.commit()
    updated = conn.execute('SELECT id, nome, documento, telefone, email, created_at FROM proprietarios WHERE id = ?', (pid,)).fetchone()
    conn.close()
    return jsonify(dict(updated))

@bp.route('/<int:pid>', methods=['DELETE'])
@token_required
def delete_proprietario(pid):
    if not row_exists('proprietarios', pid):
        return jsonify({'error': 'Proprietário not found'}), 404
    conn = get_db()
    conn.execute('DELETE FROM proprietarios WHERE id = ?', (pid,))
    conn.commit()
    conn.close()
    return jsonify({'deleted': pid})
