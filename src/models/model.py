"""Módulo de Treinamento, Validação Temporal e Inferência para o Cartola FC / Gato Mestre."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Tuple

import numpy as np
import pandas as pd
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.preprocessing import OrdinalEncoder
from lightgbm import LGBMRegressor
from xgboost import XGBRegressor

from src.features.engineering import COLS_IDS, COL_TARGET, COLS_TO_PREDICT

GLOBAL_SEED = 42


def dividir_dados_temporais(
    df: pd.DataFrame,
    ano_treino_fim: int = 2023,
    ano_val: int = 2024,
    ano_teste: int = 2025,
) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Divide a base respeitando estritamente a causalidade temporal."""
    df_train = df[df["ano"] <= ano_treino_fim].copy()
    df_val = df[df["ano"] == ano_val].copy()
    df_test = df[df["ano"] == ano_teste].copy()

    print("📊 Divisão Temporal dos Dados:")
    print(f"   • Treino (<= {ano_treino_fim}): {len(df_train):,} registros")
    print(f"   • Validação ({ano_val}): {len(df_val):,} registros")
    print(f"   • Teste Out-of-Time ({ano_teste}): {len(df_test):,} registros")

    return df_train, df_val, df_test


def preparar_matrizes_arvores(
    df_train: pd.DataFrame,
    df_val: pd.DataFrame,
    df_test: pd.DataFrame,
    feature_cols: List[str] = COLS_TO_PREDICT,
    cat_cols: List[str] | None = None,
) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, OrdinalEncoder]:
    """Codifica variáveis categóricas via OrdinalEncoder ajustado estritamente no treino."""
    if cat_cols is None:
        cat_cols = ["posicao_id", "status_pre", "status_inicial"]

    cat_cols_presentes = [c for c in cat_cols if c in feature_cols]

    encoder = OrdinalEncoder(
        handle_unknown="use_encoded_value",
        unknown_value=-1,
        encoded_missing_value=-1,
    )

    X_train = df_train[feature_cols].copy()
    X_val = df_val[feature_cols].copy()
    X_test = df_test[feature_cols].copy()

    if cat_cols_presentes:
        X_train[cat_cols_presentes] = encoder.fit_transform(
            X_train[cat_cols_presentes].astype(str)
        )
        X_val[cat_cols_presentes] = encoder.transform(
            X_val[cat_cols_presentes].astype(str)
        )
        X_test[cat_cols_presentes] = encoder.transform(
            X_test[cat_cols_presentes].astype(str)
        )

    return X_train, X_val, X_test, encoder


def treinar_modelo_lightgbm(
    X_train: pd.DataFrame,
    y_train: np.ndarray,
    X_val: pd.DataFrame | None = None,
    y_val: np.ndarray | None = None,
    params: Dict[str, Any] | None = None,
) -> LGBMRegressor:
    """Treina o modelo LightGBM Regressor com hiperparâmetros otimizados."""
    if params is None:
        params = {
            "n_estimators": 150,
            "max_depth": 6,
            "learning_rate": 0.04,
            "num_leaves": 31,
            "subsample": 0.85,
            "colsample_bytree": 0.85,
            "random_state": GLOBAL_SEED,
            "n_jobs": -1,
            "verbose": -1,
        }

    print("\n🚀 Treinando LightGBM Regressor...")
    model = LGBMRegressor(**params)
    if X_val is not None and y_val is not None:
        model.fit(
            X_train,
            y_train,
            eval_set=[(X_val, y_val)],
        )
    else:
        model.fit(X_train, y_train)

    print("✅ Treinamento LightGBM finalizado com sucesso!")
    return model


