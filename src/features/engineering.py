"""Módulo de Engenharia de Features e Preparação de Variáveis Preditivas para Modelagem no Cartola FC / Gato Mestre.

Consolida de ponta a ponta:
1. Homogeneização das regras de pontuação com pesos oficiais de 2025.
2. Força ofensiva e vulnerabilidade defensiva das equipes (L5) com fallback histórico.
3. Indicadores individuais de pontuação (Lags, Janelas Móveis e Volatilidade) com Cold Start inteligente.
4. Decomposição de Piso, Teto, Chutes, Disciplina e Médias Móveis Exponenciais (EWMA).
5. Defasagem de métricas de mercado para mitigação de Data Leakage.
6. Ratios táticos, Z-Score posicional e Regimes de Temporada.
"""

from __future__ import annotations

from typing import Dict, List, Tuple
import numpy as np
import pandas as pd

# ── Regras Oficiais de Pontuação Homogeneizada (2025) ─────────────────────────
REGRAS_PONTUACAO_2025: Dict[str, float] = {
    'G': 8.0,
    'A': 5.0,
    'SG': 5.0,
    'DS': 1.5,
    'DE': 1.3,
    'FS': 0.5,
    'FD': 1.2,
    'FF': 0.8,
    'FT': 3.0,
    'DP': 7.0,
    'GS': -1.0,
    'FC': -0.3,
    'CA': -1.0,
    'CV': -3.0,
    'I': -0.1,
    'PP': -4.0,
    'PC': -1.0,
    'GC': -3.0,
}

# ── Listas Canônicas de Features e Metadados ─────────────────────────────────
COLS_IDS: List[str] = [
    'atleta_id',
    'apelido',
    'ano',
    'rodada_id',
    'clube_id',
    'opponent',
    'match_id',
    'posicao_nome',
]

COL_TARGET: str = 'pontos_target_2025'

COLS_TO_PREDICT: List[str] = [
    # Mercado e Contexto Básico (Defasados)
    'preco_num_lag1',
    'variacao_num_lag1',
    'media_num_lag1',
    'jogos_num_lag1',
    'status_pre',
    'status_inicial',
    'home_dummy',
    'posicao_id',
    'is_rodada_1',
    # Força da Equipe e Vulnerabilidade do Rival (L5)
    'clube_media_pts_feitos_l5',
    'adv_media_pts_cedidos_l5',
    # Momento Individual de Pontos (Lags e Rolling)
    'feat_pontos_lag1',
    'feat_pontos_lag2',
    'feat_media_pontos_3j',
    'feat_media_pontos_5j',
    'feat_std_pontos_5j',
    # Decomposição de Piso, Teto, Chutes e Disciplina (EWMA 5)
    'piso_ewma5',
    'teto_ewma5',
    'chutes_ewma5',
    'pts_piso_gol_ewma5',
    'disciplina_ewma5',
    # Confiabilidade Física e Relatividade Posicional
    'minutos_ewma5',
    'taxa_presenca_ewma5',
    'ratio_teto_piso',
    'taxa_conversao_l5',
    'piso_zscore_posicao',
    # Especializações Táticas
    'taxa_criacao_armacao',
    'perfil_volante_intensidade',
    'armacao_ewma3',
    'intensidade_ewma3',
    'is_meia_armador',
    # Calendário e Regimes
    'regime_1turno',
    'regime_2turno',
    'regime_reta_final',
]


def calcular_pontos_target_2025(
    df: pd.DataFrame, regras: Dict[str, float] = REGRAS_PONTUACAO_2025
) -> pd.DataFrame:
    """Calcula o target homogeneizado de pontuação com base nas regras de 2025."""
    df_res = df.copy()
    scouts_presentes = [col for col in regras.keys() if col in df_res.columns]
    pesos = pd.Series({k: regras[k] for k in scouts_presentes})

    # Pontuação para jogadores de linha e goleiros
    df_res['pontos_target_2025'] = df_res[scouts_presentes].dot(pesos)

    # Média do clube atribuída para técnicos (posicao_id == 6)
    mask_jogadores = (df_res['posicao_id'] != 6) & (df_res['entrou_em_campo'] == True)
    medias_clube = (
        df_res[mask_jogadores]
        .groupby(['ano', 'rodada_id', 'clube_id'])['pontos_target_2025']
        .transform('mean')
    )

    df_res.loc[mask_jogadores.index[mask_jogadores], '_media_clube'] = medias_clube
    df_res['_media_clube'] = df_res.groupby(['ano', 'rodada_id', 'clube_id'])['_media_clube'].transform('first')

    mask_tecnicos = df_res['posicao_id'] == 6
    df_res.loc[mask_tecnicos, 'pontos_target_2025'] = df_res.loc[mask_tecnicos, '_media_clube'].fillna(0.0)

    return df_res.drop(columns=['_media_clube'], errors='ignore')


