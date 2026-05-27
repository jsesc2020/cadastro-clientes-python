from flask import Blueprint, request, jsonify
from ..app import get_db, row_exists, token_required, ponto_has_active_contract, update_ponto_status_from_contracts

bp = Blueprint('contracts', __name__)

VALID_STATUSES = {'ATIVO', 'CANCELADO', 'FINALIZADO', 'PENDENTE'}

def build_contract(contract_row):
    return dict(contract_row)

@bp.route('/', methods=['GET'])
@token_required
def list_contracts():
    conn = get_db()
    rows = conn.execute(
        'SELECT id, cliente_id, ponto_id, valor_cents, status, data_inicio, data_termino, created_at FROM contratos ORDER BY created_at DESC'
    ).fetchall()
    conn.close()
    return jsonify([build_contract(r) for r in rows])

@bp.route('/<int:cid>', methods=['GET'])
@token_required
def get_contract(cid):
    conn = get_db()
    row = conn.execute(
        'SELECT id, cliente_id, ponto_id, valor_cents, status, data_inicio, data_termino, created_at FROM contratos WHERE id = ?',
        (cid,)
    ).fetchone()
    conn.close()
    if not row:
        return jsonify({'error': 'Contract not found'}), 404
    return jsonify(build_contract(row))

@bp.route('/', methods=['POST'])
@token_required
def add_contract():
    data = request.get_json() or {}
    cliente_id = data.get('cliente_id')
    ponto_id = data.get('ponto_id')
    valor_cents = data.get('valor_cents') or 0
    data_inicio = data.get('data_inicio')
    data_termino = data.get('data_termino')
    status = data.get('status') or 'ATIVO'
    if not cliente_id or not ponto_id:
        return jsonify({'error': 'cliente_id and ponto_id required'}), 400
    if status not in VALID_STATUSES:
        return jsonify({'error': 'Invalid status'}), 400
    if not row_exists('clientes', cliente_id):
        return jsonify({'error': 'Cliente not found'}), 400
    if not row_exists('pontos', ponto_id):
        return jsonify({'error': 'Ponto not found'}), 400
    if status == 'ATIVO' and ponto_has_active_contract(ponto_id):
        return jsonify({'error': 'Ponto already has an active contract'}), 400
    conn = get_db()
    cur = conn.cursor()
    cur.execute(
        'INSERT INTO contratos (cliente_id, ponto_id, valor_cents, status, data_inicio, data_termino) VALUES (?, ?, ?, ?, ?, ?)',
        (cliente_id, ponto_id, valor_cents, status, data_inicio, data_termino)
    )
    conn.commit()
    cid = cur.lastrowid
    created = conn.execute(
        'SELECT id, cliente_id, ponto_id, valor_cents, status, data_inicio, data_termino, created_at FROM contratos WHERE id = ?',
        (cid,)
    ).fetchone()
    if status == 'ATIVO':
        update_ponto_status_from_contracts(ponto_id)
    conn.close()
    return jsonify(build_contract(created))

@bp.route('/<int:cid>', methods=['PUT'])
@token_required
def update_contract(cid):
    if not row_exists('contratos', cid):
        return jsonify({'error': 'Contract not found'}), 404
    data = request.get_json() or {}
    valor_cents = data.get('valor_cents')
    data_inicio = data.get('data_inicio')
    data_termino = data.get('data_termino')
    status = data.get('status')
    if status and status not in VALID_STATUSES:
        return jsonify({'error': 'Invalid status'}), 400
    conn = get_db()
    current = conn.execute('SELECT ponto_id, status FROM contratos WHERE id = ?', (cid,)).fetchone()
    ponto_id = current['ponto_id']
    current_status = current['status']
    if status == 'ATIVO' and ponto_has_active_contract(ponto_id, ignore_contract_id=cid):
        conn.close()
        return jsonify({'error': 'Ponto already has an active contract'}), 400
    conn.execute(
        'UPDATE contratos SET valor_cents = COALESCE(?, valor_cents), data_inicio = COALESCE(?, data_inicio), data_termino = COALESCE(?, data_termino), status = COALESCE(?, status) WHERE id = ?',
        (valor_cents, data_inicio, data_termino, status, cid)
    )
    conn.commit()
    if current_status != 'ATIVO' and status == 'ATIVO':
        update_ponto_status_from_contracts(ponto_id)
    if current_status == 'ATIVO' and status and status != 'ATIVO':
        update_ponto_status_from_contracts(ponto_id)
    updated = conn.execute(
        'SELECT id, cliente_id, ponto_id, valor_cents, status, data_inicio, data_termino, created_at FROM contratos WHERE id = ?',
        (cid,)
    ).fetchone()
    conn.close()
    return jsonify(build_contract(updated))

