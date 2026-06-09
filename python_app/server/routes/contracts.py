from flask import Blueprint, request, jsonify
from ..app import get_db, token_required, row_exists, ponto_has_active_contract, update_ponto_status_from_contracts
import datetime

bp = Blueprint('contracts', __name__)

_F = '''id, cliente_id, ponto_id, proprietario_id, valor_cents, num_parcelas,
    repasse_percent, repasse_cents, tipo_repasse,
    dia_vencimento, dia_pagamento,
    status, data_inicio, data_termino, observacoes, created_at'''

def _vencimento(data_inicio_str, numero_parcela, dia):
    """Calcula a data de vencimento de uma parcela."""
    base = datetime.date.fromisoformat(data_inicio_str)
    mes  = base.month + numero_parcela - 1
    ano  = base.year + (mes - 1) // 12
    mes  = (mes - 1) % 12 + 1
    # Ajusta dia para o ultimo dia do mes se necessario
    import calendar
    ultimo = calendar.monthrange(ano, mes)[1]
    dia_real = min(dia, ultimo)
    return datetime.date(ano, mes, dia_real).isoformat()

def _gerar_parcelas(contrato_id, conn):
    """Gera todas as parcelas de recebimento (cliente) e repasse (proprietário)."""
    c = conn.execute(f'SELECT {_F} FROM contratos WHERE id=?', (contrato_id,)).fetchone()
    if not c:
        return

    # Remove parcelas PENDENTES anteriores (evita duplicar em renovacao)
    conn.execute("DELETE FROM parcelas WHERE contrato_id=? AND status='PENDENTE'", (contrato_id,))

    n           = c['num_parcelas'] or 1
    data_inicio = c['data_inicio'] or datetime.date.today().isoformat()
    dia_vec     = c['dia_vencimento'] or 25
    dia_pag     = c['dia_pagamento']  or 30

    for i in range(1, n + 1):
        # Parcela de RECEBIMENTO do locatário
        conn.execute('''INSERT INTO parcelas
            (contrato_id, tipo, numero, competencia, data_vencimento, valor_cents, status)
            VALUES (?,?,?,?,?,?,?)''',
            (contrato_id, 'RECEBIMENTO', i,
             _vencimento(data_inicio, i, 1)[:7],   # YYYY-MM
             _vencimento(data_inicio, i, dia_vec),
             c['valor_cents'], 'PENDENTE'))

        # Parcela de REPASSE ao locador (só se houver repasse em dinheiro)
        if c['tipo_repasse'] == 'DINHEIRO' and c['repasse_cents'] and c['repasse_cents'] > 0:
            conn.execute('''INSERT INTO parcelas
                (contrato_id, tipo, numero, competencia, data_vencimento, valor_cents, status)
                VALUES (?,?,?,?,?,?,?)''',
                (contrato_id, 'REPASSE', i,
                 _vencimento(data_inicio, i, 1)[:7],
                 _vencimento(data_inicio, i, dia_pag),
                 c['repasse_cents'], 'PENDENTE'))

@bp.route('/', methods=['GET'])
@token_required
def list_contracts():
    conn = get_db()
    rows = conn.execute(f'''
        SELECT c.{", c.".join(_F.replace(chr(10),"").replace(" ","").split(","))},
               cl.nome as cliente_nome,
               p.nome  as ponto_nome,
               pr.nome as proprietario_nome
        FROM contratos c
        LEFT JOIN clientes      cl ON cl.id = c.cliente_id
        LEFT JOIN pontos        p  ON p.id  = c.ponto_id
        LEFT JOIN proprietarios pr ON pr.id = c.proprietario_id
        ORDER BY c.created_at DESC''').fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])

@bp.route('/<int:cid>', methods=['GET'])
@token_required
def get_contract(cid):
    conn = get_db()
    row = conn.execute(f'SELECT {_F} FROM contratos WHERE id=?', (cid,)).fetchone()
    if not row: conn.close(); return jsonify({'error': 'Not found'}), 404
    parcelas = conn.execute(
        'SELECT * FROM parcelas WHERE contrato_id=? ORDER BY tipo, numero', (cid,)).fetchall()
    conn.close()
    data = dict(row)
    data['parcelas'] = [dict(p) for p in parcelas]
    return jsonify(data)