def calcular_features_equipe(df: pd.DataFrame) -> pd.DataFrame:
    """Calcula a força recente da equipe e a vulnerabilidade do adversário com fallback histórico."""
    df_res = df.copy()

    pontos_por_clube_jogo = (
        df_res[df_res['entrou_em_campo']]
        .groupby(['ano', 'rodada_id', 'clube_id'])['pontos_target_2025']
        .sum()
        .reset_index()
        .rename(columns={'pontos_target_2025': 'pts_conquistados_equipe'})
        .sort_values(['ano', 'clube_id', 'rodada_id'])
    )

    pontos_por_clube_jogo['clube_media_pts_feitos_l5'] = (
        pontos_por_clube_jogo.groupby(['ano', 'clube_id'])['pts_conquistados_equipe']
        .transform(lambda s: s.shift(1).rolling(5, min_periods=1).mean())
    )

    df_clube_l5 = pontos_por_clube_jogo[['ano', 'rodada_id', 'clube_id', 'clube_media_pts_feitos_l5']]
    df_adv_l5 = pontos_por_clube_jogo[['ano', 'rodada_id', 'clube_id', 'clube_media_pts_feitos_l5']].rename(
        columns={'clube_id': 'opponent', 'clube_media_pts_feitos_l5': 'adv_media_pts_cedidos_l5'}
    )

    df_res = df_res.drop(columns=[c for c in ['clube_media_pts_feitos_l5', 'adv_media_pts_cedidos_l5'] if c in df_res.columns], errors='ignore')
    df_res = df_res.merge(df_clube_l5, on=['ano', 'rodada_id', 'clube_id'], how='left')
    df_res = df_res.merge(df_adv_l5, on=['ano', 'rodada_id', 'opponent'], how='left')

    media_geral_anual = df_res.groupby('ano')['pontos_target_2025'].mean() * 11
    media_clube_ano_anterior = (
        pontos_por_clube_jogo.groupby(['ano', 'clube_id'])['pts_conquistados_equipe']
        .mean()
        .reset_index()
    )
    media_clube_ano_anterior['ano_alvo'] = media_clube_ano_anterior['ano'] + 1
    dict_fallback_clube = media_clube_ano_anterior.set_index(['ano_alvo', 'clube_id'])['pts_conquistados_equipe'].to_dict()

    def aplica_fallback(row: pd.Series, col_alvo: str) -> float:
        val = row.get(col_alvo, np.nan)
        if pd.notna(val):
            return val
        ano = row['ano']
        clube = row['clube_id'] if col_alvo == 'clube_media_pts_feitos_l5' else row['opponent']
        if (ano, clube) in dict_fallback_clube:
            return dict_fallback_clube[(ano, clube)]
        return media_geral_anual.get(ano - 1, media_geral_anual.get(ano, 45.0))

    df_res['clube_media_pts_feitos_l5'] = df_res.apply(lambda r: aplica_fallback(r, 'clube_media_pts_feitos_l5'), axis=1)
    df_res['adv_media_pts_cedidos_l5'] = df_res.apply(lambda r: aplica_fallback(r, 'adv_media_pts_cedidos_l5'), axis=1)

    return df_res


