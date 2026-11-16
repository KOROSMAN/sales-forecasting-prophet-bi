"""
01_build_catalog.py
--------------------
Construit le catalogue produits complet de KARAMCASA utilisé pour le projet.

Méthodologie (voir Chapitre 3 du rapport) :
- Une partie réelle (~140 produits) a été collectée directement depuis le site
  officiel https://karamcasa.ma (catégories, noms de produits, prix en DH),
  fichier `data/real_products_raw.csv`.
- Le catalogue complet du site compte plus de 2 200 références. Pour disposer
  d'un jeu de données exploitable pour la modélisation tout en respectant la
  distribution réelle des prix et des marques observée par catégorie, le
  catalogue réel est étendu statistiquement (produits synthétiques générés à
  partir des lois de distribution empiriques par catégorie : marque, gamme de
  prix). Cette limite est documentée dans le rapport (section 5.4).

Sortie : data/catalog.csv (product_id, name, category, brand, price_dh, is_real)
"""
import pandas as pd
import numpy as np
import re
import json

np.random.seed(42)

RAW_PATH = "data/real_products_raw.csv"
OUT_PATH = "data/catalog.csv"

# Nombre cible de produits par catégorie dans le catalogue final (échantillon
# représentatif du vrai catalogue, dimensionné pour l'analyse et le dashboard)
TARGET_COUNTS = {
    "Computing & IT": 90,
    "Security & Surveillance": 110,
    "Printing": 55,
    "Networking": 45,
    "Data Storage": 35,
    "Audio-Visual": 30,
    "Telephony": 35,
}

KNOWN_BRANDS = {
    "Computing & IT": ["Asus", "HP", "Lenovo", "Dell", "Logitech", "Eaton", "Kaspersky"],
    "Security & Surveillance": ["Dahua", "Hikvision", "Ezviz", "Imou"],
    "Printing": ["Canon", "Brother", "Epson"],
    "Networking": ["TP-Link", "Ugreen", "Huawei", "Dahua", "Hikvision", "Grandstream", "Ruijie"],
    "Audio-Visual": ["DSPPA", "Epson", "Revolution Galaxy", "Dell"],
    "Telephony": ["Samsung", "Apple", "Huawei", "Motorola", "Grandstream"],
    # Catégorie non accessible lors du scraping (page indisponible) : gamme
    # reconstituée à partir de la nomenclature standard du secteur.
    "Data Storage": ["Western Digital", "Seagate", "Kingston", "SanDisk", "Synology", "Transcend"],
}

DATA_STORAGE_TEMPLATES = [
    ("{brand} SSD 2.5in SATA {size}", [128, 256, 512, 1024, 2048], (180, 2200)),
    ("{brand} NVMe M.2 SSD {size}", [256, 512, 1024, 2048], (250, 2600)),
    ("{brand} HDD Interne 3.5in {size}", [1, 2, 4, 8], (450, 2400)),
    ("{brand} HDD Externe Portable 2.5in {size}", [1, 2, 4], (400, 1300)),
    ("{brand} Cle USB 3.0 {size}", [16, 32, 64, 128, 256], (35, 320)),
    ("{brand} Carte Micro SD {size}", [32, 64, 128, 256], (60, 380)),
    ("{brand} NAS 2-Baies Reseau {size}", [0], (2800, 6500)),
]


def slug(text):
    return re.sub(r"[^a-zA-Z0-9]+", "-", text.strip().lower()).strip("-")


def load_real():
    df = pd.read_csv(RAW_PATH)
    df["is_real"] = True

    def guess_brand(name, cat):
        for b in KNOWN_BRANDS.get(cat, []):
            if b.lower().split()[0] in name.lower():
                return b
        return name.split()[0]

    df["brand"] = df.apply(lambda r: guess_brand(r["name"], r["category"]), axis=1)
    return df[["name", "category", "brand", "price_dh", "is_real"]]


def fit_lognormal(prices):
    logp = np.log(prices)
    return logp.mean(), max(logp.std(), 0.15)


