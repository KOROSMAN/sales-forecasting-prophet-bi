"""
02_generate_sales.py
---------------------
Génère un historique de commandes simulé mais réaliste pour KARAMCASA,
sur la base du catalogue produits réel/étendu (data/catalog.csv).

Hypothèses de simulation (documentées au rapport, Ch.3 §3.3 et Ch.5 §5.4) :
- Période : 24 mois (sept. 2024 -> août 2026), fréquence journalière.
- Poids de popularité différents par catégorie (Security & Surveillance et
  Computing & IT dominent le CA, cohérent avec les tailles de catégories
  observées sur le site réel : 627 et 484 produits respectivement).
- Saisonnalité :
    * Rentrée scolaire/universitaire (sept.) : pic Computing & IT
    * Ramadan (mois lunaire variable) : léger ralentissement puis reprise à l'Aïd
    * Black Friday (fin nov.) : pic toutes catégories
    * Fêtes de fin d'année (déc.) : pic Telephony / Audio-Visual
    * Été (juil-août) : creux général
- Tendance de fond légèrement croissante (croissance e-commerce).
- Bruit aléatoire jour à jour + variation du nombre d'articles par commande.

Sortie : data/sales.csv (order_id, date, product_id, category, brand,
                          quantity, unit_price, total_dh, city)
"""
import numpy as np
import pandas as pd

np.random.seed(7)

CATALOG_PATH = "data/catalog.csv"
OUT_PATH = "data/sales.csv"

START_DATE = "2024-09-01"
END_DATE = "2026-08-31"

CITIES = ["Casablanca", "Rabat", "Marrakech", "Tanger", "Fes", "Agadir",
          "Oujda", "Kenitra", "Tetouan", "Meknes"]
CITY_WEIGHTS = [0.34, 0.14, 0.10, 0.08, 0.07, 0.07, 0.05, 0.05, 0.05, 0.05]

# Popularité relative par catégorie (part du volume de commandes), calée sur
# la taille relative des catégories réelles du site (produits en catalogue)
CATEGORY_WEIGHT = {
    "Security & Surveillance": 0.27,
    "Computing & IT": 0.22,
    "Printing": 0.15,
    "Networking": 0.12,
    "Telephony": 0.12,
    "Data Storage": 0.07,
    "Audio-Visual": 0.05,
}

BASE_ORDERS_PER_DAY = 14  # commande moyenne / jour en base


def seasonal_multiplier(date, category):
    m = date.month
    mult = 1.0
    # Rentrée scolaire : boost Computing & IT et Networking en sept
    if m == 9:
        if category in ("Computing & IT", "Networking"):
            mult *= 1.55
        else:
            mult *= 1.15
    # Black Friday fin novembre
    if m == 11 and date.day >= 20:
        mult *= 1.8
    # Fêtes fin d'année : Telephony / Audio-Visual
    if m == 12:
        if category in ("Telephony", "Audio-Visual"):
            mult *= 1.6
        else:
            mult *= 1.2
    # Creux estival
    if m in (7, 8):
        mult *= 0.7
    # Sécurité: leger pic printemps (installations avant été - villas/résidences secondaires)
    if category == "Security & Surveillance" and m in (4, 5, 6):
        mult *= 1.2
    return mult


def trend_multiplier(date, start, end):
    total_days = (end - start).days
    progressed = (date - start).days / max(total_days, 1)
    return 1.0 + 0.35 * progressed  # +35% de croissance sur la période


def weekday_multiplier(date):
    # Vendredi/Samedi un peu plus calmes (usage B2B dominant), lundi actif
    wd = date.weekday()  # 0=lundi
    factors = [1.10, 1.05, 1.0, 1.0, 0.95, 0.75, 0.7]
    return factors[wd]


def main():
    catalog = pd.read_csv(CATALOG_PATH)
    dates = pd.date_range(START_DATE, END_DATE, freq="D")
    start, end = dates[0], dates[-1]

    categories = list(CATEGORY_WEIGHT.keys())
    cat_probs = np.array(list(CATEGORY_WEIGHT.values()))
    cat_probs = cat_probs / cat_probs.sum()

    products_by_cat = {c: catalog[catalog["category"] == c] for c in categories}

    rows = []
    order_id = 1
    for date in dates:
        season = np.mean([seasonal_multiplier(date, c) for c in categories])
        trend = trend_multiplier(date, start, end)
        wd = weekday_multiplier(date)
        expected_orders = BASE_ORDERS_PER_DAY * season * trend * wd
        n_orders = np.random.poisson(max(expected_orders, 1))

        for _ in range(n_orders):
            cat_p = np.array([CATEGORY_WEIGHT[c] * seasonal_multiplier(date, c) for c in categories])
            cat_p = cat_p / cat_p.sum()
            category = np.random.choice(categories, p=cat_p)
            prod_pool = products_by_cat[category]
            product = prod_pool.sample(1).iloc[0]
            quantity = int(np.clip(np.random.poisson(1.4) + 1, 1, 6))
            city = np.random.choice(CITIES, p=CITY_WEIGHTS)
            noise = np.random.normal(1.0, 0.03)
            unit_price = round(float(product["price_dh"]) * max(noise, 0.85), 2)

            rows.append({
                "order_id": f"ORD{order_id:06d}",
                "date": date.strftime("%Y-%m-%d"),
                "product_id": product["product_id"],
                "product_name": product["name"],
                "category": category,
                "brand": product["brand"],
                "quantity": quantity,
                "unit_price_dh": unit_price,
                "total_dh": round(unit_price * quantity, 2),
                "city": city,
            })
            order_id += 1

    sales = pd.DataFrame(rows)
    sales.to_csv(OUT_PATH, index=False)

    print(f"Commandes générées : {len(sales):,}")
    print(f"CA total simulé : {sales['total_dh'].sum():,.0f} DH")
    print(f"Période : {sales['date'].min()} -> {sales['date'].max()}")
    print(sales.groupby("category")["total_dh"].sum().sort_values(ascending=False))


if __name__ == "__main__":
    main()
