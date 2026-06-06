from flask import Blueprint, request, jsonify
from ..app import get_db, token_required, row_exists, ponto_has_active_contract, update_ponto_status_from_contracts, gerar_lancamentos_contrato
import datetime

bp = Blueprint('contracts', __name__)

_F = '''id, cliente_id, ponto_id, valor_cents, repasse_percent, repasse_cents,
    tipo_repasse, status, data_inicio, data_termino, observacoes, created_at'''

@bp.route('/', methods=['GET'])
@token_required
def list_contracts():
    conn = get_db()
    rows = conn.execute(f'SELECT {_F} FROM contratos ORDER BY created_at DESC').fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])

@bp.route('/', methods=['POST'])
@token_required
def add_contract():
    d = request.get_json() or {}
    cliente_id = d.get('cliente_id')
    ponto_id   = d.get('ponto_id')
    if not cliente_id or not ponto_id:
        return jsonify({'error': 'cliente_id and ponto_id required'}), 400
    if not row_exists('clientes', cliente_id):
        return jsonify({'error': 'Cliente not found'}), 404
    if not row_exists('pontos', ponto_id):
        return jsonify({'error': 'Ponto not found'}), 404
    if ponto_has_active_contract(ponto_id):
        return jsonify({'error': 'Ponto already has an active contract'}), 400

    valor_cents     = int(d.get('valor_cents') or 0)
    repasse_percent = float(d.get('repasse_percent') or 0)
    repasse_cents   = int(d.get('repasse_cents') or round(valor_cents * repasse_percent / 100))
    tipo_repasse    = d.get('tipo_repasse') or 'DINHEIRO'

    conn = get_db(); cur = conn.cursor()
    cur.execute('''INSERT INTO contratos
        (cliente_id, ponto_id, valor_cents, repasse_percent, repasse_cents,
         tipo_repasse, status, data_inicio, data_termino, observacoes)
        VALUES (?,?,?,?,?,?,?,?,?,?)''',
        (cliente_id, ponto_id, valor_cents, repasse_percent, repasse_cents,
         tipo_repasse, 'ATIVO',
         d.get('data_inicio'), d.get('data_termino'), d.get('observacoes')))
    conn.commit()
    cid = cur.lastrowid
    update_ponto_status_from_contracts(ponto_id)
    gerar_lancamentos_contrato(cid, conn)
    conn.commit()
    row = conn.execute(f'SELECT {_F} FROM contratos WHERE id=?', (cid,)).fetchone()
    conn.close()
    return jsonify(dict(row))

@bp.route('/<int:cid>', methods=['PUT'])
@token_required
def update_contract(cid):
    if not row_exists('contratos', cid):
        return jsonify({'error': 'Contract not found'}), 404
    d = request.get_json() or {}
    valor_cents     = int(d.get('valor_cents') or 0)
    repasse_percent = float(d.get('repasse_percent') or 0)
    repasse_cents   = int(d.get('repasse_cents') or round(valor_cents * repasse_percent / 100))
    conn = get_db()
    conn.execute('''UPDATE contratos SET
        valor_cents=?, repasse_percent=?, repasse_cents=?,
        tipo_repasse=?, data_inicio=?, data_termino=?,
        observacoes=?, status=COALESCE(?,status)
        WHERE id=?''',
        (valor_cents, repasse_percent, repasse_cents,
         d.get('tipo_repasse','DINHEIRO'),
         d.get('data_inicio'), d.get('data_termino'),
         d.get('observacoes'), d.get('status'), cid))
    conn.commit()
    row = conn.execute(f'SELECT {_F} FROM contratos WHERE id=?', (cid,)).fetchone()
    conn.close()
    return jsonify(dict(row))

@bp.route('/<int:cid>/cancel', methods=['POST'])
@token_required
def cancel_contract(cid):
    conn = get_db()
    row = conn.execute('SELECT ponto_id, status FROM contratos WHERE id=?', (cid,)).fetchone()
    if not row: conn.close(); return jsonify({'error': 'Not found'}), 404
    if row['status'] == 'CANCELADO':
        conn.close(); return jsonify({'error': 'Already cancelled'}), 400
    conn.execute("UPDATE contratos SET status='CANCELADO' WHERE id=?", (cid,))
    conn.commit()
    update_ponto_status_from_contracts(row['ponto_id'])
    updated = conn.execute(f'SELECT {_F} FROM contratos WHERE id=?', (cid,)).fetchone()
    conn.close()
    return jsonify(dict(updated))

@bp.route('/<int:cid>/renew', methods=['POST'])
@token_required
def renew_contract(cid):
    d = request.get_json() or {}
    data_termino = d.get('data_termino')
    if not data_termino: return jsonify({'error': 'data_termino required'}), 400
    conn = get_db()
    row = conn.execute('SELECT ponto_id, status FROM contratos WHERE id=?', (cid,)).fetchone()
    if not row: conn.close(); return jsonify({'error': 'Not found'}), 404
    if ponto_has_active_contract(row['ponto_id'], ignore_contract_id=cid):
        conn.close(); return jsonify({'error': 'Ponto already has another active contract'}), 400
    conn.execute("UPDATE contratos SET status='ATIVO', data_termino=? WHERE id=?",
                 (data_termino, cid))
    conn.commit()
    update_ponto_status_from_contracts(row['ponto_id'])
    gerar_lancamentos_contrato(cid, conn)
    conn.commit()
    updated = conn.execute(f'SELECT {_F} FROM contratos WHERE id=?', (cid,)).fetchone()
    conn.close()
    return jsonify(dict(updated))
