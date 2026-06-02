from flask import Blueprint, request, jsonify
from ..app import get_db, token_required, row_exists

bp = Blueprint('proprietarios', __name__)

_FIELDS = 'id, nome, documento, telefone, email, cep, logradouro, numero, complemento, bairro, cidade, estado, banco_nome, banco_agencia, banco_conta, banco_tipo, banco_pix, created_at'

@bp.route('/', methods=['GET'])
@token_required
def list_proprietarios():
    conn = get_db()
    rows = conn.execute(f'SELECT {_FIELDS} FROM proprietarios ORDER BY created_at DESC').fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])

@bp.route('/', methods=['POST'])
@token_required
def add_proprietario():
    data = request.get_json() or {}
    nome = data.get('nome')
    if not nome:
        return jsonify({'error': 'Nome required'}), 400
    conn = get_db()
    cur = conn.cursor()
    cur.execute('''INSERT INTO proprietarios
        (nome, documento, telefone, email, cep, logradouro, numero, complemento, bairro, cidade, estado,
         banco_nome, banco_agencia, banco_conta, banco_tipo, banco_pix)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)''',
        (nome, data.get('documento'), data.get('telefone'), data.get('email'),
         data.get('cep'), data.get('logradouro'), data.get('numero'), data.get('complemento'),
         data.get('bairro'), data.get('cidade'), data.get('estado'),
         data.get('banco_nome'), data.get('banco_agencia'), data.get('banco_conta'),
         data.get('banco_tipo'), data.get('banco_pix')))
    conn.commit()
    pid = cur.lastrowid
    created = conn.execute(f'SELECT {_FIELDS} FROM proprietarios WHERE id = ?', (pid,)).fetchone()
    conn.close()
    return jsonify(dict(created))

@bp.route('/<int:pid>', methods=['GET'])
@token_required
def get_proprietario(pid):
    conn = get_db()
    row = conn.execute(f'SELECT {_FIELDS} FROM proprietarios WHERE id = ?', (pid,)).fetchone()
    conn.close()
    if not row:
        return jsonify({'error': 'Proprietário not found'}), 404
    return jsonify(dict(row))

@bp.route('/<int:pid>', methods=['PUT'])
@token_required
def update_proprietario(pid):
    data = request.get_json() or {}
    if not row_exists('proprietarios', pid):
        return jsonify({'error': 'Proprietário not found'}), 404
    conn = get_db()
    conn.execute('''UPDATE proprietarios SET
        nome=?, documento=?, telefone=?, email=?,
        cep=?, logradouro=?, numero=?, complemento=?, bairro=?, cidade=?, estado=?,
        banco_nome=?, banco_agencia=?, banco_conta=?, banco_tipo=?, banco_pix=?
        WHERE id=?''',
        (data.get('nome'), data.get('documento'), data.get('telefone'), data.get('email'),
         data.get('cep'), data.get('logradouro'), data.get('numero'), data.get('complemento'),
         data.get('bairro'), data.get('cidade'), data.get('estado'),
         data.get('banco_nome'), data.get('banco_agencia'), data.get('banco_conta'),
         data.get('banco_tipo'), data.get('banco_pix'), pid))
    conn.commit()
    updated = conn.execute(f'SELECT {_FIELDS} FROM proprietarios WHERE id = ?', (pid,)).fetchone()
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
