"""Aplicação FastAPI para serving de previsões de pontuação de atletas do Gato Mestre."""

from contextlib import asynccontextmanager
import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException, Query, status
from fastapi.middleware.cors import CORSMiddleware

from src.service.schemas import (
    HealthResponse,
    PrevisaoItem,
    PrevisoesResponse,
    RodadasResponse,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("gato_mestre_service")

# Estrutura de armazenamento em memória para serving de baixa latência
PREVISOES_STORAGE: List[Dict[str, Any]] = []
RODADAS_DISPONIVEIS: List[int] = []


def find_previsoes_file() -> Path:
    """Localiza o arquivo previsoes.json no repositório."""
    caminhos_candidatos = [
        Path(__file__).resolve().parent.parent.parent / "previsoes.json",
        Path(__file__).resolve().parent.parent.parent / "outputs" / "previsoes.json",
        Path("previsoes.json"),
        Path("outputs/previsoes.json"),
    ]
    for p in caminhos_candidatos:
        if p.exists() and p.is_file():
            return p
    raise FileNotFoundError("Arquivo previsoes.json não foi encontrado no repositório.")


def load_previsoes_data() -> None:
    """Carrega o arquivo previsoes.json e indexa em memória."""
    global PREVISOES_STORAGE, RODADAS_DISPONIVEIS
    file_path = find_previsoes_file()
    logger.info(f"Carregando previsões a partir de: {file_path}")

    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    if "previsoes" not in data:
        raise ValueError("Formato inválido: chave 'previsoes' ausente no JSON.")

    PREVISOES_STORAGE.clear()
    PREVISOES_STORAGE.extend(data["previsoes"])
    RODADAS_DISPONIVEIS.clear()
    RODADAS_DISPONIVEIS.extend(sorted(list({p["rodada_id"] for p in PREVISOES_STORAGE if "rodada_id" in p})))
    logger.info(
        f"Carga concluída com sucesso: {len(PREVISOES_STORAGE)} previsões indexadas "
        f"abrangendo {len(RODADAS_DISPONIVEIS)} rodadas."
    )


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Gerencia o ciclo de vida do servidor (startup e shutdown)."""
    try:
        load_previsoes_data()
    except Exception as e:
        logger.error(f"Erro ao carregar dados no startup: {e}")
    yield


app = FastAPI(
    title="Gato Mestre - API de Previsão de Pontuação",
    description=(
        "Serviço de serving para disponibilização de previsões de pontuação de atletas "
        "para o ecossistema Cartola FC / ge. Desenvolvido para servir as predições do modelo de Machine Learning "
        "com alta disponibilidade e baixa latência."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get(
    "/health",
    response_model=HealthResponse,
    summary="Healthcheck e Metadados do Serviço",
    tags=["Operação"],
)
def get_health() -> HealthResponse:
    """Retorna o status operacional da API, o volume de previsões indexadas e metadados."""
    ano_safra = PREVISOES_STORAGE[0].get("ano", 2025) if PREVISOES_STORAGE else 2025
    return HealthResponse(
        status="healthy" if PREVISOES_STORAGE else "degraded",
        servico="Gato Mestre - API de Serving de Previsões",
        ano_safra=ano_safra,
        total_previsoes=len(PREVISOES_STORAGE),
        rodadas_disponiveis=RODADAS_DISPONIVEIS,
    )


@app.get(
    "/rodadas",
    response_model=RodadasResponse,
    summary="Lista de Rodadas Disponíveis",
    tags=["Consultas"],
)
def get_rodadas() -> RodadasResponse:
    """Retorna a lista de todas as rodadas que possuem previsões geradas na safra."""
    return RodadasResponse(
        total_rodadas=len(RODADAS_DISPONIVEIS),
        rodadas=RODADAS_DISPONIVEIS,
    )


def _filtrar_previsoes(
    rodada_id: Optional[int] = None,
    atleta_id: Optional[int] = None,
    clube_id: Optional[int] = None,
    posicao_id: Optional[int] = None,
    limit: int = 100,
    offset: int = 0,
) -> PrevisoesResponse:
    """Lógica pura de filtragem e paginação das previsões."""
    if not PREVISOES_STORAGE:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Serviço ainda não carregou as previsões ou arquivo de predições está vazio.",
        )

    filtrados = PREVISOES_STORAGE

    if rodada_id is not None:
        filtrados = [p for p in filtrados if p.get("rodada_id") == rodada_id]
    if atleta_id is not None:
        filtrados = [p for p in filtrados if p.get("atleta_id") == atleta_id]
    if clube_id is not None:
        filtrados = [p for p in filtrados if p.get("clube_id") == clube_id]
    if posicao_id is not None:
        filtrados = [p for p in filtrados if p.get("posicao_id") == posicao_id]

    total_disponivel = len(filtrados)
    paginados = filtrados[offset : offset + limit]

    return PrevisoesResponse(
        total=len(paginados),
        total_disponivel=total_disponivel,
        limit=limit,
        offset=offset,
        previsoes=[PrevisaoItem(**p) for p in paginados],
    )


@app.get(
    "/previsoes",
    response_model=PrevisoesResponse,
    summary="Consulta de Previsões com Filtros",
    tags=["Consultas"],
)
def get_previsoes(
    rodada_id: Optional[int] = Query(default=None, description="Filtrar por número da rodada (1 a 38)", ge=1, le=38),
    atleta_id: Optional[int] = Query(default=None, description="Filtrar por ID do atleta"),
    clube_id: Optional[int] = Query(default=None, description="Filtrar por ID do clube"),
    posicao_id: Optional[int] = Query(default=None, description="Filtrar por ID da posição tática (1 a 6)", ge=1, le=6),
    limit: int = Query(default=100, description="Quantidade máxima de registros retornados", ge=1, le=1000),
    offset: int = Query(default=0, description="Deslocamento para paginação", ge=0),
) -> PrevisoesResponse:
    """Consulta as previsões geradas para a safra de avaliação do Cartola FC.

    Permite combinar filtros por rodada, atleta, clube e posição com suporte à paginação.
    """
    return _filtrar_previsoes(
        rodada_id=rodada_id,
        atleta_id=atleta_id,
        clube_id=clube_id,
        posicao_id=posicao_id,
        limit=limit,
        offset=offset,
    )


@app.get(
    "/previsoes/{atleta_id}",
    response_model=PrevisoesResponse,
    summary="Consulta de Previsões por ID do Atleta",
    tags=["Consultas"],
)
def get_previsoes_por_atleta(
    atleta_id: int,
    rodada_id: Optional[int] = Query(default=None, description="Filtrar por rodada específica", ge=1, le=38),
) -> PrevisoesResponse:
    """Consulta o histórico de previsões de um atleta específico."""
    return _filtrar_previsoes(
        atleta_id=atleta_id,
        rodada_id=rodada_id,
        limit=100,
        offset=0,
    )
