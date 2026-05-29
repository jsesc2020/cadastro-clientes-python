import pytest
import tempfile
import os
import sys

# Importa o pacote primeiro para garantir que o modulo seja registrado no sys.modules
import server.app
from server.app import app, init_db

# Acessa o modulo real via sys.modules, evitando conflito com o __init__.py do pacote
# que sobrescreve server.app com o objeto Flask
_mod = sys.modules['server.app']


@pytest.fixture
def client():
    """
    Cria um banco SQLite temporario e isolado para cada teste.
    Garante que dados de um teste nao interfiram em outro.
    """
    db_fd, db_path = tempfile.mkstemp(suffix='.sqlite3')
    os.close(db_fd)

    original_db_path = _mod.DB_PATH
    _mod.DB_PATH = db_path

    app.config['TESTING'] = True
    init_db()

    with app.test_client() as c:
        yield c

    _mod.DB_PATH = original_db_path
    try:
        os.unlink(db_path)
    except OSError:
        pass


def test_register_and_login(client):
    rv = client.post('/api/auth/register', json={'email': 'test@local', 'password': 'pass123'})
    assert rv.status_code == 200 or rv.status_code == 400

    rv = client.post('/api/auth/login', json={'email': 'test@local', 'password': 'pass123'})
    if rv.status_code == 200:
        assert 'token' in rv.get_json()


def test_collaborator_crud(client):
    client.post('/api/auth/register', json={'email': 'admin@local', 'password': 'adminpass'})
    rv = client.post('/api/auth/login', json={'email': 'admin@local', 'password': 'adminpass'})
    assert rv.status_code == 200
    token = rv.get_json()['token']

    rv = client.get('/api/collaborators', headers={'Authorization': f'Bearer {token}'})
    assert rv.status_code == 200

    rv = client.post('/api/collaborators', json={'email': 'colab@local'}, headers={'Authorization': f'Bearer {token}'})
    assert rv.status_code == 200 or rv.status_code == 400


def test_clients_and_contracts(client):
    client.post('/api/auth/register', json={'email': 'biz@local', 'password': 'bizpass'})
    rv = client.post('/api/auth/login', json={'email': 'biz@local', 'password': 'bizpass'})
    assert rv.status_code == 200
    token = rv.get_json()['token']

    rv = client.post('/api/clients/', json={'nome': 'Client X', 'documento': '123', 'telefone': '9999', 'email': 'x@c.com'}, headers={'Authorization': f'Bearer {token}'})
    assert rv.status_code == 200

    rv = client.post('/api/pontos/', json={'nome': 'Ponto Test', 'tipo': 'OUTDOOR', 'endereco': 'Rua Teste', 'latitude': 10.0, 'longitude': 20.0}, headers={'Authorization': f'Bearer {token}'})
    assert rv.status_code == 200
    ponto_id = rv.get_json()['id']

    rv = client.get('/api/clients/', headers={'Authorization': f'Bearer {token}'})
    cid = rv.get_json()[0]['id']

    rv = client.post('/api/contracts/', json={'cliente_id': cid, 'ponto_id': ponto_id, 'valor_cents': 10000, 'data_inicio': '2026-05-01', 'data_termino': '2026-05-31'}, headers={'Authorization': f'Bearer {token}'})
    assert rv.status_code == 200


def test_contract_status_and_point_conflicts(client):
    client.post('/api/auth/register', json={'email': 'biz2@local', 'password': 'bizpass'})
    rv = client.post('/api/auth/login', json={'email': 'biz2@local', 'password': 'bizpass'})
    token = rv.get_json()['token']

    client.post('/api/clients/', json={'nome': 'Client Y', 'documento': '999', 'telefone': '1111', 'email': 'y@c.com'}, headers={'Authorization': f'Bearer {token}'})
    client.post('/api/pontos/', json={'nome': 'Ponto Y', 'tipo': 'OUTDOOR', 'endereco': 'Rua Teste', 'latitude': 12.34, 'longitude': 56.78}, headers={'Authorization': f'Bearer {token}'})

    rv = client.get('/api/clients/', headers={'Authorization': f'Bearer {token}'})
    cid = rv.get_json()[0]['id']
    rv = client.get('/api/pontos/', headers={'Authorization': f'Bearer {token}'})
    pid = rv.get_json()[0]['id']

    # Primeiro contrato deve ser criado com sucesso
    rv = client.post('/api/contracts/', json={'cliente_id': cid, 'ponto_id': pid, 'valor_cents': 15000, 'data_inicio': '2026-06-01', 'data_termino': '2026-06-30'}, headers={'Authorization': f'Bearer {token}'})
    assert rv.status_code == 200, f"Esperado 200, recebido {rv.status_code}: {rv.get_json()}"
    contract_id = rv.get_json()['id']

    # Segundo contrato no mesmo ponto deve falhar (conflito)
    rv = client.post('/api/contracts/', json={'cliente_id': cid, 'ponto_id': pid, 'valor_cents': 8000, 'data_inicio': '2026-06-15', 'data_termino': '2026-06-20'}, headers={'Authorization': f'Bearer {token}'})
    assert rv.status_code == 400
    assert 'active contract' in rv.get_json().get('error', '').lower()

    # Cancela o contrato
    rv = client.post(f'/api/contracts/{contract_id}/cancel', headers={'Authorization': f'Bearer {token}'})
    assert rv.status_code == 200
    assert rv.get_json()['status'] == 'CANCELADO'

    # Renova o contrato
    rv = client.post(f'/api/contracts/{contract_id}/renew', json={'data_termino': '2026-07-31'}, headers={'Authorization': f'Bearer {token}'})
    assert rv.status_code == 200
    assert rv.get_json()['status'] == 'ATIVO'
