from flask import Blueprint, request, jsonify
from ..app import get_db, token_required, row_exists

bp = Blueprint('pontos', __name__)
_F = '''id,nome,tipo,cep,logradouro,numero,complemento,bairro,cidade,estado,
    endereco,latitude,longitude,status,proprietario_id,created_at'''

@bp.route('/', methods=['GET'])
@token_required
def list_pontos():
    conn = get_db()
    rows = conn.execute(f'SELECT {_F} FROM pontos ORDER BY created_at DESC').fetchall()
    conn.close(); return jsonify([dict(r) for r in rows])

@bp.route('/', methods=['POST'])
@token_required
def add_ponto():
    d = request.get_json() or {}
    nome = d.get('nome')
    lat  = d.get('latitude')
    lng  = d.get('longitude')
    if not nome:
        return jsonify({'error':'Nome obrigatorio'}),400
    prop_id = d.get('proprietario_id')
    if prop_id and not row_exists('proprietarios', prop_id):
        return jsonify({'error':'Proprietario not found'}),400
    partes  = [d.get('logradouro'),d.get('numero'),d.get('bairro'),d.get('cidade'),d.get('estado')]
    endereco = ', '.join(p for p in partes if p) or d.get('endereco') or ''
    conn = get_db(); cur = conn.cursor()
    cur.execute('''INSERT INTO pontos
        (nome,tipo,cep,logradouro,numero,complemento,bairro,cidade,estado,
         endereco,latitude,longitude,status,proprietario_id)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)''',
        (nome, d.get('tipo','OUTDOOR'),
         d.get('cep'),d.get('logradouro'),d.get('numero'),d.get('complemento'),
         d.get('bairro'),d.get('cidade'),d.get('estado'),
         endereco, lat, lng, d.get('status','DISPONIVEL'), prop_id))
    conn.commit(); pid = cur.lastrowid
    row = conn.execute(f'SELECT {_F} FROM pontos WHERE id=?',(pid,)).fetchone()
    conn.close(); return jsonify(dict(row))

@bp.route('/<int:pid>', methods=['PUT'])
@token_required
def update_ponto(pid):
    if not row_exists('pontos',pid): return jsonify({'error':'Not found'}),404
    d = request.get_json() or {}
    prop_id = d.get('proprietario_id')
    if prop_id and not row_exists('proprietarios', prop_id):
        return jsonify({'error':'Proprietario not found'}),400
    partes  = [d.get('logradouro'),d.get('numero'),d.get('bairro'),d.get('cidade'),d.get('estado')]
    endereco = ', '.join(p for p in partes if p) or d.get('endereco') or ''
    conn = get_db()
    conn.execute('''UPDATE pontos SET
        nome=?,tipo=?,cep=?,logradouro=?,numero=?,complemento=?,
        bairro=?,cidade=?,estado=?,endereco=?,
        latitude=?,longitude=?,status=?,proprietario_id=?
        WHERE id=?''',
        (d.get('nome'),d.get('tipo'),
         d.get('cep'),d.get('logradouro'),d.get('numero'),d.get('complemento'),
         d.get('bairro'),d.get('cidade'),d.get('estado'),endereco,
         d.get('latitude'),d.get('longitude'),d.get('status'),prop_id,pid))
    conn.commit()
    row = conn.execute(f'SELECT {_F} FROM pontos WHERE id=?',(pid,)).fetchone()
    conn.close(); return jsonify(dict(row))

@bp.route('/<int:pid>', methods=['DELETE'])
@token_required
def delete_ponto(pid):
    if not row_exists('pontos',pid): return jsonify({'error':'Not found'}),404
    conn = get_db()
    conn.execute('DELETE FROM pontos WHERE id=?',(pid,))
    conn.commit(); conn.close()
    return jsonify({'deleted':pid})
