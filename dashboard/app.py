"""
Dashboard KARAMCASA — Pilotage des ventes & prévision de la demande
Projet de Fin de Stage — 4ème année IADATA

Lancement : streamlit run app.py
"""
import json
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"

st.set_page_config(
    page_title="KARAMCASA | Dashboard Ventes & Prévision",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------------------------------------------------------------------------
# Style
# ---------------------------------------------------------------------------
PRIMARY = "#2563EB"
ACCENT = "#F59E0B"
GOOD = "#10B981"
BAD = "#EF4444"
CAT_COLORS = ["#2563EB", "#F59E0B", "#10B981", "#EF4444", "#8B5CF6", "#06B6D4", "#EC4899"]

st.markdown(f"""
<style>
    .main {{ background-color: #F8FAFC; }}
    .block-container {{ padding-top: 1.6rem; padding-bottom: 2rem; max-width: 1300px; }}
    h1, h2, h3 {{ color: #0F172A; }}
    div[data-testid="stMetric"] {{
        background: white;
        border: 1px solid #E2E8F0;
        border-radius: 14px;
        padding: 16px 18px 12px 18px;
        box-shadow: 0 1px 3px rgba(15, 23, 42, 0.04);
    }}
    div[data-testid="stMetricLabel"] {{ color: #64748B; font-weight: 600; }}
    div[data-testid="stMetricValue"] {{ color: #0F172A; font-size: 1.35rem; white-space: nowrap; }}
    .kc-header {{
        background: linear-gradient(135deg, {PRIMARY} 0%, #1E40AF 100%);
        padding: 22px 28px;
        border-radius: 16px;
        color: white;
        margin-bottom: 22px;
    }}
    .kc-header h1 {{ color: white; margin: 0; font-size: 1.7rem; }}
    .kc-header p {{ color: #DBEAFE; margin: 4px 0 0 0; font-size: 0.95rem; }}
    .kc-badge {{
        display: inline-block; background: rgba(255,255,255,0.18); border-radius: 8px;
        padding: 3px 10px; font-size: 0.78rem; margin-top: 8px;
    }}
    section[data-testid="stSidebar"] {{ background-color: #0F172A; }}
    section[data-testid="stSidebar"] * {{ color: #E2E8F0 !important; }}
    section[data-testid="stSidebar"] .stSlider label, section[data-testid="stSidebar"] .stMultiSelect label {{
        color: #94A3B8 !important;
    }}
</style>
""", unsafe_allow_html=True)


@st.cache_data
def load_data():
    sales = pd.read_csv(DATA_DIR / "sales_clean.csv", parse_dates=["date"])
    catalog = pd.read_csv(DATA_DIR / "catalog.csv")
    daily = pd.read_csv(DATA_DIR / "agg_daily.csv", parse_dates=["date"])
    monthly = pd.read_csv(DATA_DIR / "agg_monthly.csv", parse_dates=["date"])
    with open(DATA_DIR / "kpis.json", encoding="utf-8") as f:
        kpis = json.load(f)
    with open(DATA_DIR / "quality_report.json", encoding="utf-8") as f:
        quality = json.load(f)
    fc_future = pd.read_csv(DATA_DIR / "forecast_future.csv", parse_dates=["ds"])
    fc_hist = pd.read_csv(DATA_DIR / "forecast_history.csv", parse_dates=["ds"])
    with open(DATA_DIR / "forecast_metrics.json", encoding="utf-8") as f:
        fc_metrics = json.load(f)
    return sales, catalog, daily, monthly, kpis, quality, fc_future, fc_hist, fc_metrics


sales, catalog, daily, monthly, kpis, quality, fc_future, fc_hist, fc_metrics = load_data()
categories_all = sorted(sales["category"].unique())

# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------
with st.sidebar:
    st.markdown("### 🛒 KARAMCASA")
    st.caption("Distributeur informatique & sécurité — Casablanca")
    st.divider()
    st.markdown("**Filtres**")

    min_date, max_date = sales["date"].min().date(), sales["date"].max().date()
    date_range = st.slider("Période", min_value=min_date, max_value=max_date,
                            value=(min_date, max_date), format="MMM YYYY")

    selected_cats = st.multiselect("Catégories", categories_all, default=categories_all)

    st.divider()
    st.caption("📁 Données : catalogue réel (scrapé sur karamcasa.ma) "
               "+ historique de ventes simulé à des fins pédagogiques (PFE 4A IADATA).")
    st.caption(f"Dernière mise à jour des données : {quality['periode_fin']}")

mask = (
    (sales["date"].dt.date >= date_range[0])
    & (sales["date"].dt.date <= date_range[1])
    & (sales["category"].isin(selected_cats))
)
f_sales = sales[mask]

# ---------------------------------------------------------------------------
# Header
# ---------------------------------------------------------------------------
st.markdown(f"""
<div class="kc-header">
    <h1>📊 Pilotage des ventes & prévision de la demande</h1>
    <p>Tableau de bord d'aide à la décision — KARAMCASA (e-commerce IT & sécurité)</p>
    <span class="kc-badge">Projet de Fin de Stage · 4ème année IADATA · {kpis['periode_debut']} → {kpis['periode_fin']}</span>
</div>
""", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# KPI row
# ---------------------------------------------------------------------------
total_ca_f = f_sales["total_dh"].sum()
n_cmd_f = f_sales["order_id"].nunique()
panier_moyen_f = f_sales.groupby("order_id")["total_dh"].sum().mean() if n_cmd_f else 0
top_cat_f = f_sales.groupby("category")["total_dh"].sum().idxmax() if len(f_sales) else "-"

c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("Chiffre d'affaires", f"{total_ca_f/1e6:,.2f} M DH")
c2.metric("Commandes", f"{n_cmd_f:,}")
c3.metric("Panier moyen", f"{panier_moyen_f:,.0f} DH")
c4.metric("Catégorie leader", top_cat_f)
c5.metric("Références au catalogue", f"{len(catalog):,}")

st.write("")

# ---------------------------------------------------------------------------
# Tabs
# ---------------------------------------------------------------------------
tab1, tab2, tab3, tab4 = st.tabs(["📈 Vue d'ensemble", "🗂️ Analyse par catégorie",
                                    "🔮 Prévision de la demande", "📦 Catalogue produits"])

# --- TAB 1 : Vue d'ensemble ---
with tab1:
    colA, colB = st.columns([2, 1])

    with colA:
        m = monthly[monthly["category"].isin(selected_cats)]
        m_global = m.groupby("date", as_index=False)["ca_dh"].sum()
        fig = px.area(m_global, x="date", y="ca_dh", title="Évolution mensuelle du chiffre d'affaires")
        fig.update_traces(line_color=PRIMARY, fillcolor="rgba(37,99,235,0.15)")
        fig.update_layout(yaxis_title="CA (DH)", xaxis_title="", height=380,
                           plot_bgcolor="white", margin=dict(t=50, l=10, r=10, b=10))
        st.plotly_chart(fig, use_container_width=True)

    with colB:
        cat_ca = f_sales.groupby("category")["total_dh"].sum().sort_values(ascending=False)
        fig2 = px.pie(values=cat_ca.values, names=cat_ca.index, hole=0.55,
                       color_discrete_sequence=CAT_COLORS, title="Répartition du CA par catégorie")
        fig2.update_layout(height=380, margin=dict(t=50, l=10, r=10, b=10),
                            legend=dict(orientation="h", yanchor="bottom", y=-0.35))
        st.plotly_chart(fig2, use_container_width=True)

    colC, colD = st.columns(2)
    with colC:
        top_products = (f_sales.groupby("product_name")["total_dh"].sum()
                                 .sort_values(ascending=False).head(10).sort_values())
        fig3 = px.bar(x=top_products.values, y=top_products.index, orientation="h",
                       title="Top 10 produits par chiffre d'affaires",
                       labels={"x": "CA (DH)", "y": ""}, color_discrete_sequence=[PRIMARY])
        fig3.update_layout(height=420, plot_bgcolor="white", margin=dict(t=50, l=10, r=10, b=10))
        st.plotly_chart(fig3, use_container_width=True)

    with colD:
        city_ca = f_sales.groupby("city")["total_dh"].sum().sort_values(ascending=False)
        fig4 = px.bar(x=city_ca.index, y=city_ca.values, title="Chiffre d'affaires par ville",
                       labels={"x": "", "y": "CA (DH)"}, color_discrete_sequence=[ACCENT])
        fig4.update_layout(height=420, plot_bgcolor="white", margin=dict(t=50, l=10, r=10, b=10))
        st.plotly_chart(fig4, use_container_width=True)

# --- TAB 2 : Analyse par catégorie ---
with tab2:
    m = monthly[monthly["category"].isin(selected_cats)]
    fig5 = px.line(m, x="date", y="ca_dh", color="category",
                    title="Évolution mensuelle du CA par catégorie",
                    color_discrete_sequence=CAT_COLORS, markers=True)
    fig5.update_layout(height=440, plot_bgcolor="white", yaxis_title="CA (DH)", xaxis_title="",
                        margin=dict(t=50, l=10, r=10, b=10))
    st.plotly_chart(fig5, use_container_width=True)

    col1, col2 = st.columns(2)
    with col1:
        pivot = f_sales.copy()
        pivot["mois"] = pivot["date"].dt.month
        mois_labels = ["Jan", "Fév", "Mar", "Avr", "Mai", "Jun", "Jul", "Aoû", "Sep", "Oct", "Nov", "Déc"]
        heat = pivot.pivot_table(index="category", columns="mois", values="total_dh", aggfunc="sum", fill_value=0)
        heat.columns = [mois_labels[c - 1] for c in heat.columns]
        fig6 = px.imshow(heat, color_continuous_scale="Blues", aspect="auto",
                          title="Intensité des ventes par catégorie et mois calendaire")
        fig6.update_layout(height=380, margin=dict(t=50, l=10, r=10, b=10))
        st.plotly_chart(fig6, use_container_width=True)

    with col2:
        cat_summary = (f_sales.groupby("category")
                                .agg(CA_DH=("total_dh", "sum"),
                                     Commandes=("order_id", "nunique"),
                                     Quantite=("quantity", "sum"))
                                .sort_values("CA_DH", ascending=False))
        cat_summary["Panier_moyen_DH"] = (cat_summary["CA_DH"] / cat_summary["Commandes"]).round(0)
        cat_summary["CA_DH"] = cat_summary["CA_DH"].round(0)
        st.markdown("**Synthèse par catégorie**")
        st.dataframe(cat_summary, use_container_width=True, height=380)

# --- TAB 3 : Prévision ---
with tab3:
    st.markdown("Modèle **Prophet** entraîné par catégorie sur l'historique hebdomadaire du CA "
                "(saisonnalité annuelle, tendance). Horizon de prévision : **12 semaines** (~3 mois).")

    cat_choice = st.selectbox("Choisir une catégorie", categories_all)

    hist_cat = fc_hist[fc_hist["categorie"] == cat_choice]
    future_cat = fc_future[fc_future["categorie"] == cat_choice]
    reel = hist_cat[hist_cat["type"] == "reel"]

    fig7 = go.Figure()
    fig7.add_trace(go.Scatter(x=reel["ds"], y=reel["y"], name="CA réel (hebdo)",
                               line=dict(color=PRIMARY, width=2)))
    fig7.add_trace(go.Scatter(x=future_cat["ds"], y=future_cat["yhat"], name="Prévision",
                               line=dict(color=BAD, width=2, dash="dash")))
    fig7.add_trace(go.Scatter(
        x=pd.concat([future_cat["ds"], future_cat["ds"][::-1]]),
        y=pd.concat([future_cat["yhat_upper"], future_cat["yhat_lower"][::-1]]),
        fill="toself", fillcolor="rgba(239,68,68,0.12)", line=dict(color="rgba(0,0,0,0)"),
        name="Intervalle de confiance", showlegend=True))
    fig7.update_layout(title=f"Prévision des ventes — {cat_choice}", height=440,
                        plot_bgcolor="white", yaxis_title="CA hebdomadaire (DH)", xaxis_title="",
                        margin=dict(t=50, l=10, r=10, b=10))
    st.plotly_chart(fig7, use_container_width=True)

    met = fc_metrics.get(cat_choice, {})
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("MAPE mensuel (test)", f"{met.get('MAPE_mensuel_pct', '-')} %")
    m2.metric("MAPE hebdomadaire (test)", f"{met.get('MAPE_hebdo_pct', '-')} %")
    m3.metric("MAE hebdomadaire", f"{met.get('MAE_dh_hebdo', 0):,.0f} DH")
    m4.metric("CA prévu (12 sem.)", f"{future_cat['yhat'].sum():,.0f} DH")

    st.caption("⚠️ Le MAPE hebdomadaire est plus élevé pour les catégories à faible volume "
               "(ex. Audio-Visual, Networking) : la variance relative est mécaniquement plus forte "
               "sur de petits volumes. Le MAPE mensuel, plus stable, est recommandé pour la "
               "planification des achats — voir Chapitre 5 du rapport.")

    with st.expander("Voir le tableau de prévision détaillé (12 semaines)"):
        show = future_cat[["ds", "yhat", "yhat_lower", "yhat_upper"]].copy()
        show.columns = ["Semaine", "Prévision (DH)", "Borne basse", "Borne haute"]
        for c in show.columns[1:]:
            show[c] = show[c].round(0)
        st.dataframe(show, use_container_width=True, hide_index=True)

    st.markdown("##### Comparatif des modèles par catégorie")
    metrics_df = pd.DataFrame(fc_metrics).T.reset_index().rename(columns={"index": "Catégorie"})
    st.dataframe(metrics_df, use_container_width=True, hide_index=True)

# --- TAB 4 : Catalogue ---
with tab4:
    st.markdown(f"**{len(catalog)} produits** au catalogue "
                f"({int(catalog['is_real'].sum())} collectés réellement sur karamcasa.ma, "
                f"le reste généré statistiquement pour compléter les catégories — voir méthodologie, Ch.3).")

    col1, col2, col3 = st.columns(3)
    with col1:
        cat_filter = st.multiselect("Catégorie", sorted(catalog["category"].unique()),
                                     default=sorted(catalog["category"].unique()), key="cat_catalog")
    with col2:
        search = st.text_input("Recherche produit / marque")
    with col3:
        only_real = st.checkbox("Uniquement produits réels (scrapés)", value=False)

    cat_view = catalog[catalog["category"].isin(cat_filter)]
    if search:
        cat_view = cat_view[cat_view["name"].str.contains(search, case=False) |
                             cat_view["brand"].str.contains(search, case=False)]
    if only_real:
        cat_view = cat_view[cat_view["is_real"]]

    st.dataframe(
        cat_view[["product_id", "name", "category", "brand", "price_dh", "is_real"]]
        .rename(columns={"product_id": "Réf.", "name": "Produit", "category": "Catégorie",
                          "brand": "Marque", "price_dh": "Prix (DH)", "is_real": "Réel"})
        .sort_values("Prix (DH)", ascending=False),
        use_container_width=True, height=480, hide_index=True,
    )

st.divider()
st.caption("Dashboard réalisé dans le cadre du Projet de Fin de Stage — 4ème année IADATA — KARAMCASA, Casablanca.")