@bp.route('/<int:cid>/status', methods=['PUT'])
@token_required
def change_contract_status(cid):
    if not row_exists('contratos', cid):
        return jsonify({'error': 'Contract not found'}), 404
    data = request.get_json() or {}
    status = data.get('status')
    if not status or status not in VALID_STATUSES:
        return jsonify({'error': 'Invalid status'}), 400
    conn = get_db()
    current = conn.execute('SELECT ponto_id, status FROM contratos WHERE id = ?', (cid,)).fetchone()
    ponto_id = current['ponto_id']
    if status == 'ATIVO' and ponto_has_active_contract(ponto_id, ignore_contract_id=cid):
        conn.close()
        return jsonify({'error': 'Ponto already has an active contract'}), 400
    conn.execute('UPDATE contratos SET status = ? WHERE id = ?', (status, cid))
    conn.commit()
    update_ponto_status_from_contracts(ponto_id)
    updated = conn.execute('SELECT id, cliente_id, ponto_id, valor_cents, status, data_inicio, data_termino, created_at FROM contratos WHERE id = ?', (cid,)).fetchone()
    conn.close()
    return jsonify(build_contract(updated))

@bp.route('/<int:cid>/cancel', methods=['POST'])
@token_required
def cancel_contract(cid):
    if not row_exists('contratos', cid):
        return jsonify({'error': 'Contract not found'}), 404
    conn = get_db()
    current = conn.execute('SELECT ponto_id FROM contratos WHERE id = ?', (cid,)).fetchone()
    ponto_id = current['ponto_id']
    conn.execute('UPDATE contratos SET status = ? WHERE id = ?', ('CANCELADO', cid))
    conn.commit()
    update_ponto_status_from_contracts(ponto_id)
    cancelled = conn.execute('SELECT id, cliente_id, ponto_id, valor_cents, status, data_inicio, data_termino, created_at FROM contratos WHERE id = ?', (cid,)).fetchone()
    conn.close()
    return jsonify(build_contract(cancelled))

@bp.route('/<int:cid>/renew', methods=['POST'])
@token_required
def renew_contract(cid):
    if not row_exists('contratos', cid):
        return jsonify({'error': 'Contract not found'}), 404
    data = request.get_json() or {}
    data_termino = data.get('data_termino')
    if not data_termino:
        return jsonify({'error': 'data_termino required to renew'}), 400
    conn = get_db()
    current = conn.execute('SELECT cliente_id, ponto_id, status FROM contratos WHERE id = ?', (cid,)).fetchone()
    cliente_id = current['cliente_id']
    ponto_id = current['ponto_id']
    if ponto_has_active_contract(ponto_id, ignore_contract_id=cid):
        conn.close()
        return jsonify({'error': 'Ponto already has an active contract'}), 400
    conn.execute('UPDATE contratos SET status = ?, data_termino = ? WHERE id = ?', ('ATIVO', data_termino, cid))
    conn.commit()
    update_ponto_status_from_contracts(ponto_id)
    renewed = conn.execute('SELECT id, cliente_id, ponto_id, valor_cents, status, data_inicio, data_termino, created_at FROM contratos WHERE id = ?', (cid,)).fetchone()
    conn.close()
    return jsonify(build_contract(renewed))