def calcular_features_individuais(df: pd.DataFrame) -> pd.DataFrame:
    """Calcula lags e janelas móveis individuais de pontuação com tratamento de Cold Start."""
    df_res = df.copy()

    hist_clube_pos = (
        df_res.groupby(['ano', 'clube_id', 'posicao_id'])['pontos_target_2025']
        .mean()
        .reset_index()
    )
    hist_clube_pos['ano_alvo'] = hist_clube_pos['ano'] + 1
    dict_cold_start = hist_clube_pos.set_index(['ano_alvo', 'clube_id', 'posicao_id'])['pontos_target_2025'].to_dict()

    hist_pos = df_res.groupby(['ano', 'posicao_id'])['pontos_target_2025'].mean().reset_index()
    hist_pos['ano_alvo'] = hist_pos['ano'] + 1
    dict_cold_start_pos = hist_pos.set_index(['ano_alvo', 'posicao_id'])['pontos_target_2025'].to_dict()
    media_geral_pos = df_res.groupby('posicao_id')['pontos_target_2025'].mean().to_dict()

    def get_baseline(row: pd.Series) -> float:
        ano, clube, pos = row['ano'], row['clube_id'], row['posicao_id']
        if (ano, clube, pos) in dict_cold_start:
            return dict_cold_start[(ano, clube, pos)]
        elif (ano, pos) in dict_cold_start_pos:
            return dict_cold_start_pos[(ano, pos)]
        return media_geral_pos.get(pos, 3.0)

    df_res['baseline_cold_start'] = df_res.apply(get_baseline, axis=1)

    grouped_pts = df_res.groupby(['atleta_id', 'ano'])['pontos_target_2025']
    df_res['feat_pontos_lag1'] = grouped_pts.shift(1).fillna(df_res['baseline_cold_start'])
    df_res['feat_pontos_lag2'] = grouped_pts.shift(2).fillna(df_res['baseline_cold_start'])
    df_res['feat_media_pontos_3j'] = grouped_pts.transform(lambda x: x.shift(1).rolling(3, min_periods=1).mean()).fillna(df_res['baseline_cold_start'])
    df_res['feat_media_pontos_5j'] = grouped_pts.transform(lambda x: x.shift(1).rolling(5, min_periods=1).mean()).fillna(df_res['baseline_cold_start'])
    df_res['feat_std_pontos_5j'] = grouped_pts.transform(lambda x: x.shift(1).rolling(5, min_periods=2).std()).fillna(0.0)

    return df_res.drop(columns=['baseline_cold_start'])


def calcular_features_scouts_ewma(df: pd.DataFrame) -> pd.DataFrame:
    """Calcula decomposição de piso, teto, disciplina e especializações setoriais via EWMA."""
    df_res = df.copy()

    gols = df_res.get('G', 0)
    assist = df_res.get('A', 0)
    sg = df_res.get('SG', 0)
    chutes = df_res.get('FF', 0) + df_res.get('FD', 0) + df_res.get('FT', 0)
    defensivos = df_res.get('DS', 0) + df_res.get('DE', 0) + df_res.get('DP', 0)
    disciplina = (df_res.get('CA', 0) * -1.0) + (df_res.get('CV', 0) * -3.0) + (df_res.get('FC', 0) * -0.3)

    df_res['_piso_raw'] = defensivos + df_res.get('FS', 0) * 0.5
    df_res['_teto_raw'] = (gols * 8.0) + (assist * 5.0) + (sg * 5.0)
    df_res['_chutes_raw'] = chutes
    df_res['_piso_gol_raw'] = df_res['_piso_raw'] + (gols * 8.0)
    df_res['_disciplina_raw'] = disciplina
    df_res['_minutos_raw'] = df_res.get('minutos_jogados', 0).fillna(0.0)
    df_res['_presenca_raw'] = df_res.get('entrou_em_campo', 0).astype(int)

    cols_ewma = {
        'piso_ewma5': '_piso_raw',
        'teto_ewma5': '_teto_raw',
        'chutes_ewma5': '_chutes_raw',
        'pts_piso_gol_ewma5': '_piso_gol_raw',
        'disciplina_ewma5': '_disciplina_raw',
        'minutos_ewma5': '_minutos_raw',
        'taxa_presenca_ewma5': '_presenca_raw',
    }

    for target_col, raw_col in cols_ewma.items():
        df_res[target_col] = (
            df_res.groupby(['atleta_id', 'ano'])[raw_col]
            .transform(lambda s: s.shift(1).ewm(span=5, min_periods=1).mean())
            .fillna(0.0)
        )

    df_res['ratio_teto_piso'] = np.where(df_res['piso_ewma5'] > 0, df_res['teto_ewma5'] / df_res['piso_ewma5'], df_res['teto_ewma5'])

    gols_l5 = df_res.groupby(['atleta_id', 'ano'])['G'].transform(lambda s: s.shift(1).rolling(5, min_periods=1).sum()).fillna(0.0)
    chutes_l5 = df_res.groupby(['atleta_id', 'ano'])['_chutes_raw'].transform(lambda s: s.shift(1).rolling(5, min_periods=1).sum()).fillna(0.0)
    df_res['taxa_conversao_l5'] = np.where(chutes_l5 > 0, gols_l5 / chutes_l5, 0.0)

    pos_mean = df_res.groupby(['ano', 'rodada_id', 'posicao_id'])['piso_ewma5'].transform('mean')
    pos_std = df_res.groupby(['ano', 'rodada_id', 'posicao_id'])['piso_ewma5'].transform('std').replace(0, 1.0).fillna(1.0)
    df_res['piso_zscore_posicao'] = ((df_res['piso_ewma5'] - pos_mean) / pos_std).fillna(0.0)

    df_res['_armacao_raw'] = assist + df_res.get('FS', 0)
    df_res['_intensidade_raw'] = df_res.get('DS', 0) + df_res.get('FC', 0)

    df_res['armacao_ewma3'] = df_res.groupby(['atleta_id', 'ano'])['_armacao_raw'].transform(lambda s: s.shift(1).ewm(span=3, min_periods=1).mean()).fillna(0.0)
    df_res['intensidade_ewma3'] = df_res.groupby(['atleta_id', 'ano'])['_intensidade_raw'].transform(lambda s: s.shift(1).ewm(span=3, min_periods=1).mean()).fillna(0.0)

    fator_minutos = df_res['minutos_ewma5'] / 90.0 + 0.1
    df_res['taxa_criacao_armacao'] = df_res['armacao_ewma3'] / fator_minutos
    df_res['perfil_volante_intensidade'] = df_res['intensidade_ewma3'] / fator_minutos
    df_res['is_meia_armador'] = ((df_res['posicao_id'] == 4) & (df_res['armacao_ewma3'] > 1.2)).astype(int)

    return df_res.drop(columns=[c for c in df_res.columns if c.startswith('_')], errors='ignore')


