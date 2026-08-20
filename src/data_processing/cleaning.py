"""Módulo de saneamento, limpeza e conformidade canônica de dados para o Cartola FC / Gato Mestre.

Consolida de forma reprodutível todos os tratamentos de dados brutos históricos (`base_case_gm.csv`)
integrando com a base canônica extraída da API oficial (`api_atletas.json`, `api_jogos.json`, `api_jogos_detalhes.json`).
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional
import numpy as np
import pandas as pd


def extrair_minutos_evento(texto_momento: Any) -> Optional[float]:
    """Extrai valor numérico de minutos de strings de eventos como '80min'."""
    if not texto_momento:
        return None
    m = re.search(r'(\d+)', str(texto_momento))
    return float(m.group(1)) if m else None


def limpar_e_preparar_dados(
    df_raw: pd.DataFrame,
    api_atletas: List[Dict[str, Any]],
    api_jogos: List[Dict[str, Any]],
    api_jogos_detalhes: List[Dict[str, Any]],
) -> pd.DataFrame:
    """Executa o pipeline de limpeza e conformidade canônica preservando a rodada de mercado real.

    Tratamentos executados:
    1. Correção de `posicao_id` via cadastro canônico oficial (api_atletas.json).
    2. Reconstituição de contexto de mando (`home_dummy`) e adversário (`opponent`)
    via api_jogos.json.
    3. Remoção da coluna 100% nula `DD` e saneamento de formato/sinal de
    `preco_num`.
    4. Deduplicação e resolução estrita de granularidade primária em (atleta_id,
    match_id).
    5. Correção de `rodada_id` fora do calendário (0, 39, 41, 99) via api_jogos.json
    e criação da coluna `rodada_cbf_original`.
    6. Reconstituição de `minutos_jogados`, `status_inicial` e `entrou_em_campo`
    pelas súmulas oficiais.
    7. Padronização textual de `status_pre` e `apelido`.
    """
    df = df_raw.copy()

    # -------------------------------------------------------------------------
    # 1. Correção de posicao_id via api_atletas.json
    # -------------------------------------------------------------------------
    mapa_posicoes_api = {a['atleta_id']: a['posicao_id'] for a in api_atletas}
    df['posicao_id'] = (
        df['atleta_id']
        .map(mapa_posicoes_api)
        .fillna(df['posicao_id'])
        .astype(int)
    )

    # -------------------------------------------------------------------------
    # 2. Reconstituição de home_dummy e opponent via api_jogos.json
    # -------------------------------------------------------------------------
    mapa_mandantes = {j['jogo_id']: j['equipe_mandante_id'] for j in api_jogos}
    mapa_visitantes = {j['jogo_id']: j['equipe_visitante_id'] for j in api_jogos}

    mandante_partida = df['match_id'].map(mapa_mandantes)
    visitante_partida = df['match_id'].map(mapa_visitantes)

    df['home_dummy'] = (df['clube_id'] == mandante_partida).astype(int)
    opp_oficial = np.where(
        df['clube_id'] == mandante_partida, visitante_partida, mandante_partida
    )
    df['opponent'] = (
        pd.Series(opp_oficial, index=df.index).fillna(df['opponent']).astype(int)
    )

    # -------------------------------------------------------------------------
    # 3. Remoção de DD e Saneamento de preco_num
    # -------------------------------------------------------------------------
    if 'DD' in df.columns:
        df = df.drop(columns=['DD'])

    preco_limpo = pd.to_numeric(
        df['preco_num'].astype(str).str.strip().str.replace(',', '.'),
        errors='coerce',
    )
    df['preco_num'] = preco_limpo.abs()

    df = df.sort_values(['atleta_id', 'ano', 'rodada_id', 'match_id'])
    df['preco_num'] = (
        df.groupby(['atleta_id', 'ano'])['preco_num'].ffill().bfill()
    )
    df['preco_num'] = df['preco_num'].fillna(
        df.groupby('posicao_id')['preco_num'].transform('median')
    )

    # -------------------------------------------------------------------------
    # 4. Granularidade Estrita (atleta_id, match_id) e Resolução de Conflitos
    # -------------------------------------------------------------------------
    df = df.drop_duplicates().reset_index(drop=True)

    mapa_escalacao_oficial = {}
    for jd in api_jogos_detalhes:
        jid = jd.get('resultados', {}).get('jogo', {}).get('jogo_id')
        esc = jd.get('referencias', {}).get('escalacao', {})
        if jid and isinstance(esc, dict):
            for cid, t_esc in esc.items():
                for t in t_esc.get('titulares', []):
                    aid = t.get('atleta_id')
                    if aid:
                        mapa_escalacao_oficial[(jid, aid)] = {
                            'status_inicial': 'titular',
                            'entrou_em_campo': True,
                        }
                for r in t_esc.get('reservas', []):
                    aid = r.get('atleta_id')
                    if aid:
                        entrou = 'entrou' in r
                        mapa_escalacao_oficial[(jid, aid)] = {
                            'status_inicial': 'reserva',
                            'entrou_em_campo': entrou,
                        }

    def pontuar_conformidade(row):
        info_api = mapa_escalacao_oficial.get((row['match_id'], row['atleta_id']))
        pontuacao = 0
        if info_api:
            if row['entrou_em_campo'] == info_api['entrou_em_campo']:
                pontuacao += 10
        if row['entrou_em_campo']:
            pontuacao += 5
        if pd.notna(row['minutos_jogados']) and row['minutos_jogados'] > 0:
            pontuacao += 2
        return pontuacao

    df['_score_api'] = df.apply(pontuar_conformidade, axis=1)
    df = df.sort_values(
        ['atleta_id', 'match_id', '_score_api'], ascending=[True, True, False]
    )
    df = (
        df.drop_duplicates(subset=['atleta_id', 'match_id'], keep='first')
        .drop(columns=['_score_api'])
        .reset_index(drop=True)
    )

    # -------------------------------------------------------------------------
    # 5. Saneamento de rodada_id e Criação de rodada_cbf_original
    # -------------------------------------------------------------------------
    mapa_rodada_cbf = {j['jogo_id']: j['rodada'] for j in api_jogos}

    # Corrige valores de rodada_id fora da faixa 1-38 (ex: 0, 39, 41, 99) via match_id
    rodadas_invalidas = ~df['rodada_id'].between(1, 38)
    rodada_api = df['match_id'].map(mapa_rodada_cbf)
    df.loc[rodadas_invalidas, 'rodada_id'] = rodada_api[rodadas_invalidas].fillna(
        df.loc[rodadas_invalidas, 'rodada_id']
    )
    df['rodada_id'] = df['rodada_id'].astype(int)

    # Reconstituição canônica da rodada CBF original
    df['rodada_cbf_original'] = (
        df['match_id'].map(mapa_rodada_cbf).fillna(df['rodada_id']).astype(int)
    )

    # -------------------------------------------------------------------------
    # 6. Reconstituição de minutos_jogados, status_inicial e entrou_em_campo
    # -------------------------------------------------------------------------
    mapa_minutos_oficial = {}
    mapa_status_oficial = {}
    mapa_entrou_oficial = {}

    for jd in api_jogos_detalhes:
        jid = jd.get('resultados', {}).get('jogo', {}).get('jogo_id')
        esc = jd.get('referencias', {}).get('escalacao', {})
        if jid and isinstance(esc, dict):
            for cid, t_esc in esc.items():
                for t in t_esc.get('titulares', []):
                    aid = t.get('atleta_id')
                    if aid:
                        sub = t.get('substituido', {})
                        mom_sub = (
                            extrair_minutos_evento(sub.get('momento')) if sub else None
                        )
                        minutos = mom_sub if mom_sub is not None else 90.0
                        mapa_minutos_oficial[(jid, aid)] = minutos
                        mapa_status_oficial[(jid, aid)] = 'titular'
                        mapa_entrou_oficial[(jid, aid)] = True
                for r in t_esc.get('reservas', []):
                    aid = r.get('atleta_id')
                    if aid:
                        ent = r.get('entrou', {})
                        sub = r.get('substituido', {})
                        mom_ent = (
                            extrair_minutos_evento(ent.get('momento')) if ent else None
                        )
                        mom_sub = (
                            extrair_minutos_evento(sub.get('momento')) if sub else None
                        )
                        if mom_ent is not None:
                            minutos = (
                                (mom_sub - mom_ent)
                                if mom_sub is not None
                                else (90.0 - mom_ent)
                            )
                            minutos = max(0.0, minutos)
                            entrou = True
                        else:
                            minutos = 0.0
                            entrou = False
                        mapa_minutos_oficial[(jid, aid)] = minutos
                        mapa_status_oficial[(jid, aid)] = 'reserva'
                        mapa_entrou_oficial[(jid, aid)] = entrou

    pares_chaves = list(zip(df['match_id'], df['atleta_id']))

    minutos_canonica = [mapa_minutos_oficial.get(p) for p in pares_chaves]
    status_canonica = [mapa_status_oficial.get(p) for p in pares_chaves]
    entrou_canonica = [mapa_entrou_oficial.get(p) for p in pares_chaves]

    df['minutos_jogados'] = pd.Series(
        minutos_canonica, index=df.index
    ).fillna(0.0)
    df['status_inicial'] = (
        pd.Series(status_canonica, index=df.index)
        .fillna(df['status_inicial'])
        .astype(str)
        .str.strip()
        .str.lower()
    )
    df['entrou_em_campo'] = (
        pd.Series(entrou_canonica, index=df.index)
        .fillna(df['entrou_em_campo'])
        .astype(bool)
    )

    # -------------------------------------------------------------------------
    # 7. Padronização Textual de status_pre e apelido
    # -------------------------------------------------------------------------
    mapa_apelidos_api = {a['atleta_id']: a['apelido'] for a in api_atletas}
    df['apelido'] = (
        df['atleta_id']
        .map(mapa_apelidos_api)
        .fillna(df['apelido'])
        .astype(str)
        .str.strip()
        .str.title()
    )
    df['status_pre'] = df['status_pre'].astype(str).str.strip().str.capitalize()

    return df