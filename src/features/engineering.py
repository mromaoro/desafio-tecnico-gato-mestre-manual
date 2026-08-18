"""Módulo de Engenharia de Features e Preparação da Matriz de Modelagem.

Este módulo encapsula as transformações e cálculos de variáveis contextuais,
estatísticas defasadas (lags e rolling windows) e métricas compostas de confronto
validadas no Notebook 03, garantindo ZERO vazamento temporal (Data Leakage) e ZERO nulos.
"""

from typing import Any, Dict, List
import numpy as np
import pandas as pd


def gerar_features(
    df_limpo: pd.DataFrame,
    api_confrontos: Dict[str, Any],
    api_jogos_detalhes: List[Dict[str, Any]]
) -> pd.DataFrame:
    """Gera a matriz completa de features para os modelos de Machine Learning.

    Args:
        df_limpo (pd.DataFrame): Base tratada e limpa pelo módulo `src.data_processing.cleaning`.
        api_confrontos (dict): Dicionário com médias históricas de confronto por ano/rodada.
        api_jogos_detalhes (list): Lista com súmulas oficiais e escalações de todas as partidas.

    Returns:
        pd.DataFrame: Matriz enriquecida pronta para modelagem (115.613 linhas x 61 colunas, 0 nulos).
    """
    df = df_limpo.copy()

    # -------------------------------------------------------------------------
    # 1. Enriquecimento com api_confrontos.json (Médias de Confronto)
    # -------------------------------------------------------------------------
    registros_confrontos = []
    for chave, lista_confrontos in api_confrontos.items():
        if "/" in chave:
            ano_str, r_str = chave.split("/")
            ano, rodada = int(ano_str), int(r_str)
            for c in lista_confrontos:
                registros_confrontos.append({
                    "ano": ano,
                    "rodada_id": rodada,
                    "clube_id": c["equipe_id"],
                    "opponent": c["adversario_id"],
                    "clube_media_pontos_conquistados": c.get("equipe_media_pontos_conquistados"),
                    "opponent_media_pontos_cedidos": c.get("adversario_media_pontos_cedidos")
                })

    df_confrontos_flat = pd.DataFrame(registros_confrontos).drop_duplicates(
        subset=["ano", "rodada_id", "clube_id", "opponent"]
    )

    df = df.merge(
        df_confrontos_flat,
        on=["ano", "rodada_id", "clube_id", "opponent"],
        how="left"
    )

    # -------------------------------------------------------------------------
    # 2. Enriquecimento com api_jogos_detalhes.json (Estabilidade de Jaccard t-1 -> t-2, ZERO LEAKAGE)
    # -------------------------------------------------------------------------
    mapa_titulares_jogo = {}
    for jd in api_jogos_detalhes:
        jogo = jd.get("resultados", {}).get("jogo", {})
        ano = jogo.get("edicao")
        rodada = jogo.get("rodada")
        esc = jd.get("referencias", {}).get("escalacao", {})
        if ano and rodada and isinstance(esc, dict):
            for cid_str, t_esc in esc.items():
                cid = int(cid_str)
                titulares = {t["atleta_id"] for t in t_esc.get("titulares", []) if "atleta_id" in t}
                if titulares:
                    mapa_titulares_jogo[(ano, rodada, cid)] = titulares

    registros_estabilidade = []
    clubes = sorted(df["clube_id"].unique())
    for ano in sorted(df["ano"].unique()):
        for cid in clubes:
            for r in range(1, 39):
                # Estabilidade estritamente pré-jogo: compara a escalação de r-1 com a de r-2
                t_anterior = mapa_titulares_jogo.get((ano, r - 1, cid))
                t_retrasado = mapa_titulares_jogo.get((ano, r - 2, cid))
                if t_anterior and t_retrasado:
                    inter = len(t_anterior.intersection(t_retrasado))
                    union = len(t_anterior.union(t_retrasado))
                    jaccard = inter / union if union > 0 else np.nan
                else:
                    jaccard = np.nan
                registros_estabilidade.append({
                    "ano": ano,
                    "rodada_id": r,
                    "clube_id": cid,
                    "estabilidade_11_titular": jaccard
                })

    df_estabilidade = pd.DataFrame(registros_estabilidade).drop_duplicates(
        subset=["ano", "rodada_id", "clube_id"]
    )

    df = df.merge(
        df_estabilidade,
        on=["ano", "rodada_id", "clube_id"],
        how="left"
    )

    # Nomes descritivos de posição
    nomes_posicoes = {
        1: "1. Goleiro",
        2: "2. Lateral",
        3: "3. Zagueiro",
        4: "4. Meia",
        5: "5. Atacante",
        6: "6. Técnico"
    }
    df["posicao_nome"] = df["posicao_id"].map(nomes_posicoes)

    # -------------------------------------------------------------------------
    # 3. Dinâmica Temporal e Regimes de Temporada
    # -------------------------------------------------------------------------
    def _classificar_regime(rodada: int) -> str:
        if rodada <= 5:
            return "1. Início (R1-R5)"
        elif rodada <= 30:
            return "2. Meio (R6-R30)"
        else:
            return "3. Reta Final (R31-R38)"

    df["regime_temporada"] = df["rodada_id"].map(_classificar_regime)
    df["is_inicio_temporada"] = (df["rodada_id"] <= 5).astype(int)
    df["progresso_campeonato"] = df["rodada_id"] / 38.0

    # -------------------------------------------------------------------------
    # 4. Features Defasadas Individuais (Médias Móveis dos Últimos 3 Jogos)
    # -------------------------------------------------------------------------
    # Ordenação cronológica estrita por ano, atleta e rodada
    df = df.sort_values(["ano", "atleta_id", "rodada_id"]).reset_index(drop=True)
    grp_atleta = df.groupby(["ano", "atleta_id"])

    # Participação e Minutagem em t-1 e janela de 3 jogos
    df["participou_lag1"] = grp_atleta["entrou_em_campo"].shift(1).fillna(False).astype(int)
    df["taxa_participacao_3j"] = grp_atleta["entrou_em_campo"].transform(
        lambda x: x.shift(1).rolling(3, min_periods=1).mean()
    ).fillna(0.0)
    df["minutos_medios_3j"] = grp_atleta["minutos_jogados"].transform(
        lambda x: x.shift(1).rolling(3, min_periods=1).mean()
    ).fillna(0.0)

    # Pontuação recente defasada e média acumulada pré-jogo
    df["pontos_lag1"] = grp_atleta["pontos_num"].shift(1).fillna(0.0)
    df["media_pontos_3j"] = grp_atleta["pontos_num"].transform(
        lambda x: x.shift(1).rolling(3, min_periods=1).mean()
    ).fillna(0.0)
    df["desvio_pontos_3j"] = grp_atleta["pontos_num"].transform(
        lambda x: x.shift(1).rolling(3, min_periods=1).std()
    ).fillna(0.0)
    df["media_acumulada_pre"] = grp_atleta["media_num"].shift(1).fillna(0.0)

    # Scouts de Volume defasados (DS + FS + FD + FF)
    scouts_vol = df["DS"] + df["FS"] + df["FD"] + df["FF"]
    df["_vol_temp"] = scouts_vol
    df["media_scouts_volume_3j"] = grp_atleta["_vol_temp"].transform(
        lambda x: x.shift(1).rolling(3, min_periods=1).mean()
    ).fillna(0.0)
    df.drop(columns=["_vol_temp"], inplace=True)

    # -------------------------------------------------------------------------
    # Features Defasadas de Scouts Específicos (Sem Data Leakage)
    # -------------------------------------------------------------------------
    # 1. Desarmes puros defasados (3 jogos)
    df["media_desarmes_3j"] = grp_atleta["DS"].transform(
        lambda x: x.shift(1).rolling(3, min_periods=1).mean()
    ).fillna(0.0)

    # 2. Finalizações totais defasadas (FD + FF + FT em 3 jogos)
    finalizacoes_totais = df["FD"] + df["FF"] + df["FT"]
    df["_fin_temp"] = finalizacoes_totais
    df["media_finalizacoes_3j"] = grp_atleta["_fin_temp"].transform(
        lambda x: x.shift(1).rolling(3, min_periods=1).mean()
    ).fillna(0.0)
    df.drop(columns=["_fin_temp"], inplace=True)

    # 3. Participação direta em gols nos últimos 5 jogos (G + A)
    gols_assists = df["G"] + df["A"]
    df["_ga_temp"] = gols_assists
    df["taxa_participacao_gols_5j"] = grp_atleta["_ga_temp"].transform(
        lambda x: x.shift(1).rolling(5, min_periods=1).sum()
    ).fillna(0.0)
    df.drop(columns=["_ga_temp"], inplace=True)

    # 4. Risco Disciplinar nos últimos 5 jogos (CA*2 + FC)
    cartoes_faltas = (df["CA"] * 2.0) + df["FC"]
    df["_disc_temp"] = cartoes_faltas
    df["score_risco_disciplinar_5j"] = grp_atleta["_disc_temp"].transform(
        lambda x: x.shift(1).rolling(5, min_periods=1).mean()
    ).fillna(0.0)
    df.drop(columns=["_disc_temp"], inplace=True)

    # 5. Defesas de Goleiro nos últimos 3 jogos (DE + DP)
    defesas_goleiro = df["DE"] + df["DP"]
    df["_def_temp"] = defesas_goleiro
    df["taxa_defesas_por_jogo_3j"] = grp_atleta["_def_temp"].transform(
        lambda x: x.shift(1).rolling(3, min_periods=1).mean()
    ).fillna(0.0)
    df.drop(columns=["_def_temp"], inplace=True)

    # -------------------------------------------------------------------------
    # 5. Features de Dinâmica Econômica e Eficiência de Mercado (ZERO LEAKAGE)
    # -------------------------------------------------------------------------
    # Preço de abertura da rodada t (preço de t-1) e lag de 3 jogos anteriores (t-4)
    preco_abertura_t = grp_atleta["preco_num"].shift(1).fillna(df["preco_num"])
    preco_lag3 = grp_atleta["preco_num"].shift(4).fillna(preco_abertura_t)

    df["preco_mercado_pre"] = preco_abertura_t
    df["momentum_preco_3j"] = preco_abertura_t / (preco_lag3 + 1e-4)
    df["roi_recente_3j"] = df["media_pontos_3j"] / (preco_abertura_t + 1e-4)

    # -------------------------------------------------------------------------
    # 6. Features Compostas de Confronto, Alavancagem e Risco de Rotação
    # -------------------------------------------------------------------------
    # Imputação determinística de confronto ausente pelas medianas dos clubes
    df["clube_media_pontos_conquistados"] = df["clube_media_pontos_conquistados"].fillna(
        df.groupby("clube_id")["clube_media_pontos_conquistados"].transform("median")
    ).fillna(45.0)

    df["opponent_media_pontos_cedidos"] = df["opponent_media_pontos_cedidos"].fillna(
        df.groupby("opponent")["opponent_media_pontos_cedidos"].transform("median")
    ).fillna(45.0)

    # Imputação da estabilidade tática (0.70 baseline para R1 e R2)
    df["estabilidade_11_titular_clube"] = df["estabilidade_11_titular"].fillna(0.70)

    # Fator de Alavancagem e Potencial Esperado do Atleta
    media_geral_cedida = df["opponent_media_pontos_cedidos"].mean()
    df["fator_alavancagem_confronto"] = df["opponent_media_pontos_cedidos"] / (media_geral_cedida + 1e-4)
    df["potencial_esperado_atleta"] = df["media_pontos_3j"] * df["fator_alavancagem_confronto"]

    # Favoritismo ajustado ao mando e volume da partida
    peso_mando = np.where(df["home_dummy"] == 1, 1.25, 0.75)
    df["indice_favoritismo_mando"] = (
        df["clube_media_pontos_conquistados"] - df["opponent_media_pontos_cedidos"]
    ) * peso_mando
    df["volume_esperado_partida"] = (
        df["clube_media_pontos_conquistados"] + df["opponent_media_pontos_cedidos"]
    )
    df["diff_forca_confronto"] = (
        df["clube_media_pontos_conquistados"] - df["opponent_media_pontos_cedidos"]
    )

    # Score de Risco de Rotação Tática
    df["score_risco_rotacao"] = (
        1.0 - df["estabilidade_11_titular_clube"]
    ) * (
        1.0 - df["taxa_participacao_3j"]
    )

    # -------------------------------------------------------------------------
    # 7. ALAVANCA 2: Features de Contexto Avançado e Interações Específicas
    # -------------------------------------------------------------------------
    # 1. Eficiência de Conversão Ofensiva (Gols / Finalizações nos últimos 5 jogos)
    finalizacoes_totais = df["FD"] + df["FF"] + df["FT"]
    df["_fin_temp"] = finalizacoes_totais
    fin_5j = grp_atleta["_fin_temp"].transform(lambda x: x.shift(1).rolling(5, min_periods=1).sum()).fillna(0.0)
    gols_5j = grp_atleta["G"].transform(lambda x: x.shift(1).rolling(5, min_periods=1).sum()).fillna(0.0)
    df["taxa_conversao_gols_5j"] = (gols_5j / (fin_5j + 1.0)).fillna(0.0)
    df.drop(columns=["_fin_temp"], inplace=True)

    # 2. Diferencial de Preço em Relação à Média da Posição na Rodada
    media_preco_pos = df.groupby(["ano", "rodada_id", "posicao_id"])["preco_mercado_pre"].transform("mean")
    df["diff_preco_posicao_pre"] = df["preco_mercado_pre"] - media_preco_pos

    # 3. Expectativa de Gols do Time (Encaixe Ataque Clube x Defesa Adversária)
    df["expectativa_gols_time"] = (
        df["clube_media_pontos_conquistados"] * df["opponent_media_pontos_cedidos"]
    ) / 2500.0

    # 4. Potencial de SG para Defensores (Mandante contra Ataque Pouco Produtivo)
    df["potencial_sg_defesa"] = (
        df["home_dummy"] * (1.0 - (df["opponent_media_pontos_cedidos"] / 60.0))
    ).clip(lower=0.0)

    # Remove colunas residuais puramente exploratórias
    df.drop(columns=["estabilidade_11_titular", "variacao_lag1"], inplace=True, errors="ignore")

    # -------------------------------------------------------------------------
    # 8. Asserção de Integridade e Validação
    # -------------------------------------------------------------------------
    total_nulos = int(df.isna().sum().sum())
    if total_nulos > 0:
        raise ValueError(f"Erro no pipeline de Feature Engineering: foram encontrados {total_nulos} valores nulos!")

    return df