def calcular_features_mercado_e_regime(df: pd.DataFrame) -> pd.DataFrame:
    """Aplica defasagem de métricas de mercado e codificação de regimes de temporada."""
    df_res = df.copy()

    for col in ['preco_num', 'variacao_num', 'media_num', 'jogos_num']:
        if col in df_res.columns:
            df_res[f'{col}_lag1'] = df_res.groupby(['atleta_id', 'ano'])[col].shift(1).fillna(df_res[col])

    # Criação do regime caso ainda não exista
    if 'regime_temporada' not in df_res.columns and 'rodada_id' in df_res.columns:
        conditions = [
            df_res['rodada_id'].between(1, 3),
            df_res['rodada_id'].between(4, 20),
            df_res['rodada_id'].between(21, 35),
            df_res['rodada_id'].between(36, 38),
        ]
        choices = [
            '1. Arranque (R1-R3)',
            '2. Corpo 1º Turno (R4-R20)',
            '3. Corpo 2º Turno (R21-R35)',
            '4. Reta Final (R36-R38)',
        ]
        df_res['regime_temporada'] = np.select(conditions, choices, default='2. Corpo 1º Turno (R4-R20)')

    if 'regime_temporada' in df_res.columns:
        df_res = pd.get_dummies(df_res, columns=['regime_temporada'], prefix='regime', drop_first=True, dtype=int)
        mapa_renomeacao = {
            'regime_2. Corpo 1º Turno (R4-R20)': 'regime_1turno',
            'regime_3. Corpo 2º Turno (R21-R35)': 'regime_2turno',
            'regime_4. Reta Final (R36-R38)': 'regime_reta_final',
        }
        df_res = df_res.rename(columns={k: v for k, v in mapa_renomeacao.items() if k in df_res.columns})

    for r_col in ['regime_1turno', 'regime_2turno', 'regime_reta_final']:
        if r_col not in df_res.columns:
            df_res[r_col] = 0

    return df_res


def pipeline_gerar_features(
    input_path: str = "base_limpa_gm.parquet",
    output_path: str | None = "dataset_features_modelagem.parquet",
) -> pd.DataFrame:
    """Executa a pipeline completa de engenharia de features e salva o dataset de modelagem."""
    print(f"🔄 Carregando base limpa: {input_path}...")
    df = pd.read_parquet(input_path)

    # 1. Ordenação Causal
    df = df.sort_values(by=['atleta_id', 'ano', 'rodada_id']).reset_index(drop=True)
    df['is_rodada_1'] = (df['rodada_id'] == 1).astype(int)

    # 2. Execução sequencial dos blocos de features
    print("⚙️  Calculando target homogeneizado (2025)...")
    df = calcular_pontos_target_2025(df)

    print("⚙️  Calculando features de equipe e adversário (L5)...")
    df = calcular_features_equipe(df)

    print("⚙️  Calculando features individuais com Cold Start...")
    df = calcular_features_individuais(df)

    print("⚙️  Calculando scouts derivados e médias exponenciais (EWMA)...")
    df = calcular_features_scouts_ewma(df)

    print("⚙️  Defasando métricas de mercado e codificando regimes...")
    df = calcular_features_mercado_e_regime(df)

    print(f"✅ Pipeline finalizada com sucesso! Shape final: {df.shape}")

    if output_path:
        df.to_parquet(output_path, index=False)
        print(f"💾 Dataset salvo em: {output_path}")

    return df