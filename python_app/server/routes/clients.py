from flask import Blueprint, request, jsonify
from ..app import get_db, token_required, row_exists

bp = Blueprint('clients', __name__)

@bp.route('/', methods=['GET'])
@token_required
def list_clients():
    conn = get_db()
    rows = conn.execute('SELECT id, nome, documento, telefone, email, created_at FROM clientes ORDER BY created_at DESC').fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])

@bp.route('/', methods=['POST'])
@token_required
def add_client():
    data = request.get_json() or {}
    nome = data.get('nome')
    documento = data.get('documento')
    telefone = data.get('telefone')
    email = data.get('email')
    if not nome:
        return jsonify({'error': 'Nome required'}), 400
    conn = get_db()
    cur = conn.cursor()
    cur.execute('INSERT INTO clientes (nome, documento, telefone, email) VALUES (?, ?, ?, ?)', (nome, documento, telefone, email))
    conn.commit()
    cid = cur.lastrowid
    created = conn.execute('SELECT id, nome, documento, telefone, email, created_at FROM clientes WHERE id = ?', (cid,)).fetchone()
    conn.close()
    return jsonify(dict(created))

@bp.route('/<int:cid>', methods=['GET'])
@token_required
def get_client(cid):
    conn = get_db()
    row = conn.execute('SELECT id, nome, documento, telefone, email, created_at FROM clientes WHERE id = ?', (cid,)).fetchone()
    conn.close()
    if not row:
        return jsonify({'error': 'Cliente not found'}), 404
    return jsonify(dict(row))

@bp.route('/<int:cid>', methods=['PUT'])
@token_required
def update_client(cid):
    data = request.get_json() or {}
    nome = data.get('nome')
    documento = data.get('documento')
    telefone = data.get('telefone')
    email = data.get('email')
    if not row_exists('clientes', cid):
        return jsonify({'error': 'Cliente not found'}), 404
    conn = get_db()
    conn.execute('UPDATE clientes SET nome = ?, documento = ?, telefone = ?, email = ? WHERE id = ?', (nome, documento, telefone, email, cid))
    conn.commit()
    updated = conn.execute('SELECT id, nome, documento, telefone, email, created_at FROM clientes WHERE id = ?', (cid,)).fetchone()
    conn.close()
    return jsonify(dict(updated))

@bp.route('/<int:cid>', methods=['DELETE'])
@token_required
def delete_client(cid):
    if not row_exists('clientes', cid):
        return jsonify({'error': 'Cliente not found'}), 404
    conn = get_db()
    conn.execute('DELETE FROM clientes WHERE id = ?', (cid,))
    conn.commit()
    conn.close()
    return jsonify({'deleted': cid})
