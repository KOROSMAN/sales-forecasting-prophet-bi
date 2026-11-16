"""
03_clean_aggregate.py
----------------------
Nettoyage et agrégation des données de ventes pour l'EDA, la modélisation de
prévision et le dashboard.

Étapes de nettoyage (Ch.4 §4.3 du rapport) :
- Vérification des types (dates, numériques)
- Détection de doublons (order_id + product_id)
- Détection de valeurs manquantes / aberrantes (prix <=0, quantité <=0)
- Recalcul du total (contrôle de cohérence quantité * prix_unitaire)

Sorties :
- data/sales_clean.csv         : ventes nettoyées, granularité ligne de commande
- data/agg_daily.csv           : CA / quantité agrégés par jour et catégorie
- data/agg_monthly.csv         : CA / quantité agrégés par mois et catégorie
- data/kpis.json               : indicateurs clés pour le dashboard
- data/quality_report.json     : rapport qualité données (annexe rapport)
"""
import pandas as pd
import numpy as np
import json

SALES_PATH = "data/sales.csv"
OUT_CLEAN = "data/sales_clean.csv"
OUT_DAILY = "data/agg_daily.csv"
OUT_MONTHLY = "data/agg_monthly.csv"
OUT_KPIS = "data/kpis.json"
OUT_QUALITY = "data/quality_report.json"


def main():
    df = pd.read_csv(SALES_PATH, parse_dates=["date"])
    n_initial = len(df)

    quality = {"n_lignes_initiales": int(n_initial)}

    # Doublons
    n_dup = df.duplicated(subset=["order_id", "product_id"]).sum()
    quality["doublons_detectes"] = int(n_dup)
    df = df.drop_duplicates(subset=["order_id", "product_id"])

    # Valeurs manquantes
    quality["valeurs_manquantes_par_colonne"] = df.isna().sum().to_dict()
    df = df.dropna(subset=["date", "product_id", "quantity", "unit_price_dh"])

    # Valeurs aberrantes : quantité ou prix <= 0
    n_bad = ((df["quantity"] <= 0) | (df["unit_price_dh"] <= 0)).sum()
    quality["lignes_aberrantes_supprimees"] = int(n_bad)
    df = df[(df["quantity"] > 0) & (df["unit_price_dh"] > 0)]

    # Contrôle de cohérence du total
    recompute = (df["quantity"] * df["unit_price_dh"]).round(2)
    mismatch = (recompute - df["total_dh"]).abs() > 0.05
    quality["incoherences_total_corrigees"] = int(mismatch.sum())
    df.loc[mismatch, "total_dh"] = recompute[mismatch]

    quality["n_lignes_finales"] = int(len(df))
    quality["periode_debut"] = str(df["date"].min().date())
    quality["periode_fin"] = str(df["date"].max().date())

    df.to_csv(OUT_CLEAN, index=False)

    # Agrégation journalière par catégorie
    daily = (df.groupby([pd.Grouper(key="date", freq="D"), "category"])
                .agg(ca_dh=("total_dh", "sum"), quantite=("quantity", "sum"),
                     n_commandes=("order_id", "nunique"))
                .reset_index())
    daily.to_csv(OUT_DAILY, index=False)

    # Agrégation mensuelle par catégorie
    monthly = (df.groupby([pd.Grouper(key="date", freq="MS"), "category"])
                 .agg(ca_dh=("total_dh", "sum"), quantite=("quantity", "sum"),
                      n_commandes=("order_id", "nunique"))
                 .reset_index())
    monthly.to_csv(OUT_MONTHLY, index=False)

    # KPIs globaux
    total_ca = df["total_dh"].sum()
    n_commandes = df["order_id"].nunique()
    panier_moyen = df.groupby("order_id")["total_dh"].sum().mean()
    top_categorie = df.groupby("category")["total_dh"].sum().idxmax()
    top_produit = df.groupby("product_name")["total_dh"].sum().idxmax()
    top_ville = df.groupby("city")["total_dh"].sum().idxmax()

    kpis = {
        "ca_total_dh": round(float(total_ca), 2),
        "n_commandes": int(n_commandes),
        "n_lignes_vente": int(len(df)),
        "panier_moyen_dh": round(float(panier_moyen), 2),
        "categorie_top_ca": top_categorie,
        "produit_top_ca": top_produit,
        "ville_top_ca": top_ville,
        "periode_debut": quality["periode_debut"],
        "periode_fin": quality["periode_fin"],
    }
    with open(OUT_KPIS, "w", encoding="utf-8") as f:
        json.dump(kpis, f, indent=2, ensure_ascii=False)
    with open(OUT_QUALITY, "w", encoding="utf-8") as f:
        json.dump(quality, f, indent=2, ensure_ascii=False)

    print("=== Rapport qualité ===")
    print(json.dumps(quality, indent=2, ensure_ascii=False))
    print("\n=== KPIs ===")
    print(json.dumps(kpis, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
