"""
04_eda.py
---------
Analyse exploratoire des données (EDA) - génère les figures utilisées dans
le rapport (Ch.4 §4.4 et Ch.5) et dans le dashboard.

Sortie : exports/figures/*.png
"""
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import seaborn as sns
import os

sns.set_theme(style="whitegrid", font_scale=1.05)
PALETTE = ["#2563EB", "#F59E0B", "#10B981", "#EF4444", "#8B5CF6", "#06B6D4", "#EC4899"]
sns.set_palette(PALETTE)

os.makedirs("exports/figures", exist_ok=True)

sales = pd.read_csv("data/sales_clean.csv", parse_dates=["date"])
monthly = pd.read_csv("data/agg_monthly.csv", parse_dates=["date"])


def savefig(name):
    plt.tight_layout()
    plt.savefig(f"exports/figures/{name}.png", dpi=160, bbox_inches="tight")
    plt.close()


# 1. Évolution mensuelle du CA global
global_monthly = monthly.groupby("date")["ca_dh"].sum().reset_index()
plt.figure(figsize=(10, 5))
plt.plot(global_monthly["date"], global_monthly["ca_dh"] / 1000, marker="o", color=PALETTE[0], linewidth=2)
plt.fill_between(global_monthly["date"], global_monthly["ca_dh"] / 1000, alpha=0.15, color=PALETTE[0])
plt.title("Évolution du chiffre d'affaires mensuel (KDH)", fontsize=14, fontweight="bold")
plt.ylabel("CA (milliers DH)")
plt.xlabel("")
plt.xticks(rotation=45)
savefig("01_ca_mensuel_global")

# 2. CA par catégorie (bar horizontal)
cat_ca = sales.groupby("category")["total_dh"].sum().sort_values()
plt.figure(figsize=(9, 5))
bars = plt.barh(cat_ca.index, cat_ca.values / 1e6, color=PALETTE[: len(cat_ca)])
plt.title("Chiffre d'affaires total par catégorie (MDH)", fontsize=14, fontweight="bold")
plt.xlabel("CA (millions DH)")
for b in bars:
    plt.text(b.get_width() + 0.2, b.get_y() + b.get_height() / 2,
              f"{b.get_width():.1f} M", va="center", fontsize=9)
savefig("02_ca_par_categorie")

# 3. Évolution mensuelle par catégorie (lignes)
plt.figure(figsize=(11, 6))
for i, cat in enumerate(monthly["category"].unique()):
    sub = monthly[monthly["category"] == cat]
    plt.plot(sub["date"], sub["ca_dh"] / 1000, label=cat, linewidth=2, color=PALETTE[i % len(PALETTE)])
plt.title("Évolution mensuelle du CA par catégorie (KDH)", fontsize=14, fontweight="bold")
plt.ylabel("CA (milliers DH)")
plt.legend(bbox_to_anchor=(1.02, 1), loc="upper left", fontsize=9)
plt.xticks(rotation=45)
savefig("03_ca_mensuel_par_categorie")

# 4. Top 10 produits par CA
top_products = sales.groupby("product_name")["total_dh"].sum().sort_values(ascending=False).head(10)
plt.figure(figsize=(9, 5.5))
bars = plt.barh(top_products.index[::-1], top_products.values[::-1] / 1000, color=PALETTE[0])
plt.title("Top 10 des produits par chiffre d'affaires (KDH)", fontsize=14, fontweight="bold")
plt.xlabel("CA (milliers DH)")
savefig("04_top10_produits")

# 5. Saisonnalité : CA moyen par mois de l'année (toutes années confondues)
sales["mois"] = sales["date"].dt.month
season = sales.groupby("mois")["total_dh"].sum()
mois_labels = ["Jan", "Fév", "Mar", "Avr", "Mai", "Jun", "Jul", "Aoû", "Sep", "Oct", "Nov", "Déc"]
plt.figure(figsize=(10, 5))
colors = [PALETTE[3] if v == season.max() else PALETTE[0] for v in season.values]
plt.bar([mois_labels[m - 1] for m in season.index], season.values / 1000, color=colors)
plt.title("Saisonnalité des ventes : CA cumulé par mois calendaire (KDH)", fontsize=14, fontweight="bold")
plt.ylabel("CA (milliers DH)")
savefig("05_saisonnalite_mensuelle")

# 6. Répartition géographique
city_ca = sales.groupby("city")["total_dh"].sum().sort_values(ascending=False)
plt.figure(figsize=(9, 5))
bars = plt.bar(city_ca.index, city_ca.values / 1e6, color=PALETTE[2])
plt.title("Chiffre d'affaires par ville (MDH)", fontsize=14, fontweight="bold")
plt.ylabel("CA (millions DH)")
plt.xticks(rotation=30)
savefig("06_ca_par_ville")

# 7. Heatmap mois x catégorie (intensité des ventes)
pivot = sales.pivot_table(index="category", columns="mois", values="total_dh", aggfunc="sum", fill_value=0)
pivot.columns = [mois_labels[m - 1] for m in pivot.columns]
plt.figure(figsize=(11, 5.5))
sns.heatmap(pivot / 1000, cmap="Blues", annot=False, cbar_kws={"label": "CA (KDH)"})
plt.title("Intensité des ventes par catégorie et par mois (KDH)", fontsize=14, fontweight="bold")
plt.ylabel("")
plt.xlabel("")
savefig("07_heatmap_categorie_mois")

print("Figures générées dans exports/figures/")
for f in sorted(os.listdir("exports/figures")):
    print(" -", f)
