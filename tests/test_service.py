"""Testes de integração para a API FastAPI de serving de previsões."""

from fastapi.testclient import TestClient
import pytest

from src.service.app import app, load_previsoes_data


@pytest.fixture(scope="module")
def client():
    """Inicializa o TestClient garantindo o carregamento dos dados."""
    load_previsoes_data()
    with TestClient(app) as test_client:
        yield test_client


def test_endpoint_health(client):
    """Garante que o endpoint /health responde 200 OK com status healthy."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["ano_safra"] == 2025
    assert data["total_previsoes"] > 0
    assert len(data["rodadas_disponiveis"]) > 0


def test_endpoint_rodadas(client):
    """Garante que o endpoint /rodadas retorna a lista de rodadas indexadas."""
    response = client.get("/rodadas")
    assert response.status_code == 200
    data = response.json()
    assert data["total_rodadas"] > 0
    assert isinstance(data["rodadas"], list)
    assert 1 in data["rodadas"]


def test_endpoint_previsoes_padrao(client):
    """Garante que /previsoes retorna o envelope correto com paginação padrão."""
    response = client.get("/previsoes")
    assert response.status_code == 200
    data = response.json()
    assert "previsoes" in data
    assert "total" in data
    assert "total_disponivel" in data
    assert data["total"] == 100  # limit default
    assert data["offset"] == 0
    assert len(data["previsoes"]) == 100


def test_endpoint_previsoes_filtro_rodada(client):
    """Garante que o filtro de rodada funciona corretamente."""
    response = client.get("/previsoes?rodada_id=5&limit=50")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] <= 50
    for p in data["previsoes"]:
        assert p["rodada_id"] == 5


def test_endpoint_previsoes_filtro_atleta(client):
    """Garante que o filtro por atleta_id retorna apenas o atleta solicitado."""
    atleta_id_teste = 10004
    response = client.get(f"/previsoes?atleta_id={atleta_id_teste}")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] > 0
    for p in data["previsoes"]:
        assert p["atleta_id"] == atleta_id_teste


def test_endpoint_previsoes_filtro_posicao(client):
    """Garante que o filtro por posicao_id retorna apenas atletas daquela posição."""
    posicao_teste = 1  # Goleiro
    response = client.get(f"/previsoes?posicao_id={posicao_teste}&limit=30")
    assert response.status_code == 200
    data = response.json()
    for p in data["previsoes"]:
        assert p["posicao_id"] == posicao_teste


def test_endpoint_previsoes_atleta_path_param(client):
    """Garante funcionamento da rota específica /previsoes/{atleta_id}."""
    atleta_id_teste = 10004
    response = client.get(f"/previsoes/{atleta_id_teste}")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] > 0
    assert all(p["atleta_id"] == atleta_id_teste for p in data["previsoes"])


def test_endpoint_previsoes_atleta_inexistente(client):
    """Garante que consultar um atleta inexistente retorna 200 com lista vazia (sem erro 500)."""
    response = client.get("/previsoes?atleta_id=999999999")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 0
    assert data["total_disponivel"] == 0
    assert data["previsoes"] == []


def test_validacao_parametros_invalidos(client):
    """Garante que parâmetros fora dos limites de negócio retornam 422 (validação Pydantic)."""
    # Rodada inválida (> 38)
    res_rodada = client.get("/previsoes?rodada_id=99")
    assert res_rodada.status_code == 422

    # Posição inválida (> 6)
    res_posicao = client.get("/previsoes?posicao_id=10")
    assert res_posicao.status_code == 422