def generate_synthetic_generic(category, brand_list, prices, n):
    """Génère des produits synthétiques calés sur la distribution réelle des prix."""
    mu, sigma = fit_lognormal(prices)
    sigma = min(sigma, 0.55)  # évite une queue de distribution irréaliste
    price_cap = float(np.max(prices)) * 1.15
    price_floor = max(float(np.min(prices)) * 0.7, 10.0)
    rows = []
    descriptors = ["Pro", "Lite", "Plus", "Max", "Standard", "Compact", "Business", "Home", "Advanced"]
    specs = ["", " Wi-Fi", " 4K", " Full HD", " USB-C", " Bluetooth", " Duplex", " PoE", " Gigabit"]
    for i in range(n):
        brand = np.random.choice(brand_list)
        desc = np.random.choice(descriptors)
        spec = np.random.choice(specs)
        model = f"{np.random.randint(100, 9999)}{np.random.choice(['', 'X', 'A', 'S', 'G'])}"
        name = f"{brand} {model} {desc} {category.split(' ')[0]}{spec}".replace("  ", " ").strip()
        price = float(np.round(np.exp(np.random.normal(mu, sigma)), 2))
        price = min(max(price, price_floor), price_cap)
        rows.append({"name": name, "category": category, "brand": brand,
                      "price_dh": price, "is_real": False})
    return rows


def generate_data_storage(n):
    rows = []
    brands = KNOWN_BRANDS["Data Storage"]
    for i in range(n):
        tpl, sizes, price_range = DATA_STORAGE_TEMPLATES[np.random.randint(len(DATA_STORAGE_TEMPLATES))]
        brand = np.random.choice(brands)
        size = np.random.choice(sizes)
        size_str = "" if size == 0 else (f"{size}GB" if size < 100 or tpl.find("HDD") == -1 and size < 100 else f"{size}GB")
        if "HDD" in tpl and size in [1, 2, 4, 8]:
            size_str = f"{size}TB"
        name = tpl.format(brand=brand, size=size_str).replace("  ", " ").strip()
        price = float(np.round(np.random.uniform(*price_range), 2))
        rows.append({"name": name, "category": "Data Storage", "brand": brand,
                      "price_dh": price, "is_real": False})
    return rows


def main():
    real_df = load_real()
    all_rows = [real_df]

    for cat, target in TARGET_COUNTS.items():
        if cat == "Data Storage":
            n_needed = target
            synth = generate_data_storage(n_needed)
            all_rows.append(pd.DataFrame(synth))
            continue
        real_cat = real_df[real_df["category"] == cat]
        n_real = len(real_cat)
        n_needed = max(target - n_real, 0)
        if n_needed > 0:
            prices = real_cat["price_dh"].values if n_real > 3 else real_df["price_dh"].values
            synth = generate_synthetic_generic(cat, KNOWN_BRANDS[cat], prices, n_needed)
            all_rows.append(pd.DataFrame(synth))

    catalog = pd.concat(all_rows, ignore_index=True)
    catalog = catalog.drop_duplicates(subset=["name"]).reset_index(drop=True)
    catalog.insert(0, "product_id", ["P" + str(i + 1).zfill(4) for i in range(len(catalog))])
    catalog["price_dh"] = catalog["price_dh"].round(2)
    catalog.to_csv(OUT_PATH, index=False)

    summary = catalog.groupby("category").agg(
        n_produits=("product_id", "count"),
        n_reels=("is_real", "sum"),
        prix_moyen=("price_dh", "mean"),
        prix_min=("price_dh", "min"),
        prix_max=("price_dh", "max"),
    ).round(1)
    print(f"Catalogue final : {len(catalog)} produits")
    print(summary)
    with open("data/catalog_summary.json", "w") as f:
        json.dump(json.loads(summary.reset_index().to_json(orient="records")), f, indent=2, ensure_ascii=False)


if __name__ == "__main__":
    main()
