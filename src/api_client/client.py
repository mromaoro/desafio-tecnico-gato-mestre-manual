"""
Cliente HTTP resiliente para consumo da API de Apoio de Dados Esportivos do Cartola FC / Gato Mestre.

Trata:
- Autenticação por header `token`.
- Paginação por cursor (`paginacao.proximo`) até exaustão.
- Rate limit (HTTP 429) respeitando o cabeçalho `Retry-After`.
- Instabilidades transitórias (HTTP 503 e erros de conexão) com retentativas e backoff exponencial.
"""

from __future__ import annotations

import time
import logging
from typing import Any, Dict, List, Optional
from urllib.parse import urljoin

import requests

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("ApiClient")


class ApiClient:
    """
    Cliente HTTP resiliente para a API de apoio do Desafio Técnico.
    """

    def __init__(
        self,
        base_url: str = "http://localhost:8080",
        token: str = "gm-0e9ba73c2c96",
        max_retries: int = 5,
        backoff_base: float = 1.0,
        timeout: float = 10.0,
    ):
        self.base_url = base_url.rstrip("/")
        self.token = token
        self.max_retries = max_retries
        self.backoff_base = backoff_base
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update({"token": self.token})

    def requisitar(
        self,
        endpoint_ou_url: str,
        params: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Executa requisição GET com retentativa para erros 503/conexão e espera para 429.
        """
        if endpoint_ou_url.startswith("http://") or endpoint_ou_url.startswith("https://"):
            url = endpoint_ou_url
        else:
            path = endpoint_ou_url if endpoint_ou_url.startswith("/") else f"/{endpoint_ou_url}"
            url = f"{self.base_url}{path}"

        tentativa = 0
        while tentativa <= self.max_retries:
            try:
                resposta = self.session.get(url, params=params, timeout=self.timeout)

                # 1. Sucesso (200)
                if resposta.status_code == 200:
                    return resposta.json()

                # 2. Rate Limit (429) - Respeita o cabeçalho Retry-After
                if resposta.status_code == 429:
                    retry_after = int(resposta.headers.get("Retry-After", 2))
                    logger.warning(
                        f"[429 Rate Limit] Limite excedido na URL {url}. "
                        f"Aguardando {retry_after}s conforme Retry-After..."
                    )
                    time.sleep(retry_after + 0.5)
                    continue

                # 3. Instabilidade Transitória (503) - Backoff Exponencial
                if resposta.status_code == 503:
                    tentativa += 1
                    espera = self.backoff_base * (2 ** (tentativa - 1))
                    logger.warning(
                        f"[503 Servidor Sobrecarregado] Tentativa {tentativa}/{self.max_retries}. "
                        f"Aguardando {espera:.1f}s antes de retentar..."
                    )
                    time.sleep(espera)
                    continue

                # 4. Erros não recuperáveis (400, 401, 404, etc.)
                resposta.raise_for_status()

            except (requests.exceptions.ConnectionError, requests.exceptions.Timeout) as e:
                tentativa += 1
                espera = self.backoff_base * (2 ** (tentativa - 1))
                logger.warning(
                    f"[Falha de Rede/Timeout] {e}. Tentativa {tentativa}/{self.max_retries}. "
                    f"Aguardando {espera:.1f}s..."
                )
                time.sleep(espera)

        raise RuntimeError(f"Falha ao consultar {url} após {self.max_retries} tentativas.")

    def obter_todos_paginado(
        self,
        endpoint: str,
        chave_resultados: str,
        params: Optional[Dict[str, Any]] = None,
        max_registros: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """
        Percorre todas as páginas de um endpoint até `paginacao.proximo` ser None ou atingir `max_registros`.
        """
        todos_itens = []
        url_ou_endpoint = endpoint
        parametros_atuais = params

        while url_ou_endpoint:
            dados = self.requisitar(url_ou_endpoint, params=parametros_atuais)
            
            # Extrai os itens do resultado
            resultados = dados.get("resultados", {})
            itens = resultados.get(chave_resultados, [])
            todos_itens.extend(itens)

            # Limite opcional para amostragem/testes
            if max_registros and len(todos_itens) >= max_registros:
                return todos_itens[:max_registros]

            # Próxima página
            paginacao = dados.get("paginacao", {})
            proximo = paginacao.get("proximo")
            if proximo:
                url_ou_endpoint = proximo
                parametros_atuais = None  # Os parâmetros já vêm embutidos na URL do proximo
            else:
                break

        return todos_itens

    def obter_jogos_temporada(
        self,
        edicao: int,
        rodada: Optional[int] = None,
        por_pagina: int = 100,
        max_registros: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """
        Lista todas as partidas de uma temporada inteira (ou rodada específica), com paginação automática.
        """
        params = {"edicao": edicao, "por_pagina": por_pagina}
        if rodada is not None:
            params["rodada"] = rodada
        return self.obter_todos_paginado("/jogos", "jogos", params=params, max_registros=max_registros)

    def obter_detalhes_jogo(self, jogo_id: int) -> Dict[str, Any]:
        """
        Consulta o detalhe de uma partida específica (incluindo escalação, se houver).
        """
        return self.requisitar(f"/jogos/{jogo_id}")

    def obter_equipes(self) -> List[Dict[str, Any]]:
        """
        Lista todas as equipes cadastradas.
        """
        dados = self.requisitar("/equipes")
        return dados.get("resultados", {}).get("equipes", [])

    def obter_atleta(self, atleta_id: int) -> Dict[str, Any]:
        """
        Consulta os dados cadastrais de um atleta (posição e clube).
        """
        return self.requisitar(f"/atletas/{atleta_id}")

    def obter_confrontos(self, temporada: int, rodada: int) -> Optional[Dict[str, Any]]:
        """
        Consulta o panorama de confrontos de uma rodada (médias de pontos cedidos e conquistados).
        Retorna None caso a rodada não tenha dados (HTTP 404).
        """
        try:
            dados = self.requisitar("/confrontos", params={"temporada": temporada, "rodada": rodada})
            return dados.get("resultados", {}).get("confrontos", {})
        except requests.exceptions.HTTPError as e:
            if e.response is not None and e.response.status_code == 404:
                return None
            raise
