from .app import init_db, get_db


def seed():
    init_db()
    conn = get_db()
    cur = conn.cursor()
    # sample clients
    clients = [
        ('ACME Ltda', '12.345.678/0001-90', '11999990000', 'acme@example.com'),
        ('Foo Bar SA', '98.765.432/0001-10', '21988880000', 'foo@example.com')
    ]
    for c in clients:
        try:
            cur.execute('INSERT INTO clientes (nome, documento, telefone, email) VALUES (?, ?, ?, ?)', c)
        except Exception:
            pass

    # sample pontos (simple table-less points simulated as contratos referencing ponto_id)
    # create contracts
    try:
        cur.execute('INSERT INTO contratos (cliente_id, ponto_id, valor_cents, status, data_inicio, data_termino) VALUES (?, ?, ?, ?, ?, ?)', (1, 101, 250000, 'ATIVO', '2026-01-01', '2026-12-31'))
        cur.execute('INSERT INTO contratos (cliente_id, ponto_id, valor_cents, status, data_inicio, data_termino) VALUES (?, ?, ?, ?, ?, ?)', (2, 102, 150000, 'ATIVO', '2026-03-01', '2026-09-30'))
    except Exception:
        pass

    conn.commit()
    conn.close()

if __name__ == '__main__':
    seed()
    print('Seed complete')
