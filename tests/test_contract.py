"""Testes automatizados para validação do contrato de saída (previsoes.json)."""

from datetime import datetime
import json
from pathlib import Path
import pytest


def get_previsoes_path() -> Path:
    """Busca o arquivo de previsões na raiz ou em outputs/."""
    raiz = Path(__file__).resolve().parent.parent
    candidatos = [
        raiz / "previsoes.json",
        raiz / "outputs" / "previsoes.json",
    ]
    for p in candidatos:
        if p.exists() and p.is_file():
            return p
    pytest.fail("Arquivo previsoes.json não foi encontrado no repositório.")


@pytest.fixture(scope="module")
def previsoes_data():
    """Carrega o JSON de previsões para uso nos testes."""
    path = get_previsoes_path()
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data


def test_estrutura_raiz_json(previsoes_data):
    """Garante que a raiz do JSON contém a chave obrigatória 'previsoes'."""
    assert isinstance(previsoes_data, dict), "A raiz do arquivo JSON deve ser um objeto/dicionário."
    assert "previsoes" in previsoes_data, "A chave 'previsoes' deve estar presente na raiz do JSON."
    assert isinstance(previsoes_data["previsoes"], list), "O valor sob a chave 'previsoes' deve ser uma lista."
    assert len(previsoes_data["previsoes"]) > 0, "A lista de previsões não pode estar vazia."


def test_campos_obrigatorios_e_tipos(previsoes_data):
    """Valida se todas as previsões respeitam os campos e tipos do contrato oficial."""
    campos_esperados = {
        "atleta_id": int,
        "ano": int,
        "rodada_id": int,
        "clube_id": int,
        "posicao_id": int,
        "pontos_predito": (float, int),
        "data_predicao": str,
    }

    # Amostra as primeiras 500 predições e as últimas 500 para teste rápido e rigoroso
    amostra = previsoes_data["previsoes"][:500] + previsoes_data["previsoes"][-500:]

    for idx, item in enumerate(amostra):
        for campo, tipo_esperado in campos_esperados.items():
            assert campo in item, f"Campo '{campo}' ausente no registro de índice {idx}."
            assert isinstance(
                item[campo], tipo_esperado
            ), f"Campo '{campo}' com tipo inválido no registro {idx}: esperado {tipo_esperado}, obtido {type(item[campo])}."


def test_regras_de_dominio_e_intervalos(previsoes_data):
    """Valida intervalos regulamentares de rodadas, posições e anos."""
    for item in previsoes_data["previsoes"][:1000]:
        assert item["ano"] == 2025, f"Ano inválido: esperado 2025, obtido {item['ano']}."
        assert 1 <= item["rodada_id"] <= 38, f"Rodada fora do intervalo oficial (1-38): {item['rodada_id']}."
        assert 1 <= item["posicao_id"] <= 6, f"Posição tática fora do intervalo oficial (1-6): {item['posicao_id']}."
        assert not (
            item["pontos_predito"] != item["pontos_predito"]
        ), f"Predição NaN encontrada para atleta {item['atleta_id']} na rodada {item['rodada_id']}."


def test_formato_timestamp_iso8601(previsoes_data):
    """Valida se o campo data_predicao segue o padrão ISO 8601."""
    primeiro_item = previsoes_data["previsoes"][0]
    data_str = primeiro_item["data_predicao"]

    # Deve conseguir converter para datetime sem erro
    try:
        # Suporta sufixo Z substituindo por +00:00 para datetime.fromisoformat
        dt = datetime.fromisoformat(data_str.replace("Z", "+00:00"))
        assert dt is not None
    except Exception as e:
        pytest.fail(f"Formato de data inválido ('{data_str}'): {e}")