@bp.route('/', methods=['POST'])
@token_required
def add_contract():
    d          = request.get_json() or {}
    cliente_id = d.get('cliente_id')
    ponto_id   = d.get('ponto_id')
    if not cliente_id or not ponto_id:
        return jsonify({'error': 'cliente_id e ponto_id obrigatorios'}), 400
    if not row_exists('clientes', cliente_id):
        return jsonify({'error': 'Cliente não encontrado'}), 404
    if not row_exists('pontos', ponto_id):
        return jsonify({'error': 'Ponto não encontrado'}), 404
    if ponto_has_active_contract(ponto_id):
        return jsonify({'error': 'Ponto já possui contrato ativo'}), 400

    # Proprietário: usa o do ponto se não informado
    conn = get_db()
    prop_id = d.get('proprietario_id')
    if not prop_id:
        ponto = conn.execute('SELECT proprietario_id FROM pontos WHERE id=?', (ponto_id,)).fetchone()
        prop_id = ponto['proprietario_id'] if ponto else None

    # Configurações padrão do sistema
    def _cfg(chave, fallback):
        r = conn.execute('SELECT valor FROM config WHERE chave=?', (chave,)).fetchone()
        return int(r['valor']) if r else fallback

    valor_cents     = int(d.get('valor_cents') or 0)
    num_parcelas    = int(d.get('num_parcelas') or 1)
    repasse_percent = float(d.get('repasse_percent') or 0)
    repasse_cents   = int(d.get('repasse_cents') or round(valor_cents * repasse_percent / 100))
    tipo_repasse    = d.get('tipo_repasse') or 'DINHEIRO'
    dia_vec         = int(d.get('dia_vencimento') or _cfg('dia_vencimento_locatario', 25))
    dia_pag         = int(d.get('dia_pagamento')  or _cfg('dia_pagamento_locador',    30))
    data_inicio     = d.get('data_inicio') or datetime.date.today().isoformat()

    cur = conn.cursor()
    cur.execute('''INSERT INTO contratos
        (cliente_id, ponto_id, proprietario_id, valor_cents, num_parcelas,
         repasse_percent, repasse_cents, tipo_repasse,
         dia_vencimento, dia_pagamento,
         status, data_inicio, data_termino, observacoes)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)''',
        (cliente_id, ponto_id, prop_id, valor_cents, num_parcelas,
         repasse_percent, repasse_cents, tipo_repasse,
         dia_vec, dia_pag,
         'ATIVO', data_inicio,
         d.get('data_termino'), d.get('observacoes')))
    conn.commit()
    contrato_id = cur.lastrowid

    _gerar_parcelas(contrato_id, conn)
    conn.commit()
    update_ponto_status_from_contracts(ponto_id)

    row = conn.execute(f'SELECT {_F} FROM contratos WHERE id=?', (contrato_id,)).fetchone()
    parcelas = conn.execute(
        'SELECT * FROM parcelas WHERE contrato_id=? ORDER BY tipo, numero', (contrato_id,)).fetchall()
    conn.close()
    data = dict(row)
    data['parcelas'] = [dict(p) for p in parcelas]
    return jsonify(data)

@bp.route('/<int:cid>', methods=['PUT'])
@token_required
def update_contract(cid):
    if not row_exists('contratos', cid):
        return jsonify({'error': 'Not found'}), 404
    d   = request.get_json() or {}
    conn = get_db()
    cur  = conn.execute('SELECT * FROM contratos WHERE id=?', (cid,)).fetchone()
    ponto_id = cur['ponto_id']

    valor_cents     = int(d.get('valor_cents', cur['valor_cents']) or 0)
    num_parcelas    = int(d.get('num_parcelas', cur['num_parcelas']) or 1)
    repasse_percent = float(d.get('repasse_percent', cur['repasse_percent']) or 0)
    repasse_cents   = int(d.get('repasse_cents', cur['repasse_cents']) or round(valor_cents * repasse_percent / 100))
    tipo_repasse    = d.get('tipo_repasse', cur['tipo_repasse']) or 'DINHEIRO'
    dia_vec         = int(d.get('dia_vencimento', cur['dia_vencimento']) or 25)
    dia_pag         = int(d.get('dia_pagamento',  cur['dia_pagamento'])  or 30)

    conn.execute('''UPDATE contratos SET
        proprietario_id=?, valor_cents=?, num_parcelas=?,
        repasse_percent=?, repasse_cents=?, tipo_repasse=?,
        dia_vencimento=?, dia_pagamento=?,
        data_inicio=COALESCE(?,data_inicio),
        data_termino=COALESCE(?,data_termino),
        observacoes=COALESCE(?,observacoes),
        status=COALESCE(?,status)
        WHERE id=?''',
        (d.get('proprietario_id', cur['proprietario_id']),
         valor_cents, num_parcelas, repasse_percent, repasse_cents, tipo_repasse,
         dia_vec, dia_pag,
         d.get('data_inicio'), d.get('data_termino'),
         d.get('observacoes'), d.get('status'), cid))
    conn.commit()

    _gerar_parcelas(cid, conn)
    conn.commit()
    update_ponto_status_from_contracts(ponto_id)

    row = conn.execute(f'SELECT {_F} FROM contratos WHERE id=?', (cid,)).fetchone()
    parcelas = conn.execute('SELECT * FROM parcelas WHERE contrato_id=? ORDER BY tipo,numero',(cid,)).fetchall()
    conn.close()
    data = dict(row)
    data['parcelas'] = [dict(p) for p in parcelas]
    return jsonify(data)

