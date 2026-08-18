"""Contratos de dados e schemas Pydantic para o serviço de serving de previsões."""

from typing import List, Optional
from pydantic import BaseModel, Field


class PrevisaoItem(BaseModel):
    """Schema de uma previsão individual de atleta por rodada."""

    atleta_id: int = Field(..., description="Identificador único do atleta", json_schema_extra={"example": 10004})
    ano: int = Field(..., description="Ano da temporada", json_schema_extra={"example": 2025})
    rodada_id: int = Field(..., description="Número da rodada", json_schema_extra={"example": 1})
    clube_id: int = Field(..., description="Identificador do clube do atleta", json_schema_extra={"example": 105})
    posicao_id: int = Field(..., description="Identificador da posição tática", json_schema_extra={"example": 6})
    pontos_predito: float = Field(..., description="Pontuação prevista pelo modelo", json_schema_extra={"example": 4.09})
    data_predicao: str = Field(
        ...,
        description="Timestamp ISO 8601 da geração da predição",
        json_schema_extra={"example": "2026-08-18T05:45:34Z"},
    )


class PrevisoesResponse(BaseModel):
    """Envelope de resposta para o endpoint de previsões."""

    total: int = Field(..., description="Total de previsões retornadas na consulta", json_schema_extra={"example": 100})
    total_disponivel: int = Field(
        ..., description="Total de previsões correspondentes ao filtro antes da paginação", json_schema_extra={"example": 27832}
    )
    limit: int = Field(..., description="Limite de registros por página", json_schema_extra={"example": 100})
    offset: int = Field(..., description="Deslocamento da paginação", json_schema_extra={"example": 0})
    previsoes: List[PrevisaoItem] = Field(..., description="Lista de previsões no contrato oficial")


class HealthResponse(BaseModel):
    """Schema de resposta do healthcheck."""

    status: str = Field(..., json_schema_extra={"example": "healthy"})
    servico: str = Field(..., json_schema_extra={"example": "Gato Mestre - API de Serving de Previsões"})
    ano_safra: int = Field(..., json_schema_extra={"example": 2025})
    total_previsoes: int = Field(..., json_schema_extra={"example": 27832})
    rodadas_disponiveis: List[int] = Field(..., json_schema_extra={"example": [1, 2, 3, 38]})


class RodadasResponse(BaseModel):
    """Schema de resposta para a lista de rodadas."""

    total_rodadas: int = Field(..., json_schema_extra={"example": 38})
    rodadas: List[int] = Field(..., json_schema_extra={"example": [1, 2, 3, 38]})