def treinar_modelo_xgboost(
    X_train: pd.DataFrame,
    y_train: np.ndarray,
    X_val: pd.DataFrame,
    y_val: np.ndarray,
    params: Dict[str, Any] | None = None,
) -> XGBRegressor:
    """Treina o modelo XGBoost Regressor com parada antecipada no conjunto de validação."""
    if params is None:
        params = {
            "n_estimators": 250,
            "max_depth": 5,
            "learning_rate": 0.03,
            "subsample": 0.85,
            "colsample_bytree": 0.85,
            "reg_alpha": 0.1,
            "reg_lambda": 1.0,
            "random_state": GLOBAL_SEED,
            "n_jobs": -1,
            "early_stopping_rounds": 30,
        }

    print("\n🚀 Treinando XGBoost Regressor...")
    model = XGBRegressor(**params)
    model.fit(
        X_train,
        y_train,
        eval_set=[(X_val, y_val)],
        verbose=False,
    )
    print("✅ Treinamento finalizado com sucesso!")
    return model


def avaliar_modelo(
    y_real: np.ndarray,
    y_pred: np.ndarray,
    nome_conjunto: str = "Teste (2025)",
) -> Dict[str, float]:
    """Calcula métricas principais de avaliação de regressão e ranqueamento."""
    mae = mean_absolute_error(y_real, y_pred)
    rmse = np.sqrt(mean_squared_error(y_real, y_pred))
    r2 = r2_score(y_real, y_pred)
    pearson_r = float(np.corrcoef(y_real, y_pred)[0, 1])

    top20_cut = np.quantile(y_real, 0.80)
    mask_top20 = y_real >= top20_cut
    mae_top20 = mean_absolute_error(y_real[mask_top20], y_pred[mask_top20])

    metricas = {
        "MAE": mae,
        "RMSE": rmse,
        "R2": r2,
        "Pearson_r": pearson_r,
        "MAE_Top20%": mae_top20,
    }

    print(f"\n📈 Métricas de Avaliação - {nome_conjunto}:")
    for k, v in metricas.items():
        print(f"   • {k:12s}: {v:.4f}")

    return metricas


def gerar_previsoes_json(
    df_test: pd.DataFrame,
    y_pred: np.ndarray,
    output_path: str = "previsoes.json",
) -> Dict[str, Any]:
    """Consolida as predições no contrato JSON exigido pelo desafio técnico."""
    df_out = df_test.copy()
    df_out["pontos_predito"] = np.round(y_pred, 2)

    # Data da geração em formato ISO 8601 UTC
    now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    previsoes_lista = []
    for _, row in df_out.iterrows():
        previsoes_lista.append(
            {
                "atleta_id": int(row["atleta_id"]),
                "ano": int(row["ano"]),
                "rodada_id": int(row["rodada_id"]),
                "clube_id": int(row["clube_id"]),
                "posicao_id": int(row["posicao_id"]),
                "pontos_predito": float(row["pontos_predito"]),
                "data_predicao": now_iso,
            }
        )

    resultado_json = {"previsoes": previsoes_lista}

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(resultado_json, f, indent=2)

    print(f"\n💾 Arquivo de previsões salvo em: {output_path}")
    print(f"   • Total de previsões geradas: {len(previsoes_lista):,}")

    return resultado_json


def pipeline_completo_modelagem(
    caminho_features: str = "data/processed/dataset_features_modelagem.parquet",
    caminho_saida_json: str = "previsoes.json",
) -> Tuple[LGBMRegressor, Dict[str, float]]:
    """Executa a pipeline completa: carga, split, encode, treino LightGBM, métricas e exportação."""
    df_features = pd.read_parquet(caminho_features)

    # 1. Split Temporal
    df_train, df_val, df_test = dividir_dados_temporais(df_features)

    # 2. Matrizes para Árvores/Boosting
    X_train, X_val, X_test, _ = preparar_matrizes_arvores(
        df_train, df_val, df_test, COLS_TO_PREDICT
    )
    y_train = df_train[COL_TARGET].values
    y_val = df_val[COL_TARGET].values
    y_test = df_test[COL_TARGET].values

    # 3. Treino LightGBM
    modelo = treinar_modelo_lightgbm(X_train, y_train, X_val, y_val)

    # 4. Inferência e Avaliação
    y_pred_test = modelo.predict(X_test)
    metricas = avaliar_modelo(y_test, y_pred_test, "Teste OOS 2025")

    # 5. Exportação no contrato oficial
    gerar_previsoes_json(df_test, y_pred_test, caminho_saida_json)

    return modelo, metricas