@bp.route('/<int:cid>/cancel', methods=['POST'])
@token_required
def cancel_contract(cid):
    conn = get_db()
    row = conn.execute('SELECT ponto_id,status FROM contratos WHERE id=?',(cid,)).fetchone()
    if not row: conn.close(); return jsonify({'error':'Not found'}),404
    conn.execute("UPDATE contratos SET status='CANCELADO' WHERE id=?",(cid,))
    conn.execute("UPDATE parcelas SET status='CANCELADO' WHERE contrato_id=? AND status='PENDENTE'",(cid,))
    conn.commit()
    update_ponto_status_from_contracts(row['ponto_id'])
    updated = conn.execute(f'SELECT {_F} FROM contratos WHERE id=?',(cid,)).fetchone()
    conn.close()
    return jsonify(dict(updated))

@bp.route('/<int:cid>/renew', methods=['POST'])
@token_required
def renew_contract(cid):
    d = request.get_json() or {}
    num_parcelas = int(d.get('num_parcelas') or 1)
    data_inicio  = d.get('data_inicio')  # opcional: se nao informado, usa o do contrato
    data_termino = d.get('data_termino')
    if not data_termino:
        return jsonify({'error': 'data_termino obrigatoria para renovacao'}), 400
    conn = get_db()
    row = conn.execute('SELECT ponto_id FROM contratos WHERE id=?',(cid,)).fetchone()
    if not row: conn.close(); return jsonify({'error':'Not found'}),404
    if ponto_has_active_contract(row['ponto_id'], ignore_contract_id=cid):
        conn.close(); return jsonify({'error':'Ponto ja possui contrato ativo'}),400
    conn.execute('''UPDATE contratos SET
        status='ATIVO', num_parcelas=?,
        data_inicio=COALESCE(?,data_inicio),
        data_termino=COALESCE(?,data_termino)
        WHERE id=?''', (num_parcelas, data_inicio, data_termino, cid))
    conn.commit()
    _gerar_parcelas(cid, conn)
    conn.commit()
    update_ponto_status_from_contracts(row['ponto_id'])
    updated = conn.execute(f'SELECT {_F} FROM contratos WHERE id=?',(cid,)).fetchone()
    parcelas = conn.execute('SELECT * FROM parcelas WHERE contrato_id=? ORDER BY tipo,numero',(cid,)).fetchall()
    conn.close()
    data = dict(updated); data['parcelas']=[dict(p) for p in parcelas]
    return jsonify(data)

# ── Parcelas ──────────────────────────────────────────────────
@bp.route('/<int:cid>/parcelas', methods=['GET'])
@token_required
def list_parcelas(cid):
    conn = get_db()
    rows = conn.execute(
        'SELECT * FROM parcelas WHERE contrato_id=? ORDER BY tipo,numero',(cid,)).fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])

@bp.route('/parcelas/<int:pid>/pagar', methods=['POST'])
@token_required
def pagar_parcela(pid):
    d    = request.get_json() or {}
    hoje = d.get('data_pagamento') or datetime.date.today().isoformat()
    conn = get_db()
    row  = conn.execute('SELECT id,status FROM parcelas WHERE id=?',(pid,)).fetchone()
    if not row: conn.close(); return jsonify({'error':'Not found'}),404
    conn.execute("UPDATE parcelas SET status='PAGO',data_pagamento=? WHERE id=?",
                 (hoje, pid))
    conn.commit()
    updated = conn.execute('SELECT * FROM parcelas WHERE id=?',(pid,)).fetchone()
    conn.close()
    return jsonify(dict(updated))

@bp.route('/parcelas/<int:pid>', methods=['PUT'])
@token_required
def update_parcela(pid):
    d    = request.get_json() or {}
    conn = get_db()
    row  = conn.execute('SELECT * FROM parcelas WHERE id=?',(pid,)).fetchone()
    if not row: conn.close(); return jsonify({'error':'Not found'}),404
    conn.execute('''UPDATE parcelas SET
        status=COALESCE(?,status),
        data_vencimento=COALESCE(?,data_vencimento),
        data_pagamento=COALESCE(?,data_pagamento),
        valor_cents=COALESCE(?,valor_cents),
        observacoes=COALESCE(?,observacoes)
        WHERE id=?''',
        (d.get('status'),d.get('data_vencimento'),d.get('data_pagamento'),
         d.get('valor_cents'),d.get('observacoes'),pid))
    conn.commit()
    updated = conn.execute('SELECT * FROM parcelas WHERE id=?',(pid,)).fetchone()
    conn.close()
    return jsonify(dict(updated))

# ── Config do sistema ─────────────────────────────────────────
@bp.route('/config', methods=['GET'])
@token_required
def get_config():
    conn = get_db()
    rows = conn.execute('SELECT * FROM config').fetchall()
    conn.close()
    return jsonify({r['chave']: r['valor'] for r in rows})

@bp.route('/config', methods=['PUT'])
@token_required
def update_config():
    d    = request.get_json() or {}
    conn = get_db()
    for chave, valor in d.items():
        conn.execute('INSERT OR REPLACE INTO config (chave,valor) VALUES (?,?)',
                     (chave, str(valor)))
    conn.commit()
    rows = conn.execute('SELECT * FROM config').fetchall()
    conn.close()
    return jsonify({r['chave']: r['valor'] for r in rows})
