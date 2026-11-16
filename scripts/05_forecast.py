"""
05_forecast.py
---------------
Modélisation de la prévision des ventes par catégorie avec Prophet.

Méthodologie (Ch.3 §3.3 et Ch.4 §4.4 du rapport) :
- Granularité hebdomadaire (plus de points que le mensuel, moins bruité que
  le journalier) du chiffre d'affaires par catégorie.
- Split train / test : les 8 dernières semaines sont retenues comme jeu de
  test pour évaluer la qualité de la prévision (MAE, RMSE, MAPE).
- Un modèle Prophet est entraîné par catégorie (saisonnalité annuelle +
  hebdomadaire, changepoints sur la tendance).
- Une fois validé, le modèle est ré-entraîné sur l'ensemble des données pour
  produire une prévision opérationnelle à horizon 12 semaines (~3 mois),
  utilisée dans le dashboard pour anticiper les besoins de réassort.

Sorties :
- data/forecast_history.csv   : série réelle + prévision in-sample/test par catégorie
- data/forecast_future.csv    : prévision à 12 semaines par catégorie
- data/forecast_metrics.json  : MAE / RMSE / MAPE par catégorie
- exports/figures/08_forecast_<categorie>.png (une figure par catégorie)
"""
import pandas as pd
import numpy as np
import json
import logging
import os
import warnings

logging.getLogger("cmdstanpy").setLevel(logging.WARNING)
logging.getLogger("prophet").setLevel(logging.WARNING)
warnings.filterwarnings("ignore")

from prophet import Prophet
import matplotlib.pyplot as plt
import seaborn as sns

sns.set_theme(style="whitegrid", font_scale=1.0)
PALETTE = ["#2563EB", "#F59E0B", "#10B981", "#EF4444", "#8B5CF6", "#06B6D4", "#EC4899"]

os.makedirs("exports/figures", exist_ok=True)

TEST_WEEKS = 8
HORIZON_WEEKS = 12

sales = pd.read_csv("data/sales_clean.csv", parse_dates=["date"])
categories = sorted(sales["category"].unique())

all_history = []
all_future = []
metrics = {}

for i, cat in enumerate(categories):
    sub = sales[sales["category"] == cat]
    weekly = (sub.set_index("date")["total_dh"]
                 .resample("W-MON").sum()
                 .reset_index()
                 .rename(columns={"date": "ds", "total_dh": "y"}))
    weekly = weekly[weekly["y"] > 0].reset_index(drop=True)
    if len(weekly) < 20:
        continue

    train = weekly.iloc[:-TEST_WEEKS]
    test = weekly.iloc[-TEST_WEEKS:]

    m_eval = Prophet(yearly_seasonality=True, weekly_seasonality=False,
                      daily_seasonality=False, seasonality_mode="multiplicative",
                      changepoint_prior_scale=0.2)
    m_eval.fit(train)
    future_test = m_eval.make_future_dataframe(periods=TEST_WEEKS, freq="W-MON")
    fc_test = m_eval.predict(future_test)
    pred_test = fc_test.set_index("ds").loc[test["ds"], "yhat"].values
    y_true = test["y"].values

    mae = float(np.mean(np.abs(y_true - pred_test)))
    rmse = float(np.sqrt(np.mean((y_true - pred_test) ** 2)))
    mape = float(np.mean(np.abs((y_true - pred_test) / np.where(y_true == 0, 1, y_true))) * 100)

    # Agrégation mensuelle du test (réel vs prévu) : lisse le bruit hebdomadaire,
    # pertinent pour un usage "planification des achats mensuels"
    test_df = pd.DataFrame({"ds": test["ds"].values, "y_true": y_true, "y_pred": pred_test})
    test_df["mois"] = test_df["ds"].dt.to_period("M")
    monthly_test = test_df.groupby("mois")[["y_true", "y_pred"]].sum()
    mape_month = float(np.mean(np.abs((monthly_test["y_true"] - monthly_test["y_pred"]) /
                                       monthly_test["y_true"].replace(0, np.nan))) * 100)

    metrics[cat] = {"MAE_dh_hebdo": round(mae, 0), "RMSE_dh_hebdo": round(rmse, 0),
                     "MAPE_hebdo_pct": round(mape, 1), "MAPE_mensuel_pct": round(mape_month, 1),
                     "n_semaines_train": len(train), "n_semaines_test": len(test)}

    # Historique complet (réel) + prévision in-sample sur la période de test, pour graphe
    hist_df = weekly.copy()
    hist_df["categorie"] = cat
    hist_df["type"] = "reel"
    test_pred_df = pd.DataFrame({"ds": test["ds"].values, "y": pred_test, "categorie": cat, "type": "prevision_test"})
    all_history.append(pd.concat([hist_df.assign(y=hist_df["y"]).drop(columns=[]), test_pred_df], ignore_index=True))

    # Modèle final ré-entraîné sur toutes les données -> prévision future
    m_final = Prophet(yearly_seasonality=True, weekly_seasonality=False,
                       daily_seasonality=False, seasonality_mode="multiplicative",
                       changepoint_prior_scale=0.2)
    m_final.fit(weekly)
    future = m_final.make_future_dataframe(periods=HORIZON_WEEKS, freq="W-MON")
    fc = m_final.predict(future)
    fc_future = fc[fc["ds"] > weekly["ds"].max()][["ds", "yhat", "yhat_lower", "yhat_upper"]].copy()
    fc_future["categorie"] = cat
    all_future.append(fc_future)

    # Figure par catégorie
    plt.figure(figsize=(10, 5))
    plt.plot(weekly["ds"], weekly["y"] / 1000, label="CA réel (simulé)", color=PALETTE[0], linewidth=1.8)
    plt.plot(fc_future["ds"], fc_future["yhat"] / 1000, label="Prévision (12 sem.)",
              color=PALETTE[3], linewidth=2, linestyle="--")
    plt.fill_between(fc_future["ds"], fc_future["yhat_lower"] / 1000, fc_future["yhat_upper"] / 1000,
                      color=PALETTE[3], alpha=0.15, label="Intervalle de confiance")
    plt.title(f"Prévision des ventes — {cat} (KDH/semaine)", fontsize=13, fontweight="bold")
    plt.ylabel("CA hebdomadaire (KDH)")
    plt.legend()
    plt.xticks(rotation=45)
    plt.tight_layout()
    safe_name = cat.lower().replace(" & ", "_").replace(" ", "_")
    plt.savefig(f"exports/figures/08_forecast_{safe_name}.png", dpi=160, bbox_inches="tight")
    plt.close()

    print(f"[{cat}] MAPE hebdo={mape:.1f}%  MAPE mensuel={mape_month:.1f}%  MAE={mae:,.0f} DH")

pd.concat(all_history, ignore_index=True).to_csv("data/forecast_history.csv", index=False)
pd.concat(all_future, ignore_index=True).to_csv("data/forecast_future.csv", index=False)
with open("data/forecast_metrics.json", "w", encoding="utf-8") as f:
    json.dump(metrics, f, indent=2, ensure_ascii=False)

print("\nMétriques sauvegardées dans data/forecast_metrics.json")
