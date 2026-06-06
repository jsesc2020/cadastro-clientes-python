from flask import Blueprint, request, jsonify
from ..app import get_db, token_required, row_exists

bp = Blueprint('proprietarios', __name__)
_F = '''id,nome,documento,tipo_pessoa,telefone,email,
    cep,logradouro,numero,complemento,bairro,cidade,estado,
    banco_nome,banco_agencia,banco_conta,banco_tipo,banco_pix,created_at'''

@bp.route('/', methods=['GET'])
@token_required
def list_proprietarios():
    conn = get_db()
    rows = conn.execute(f'SELECT {_F} FROM proprietarios ORDER BY created_at DESC').fetchall()
    conn.close(); return jsonify([dict(r) for r in rows])

@bp.route('/', methods=['POST'])
@token_required
def add_proprietario():
    d = request.get_json() or {}
    if not d.get('nome'): return jsonify({'error':'Nome required'}),400
    conn = get_db(); cur = conn.cursor()
    cur.execute('''INSERT INTO proprietarios
        (nome,documento,tipo_pessoa,telefone,email,
         cep,logradouro,numero,complemento,bairro,cidade,estado,
         banco_nome,banco_agencia,banco_conta,banco_tipo,banco_pix)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)''',
        (d.get('nome'),d.get('documento'),d.get('tipo_pessoa','PF'),
         d.get('telefone'),d.get('email'),
         d.get('cep'),d.get('logradouro'),d.get('numero'),d.get('complemento'),
         d.get('bairro'),d.get('cidade'),d.get('estado'),
         d.get('banco_nome'),d.get('banco_agencia'),d.get('banco_conta'),
         d.get('banco_tipo'),d.get('banco_pix')))
    conn.commit(); pid = cur.lastrowid
    row = conn.execute(f'SELECT {_F} FROM proprietarios WHERE id=?',(pid,)).fetchone()
    conn.close(); return jsonify(dict(row))

@bp.route('/<int:pid>', methods=['PUT'])
@token_required
def update_proprietario(pid):
    if not row_exists('proprietarios',pid): return jsonify({'error':'Not found'}),404
    d = request.get_json() or {}
    conn = get_db()
    conn.execute('''UPDATE proprietarios SET
        nome=?,documento=?,tipo_pessoa=?,telefone=?,email=?,
        cep=?,logradouro=?,numero=?,complemento=?,bairro=?,cidade=?,estado=?,
        banco_nome=?,banco_agencia=?,banco_conta=?,banco_tipo=?,banco_pix=?
        WHERE id=?''',
        (d.get('nome'),d.get('documento'),d.get('tipo_pessoa','PF'),
         d.get('telefone'),d.get('email'),
         d.get('cep'),d.get('logradouro'),d.get('numero'),d.get('complemento'),
         d.get('bairro'),d.get('cidade'),d.get('estado'),
         d.get('banco_nome'),d.get('banco_agencia'),d.get('banco_conta'),
         d.get('banco_tipo'),d.get('banco_pix'),pid))
    conn.commit()
    row = conn.execute(f'SELECT {_F} FROM proprietarios WHERE id=?',(pid,)).fetchone()
    conn.close(); return jsonify(dict(row))

@bp.route('/<int:pid>', methods=['DELETE'])
@token_required
def delete_proprietario(pid):
    if not row_exists('proprietarios',pid): return jsonify({'error':'Not found'}),404
    conn = get_db()
    conn.execute('DELETE FROM proprietarios WHERE id=?',(pid,))
    conn.commit(); conn.close()
    return jsonify({'deleted':pid})
