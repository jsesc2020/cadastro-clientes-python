from flask import Blueprint, request, jsonify
from ..app import get_db, token_required, row_exists

bp = Blueprint('pontos', __name__)

@bp.route('/', methods=['GET'])
@token_required
def list_pontos():
    conn = get_db()
    rows = conn.execute('SELECT id, nome, tipo, endereco, latitude, longitude, status, created_at FROM pontos ORDER BY created_at DESC').fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])

@bp.route('/', methods=['POST'])
@token_required
def add_ponto():
    data = request.get_json() or {}
    nome = data.get('nome')
    tipo = data.get('tipo') or 'OUTDOOR'
    endereco = data.get('endereco')
    latitude = data.get('latitude')
    longitude = data.get('longitude')
    status = data.get('status') or 'DISPONIVEL'
    proprietario_id = data.get('proprietario_id')
    if not nome or latitude is None or longitude is None:
        return jsonify({'error': 'nome, latitude and longitude required'}), 400
    if proprietario_id and not row_exists('proprietarios', proprietario_id):
        return jsonify({'error': 'Proprietário not found'}), 400
    conn = get_db()
    cur = conn.cursor()
    cur.execute('INSERT INTO pontos (nome, tipo, endereco, latitude, longitude, status, proprietario_id) VALUES (?, ?, ?, ?, ?, ?, ?)', (nome, tipo, endereco, latitude, longitude, status, proprietario_id))
    conn.commit()
    pid = cur.lastrowid
    created = conn.execute('SELECT id, nome, tipo, endereco, latitude, longitude, status, proprietario_id, created_at FROM pontos WHERE id = ?', (pid,)).fetchone()
    conn.close()
    return jsonify(dict(created))

@bp.route('/<int:pid>', methods=['GET'])
@token_required
def get_ponto(pid):
    conn = get_db()
    row = conn.execute('SELECT id, nome, tipo, endereco, latitude, longitude, status, proprietario_id, created_at FROM pontos WHERE id = ?', (pid,)).fetchone()
    conn.close()
    if not row:
        return jsonify({'error': 'Ponto not found'}), 404
    return jsonify(dict(row))

@bp.route('/<int:pid>', methods=['PUT'])
@token_required
def update_ponto(pid):
    data = request.get_json() or {}
    nome = data.get('nome')
    tipo = data.get('tipo')
    endereco = data.get('endereco')
    latitude = data.get('latitude')
    longitude = data.get('longitude')
    status = data.get('status')
    proprietario_id = data.get('proprietario_id')
    if proprietario_id and not row_exists('proprietarios', proprietario_id):
        return jsonify({'error': 'Proprietário not found'}), 400
    if not row_exists('pontos', pid):
        return jsonify({'error': 'Ponto not found'}), 404
    conn = get_db()
    conn.execute('UPDATE pontos SET nome = ?, tipo = ?, endereco = ?, latitude = ?, longitude = ?, status = ?, proprietario_id = ? WHERE id = ?', (nome, tipo, endereco, latitude, longitude, status, proprietario_id, pid))
    conn.commit()
    updated = conn.execute('SELECT id, nome, tipo, endereco, latitude, longitude, status, proprietario_id, created_at FROM pontos WHERE id = ?', (pid,)).fetchone()
    conn.close()
    return jsonify(dict(updated))

@bp.route('/<int:pid>', methods=['DELETE'])
@token_required
def delete_ponto(pid):
    if not row_exists('pontos', pid):
        return jsonify({'error': 'Ponto not found'}), 404
    conn = get_db()
    conn.execute('DELETE FROM pontos WHERE id = ?', (pid,))
    conn.commit()
    conn.close()
    return jsonify({'deleted': pid})

@bp.route('/<int:pid>/status', methods=['PUT'])
@token_required
def update_status(pid):
    data = request.get_json() or {}
    status = data.get('status')
    if not status:
        return jsonify({'error': 'status required'}), 400
    if not row_exists('pontos', pid):
        return jsonify({'error': 'Ponto not found'}), 404
    conn = get_db()
    conn.execute('UPDATE pontos SET status = ? WHERE id = ?', (status, pid))
    conn.commit()
    updated = conn.execute('SELECT id, nome, tipo, endereco, latitude, longitude, status, proprietario_id, created_at FROM pontos WHERE id = ?', (pid,)).fetchone()
    conn.close()
    return jsonify(dict(updated))
