"""
Synthetic data generator for StockSense.
All data produced here is SYNTHETIC — clearly labelled as such.
Run: python data/generate_synthetic.py
"""
import random
import math
import csv
from pathlib import Path
from datetime import date, timedelta

SEED = 42
random.seed(SEED)

SKUS = [
    {"sku": "WATER-500",  "base_demand": 10, "trend": 0.01,  "promo_days": [30, 60]},
    {"sku": "JUICE-1L",   "base_demand": 5,  "trend": 0.005, "promo_days": [15]},
    {"sku": "SNACK-BAR",  "base_demand": 20, "trend": 0.02,  "promo_days": [45, 75]},
]

START = date(2026, 1, 1)
DAYS  = 180

output = Path(__file__).parent / "sample"
output.mkdir(exist_ok=True)

rows = []
anomaly_truth = []

for sku_cfg in SKUS:
    sku = sku_cfg["sku"]
    base = sku_cfg["base_demand"]
    trend = sku_cfg["trend"]
    promo_days = set(sku_cfg["promo_days"])
    on_hand = base * 30

    for i in range(DAYS):
        d = START + timedelta(days=i)
        weekday_factor = 1.0 + 0.2 * math.sin(2 * math.pi * d.weekday() / 7)
        trend_factor   = 1 + trend * i
        promo_flag     = 1 if i in promo_days else 0
        promo_boost    = 2.5 if promo_flag else 1.0
        demand         = base * weekday_factor * trend_factor * promo_boost
        noise          = random.gauss(0, base * 0.1)
        units_sold     = max(0.0, round(demand + noise, 1))

        anomaly_class = None

        # Inject a data error on day 50 for first SKU
        if sku == "WATER-500" and i == 50:
            units_sold = -5.0
            anomaly_class = "data_error"

        # Inject stockout suppression on days 100-105 for second SKU
        if sku == "JUICE-1L" and 100 <= i <= 105:
            units_sold = 0.0
            on_hand = 0.0
            anomaly_class = "stockout_censored"

        rows.append({
            "date": d.isoformat(),
            "sku": sku,
            "units_sold": units_sold,
            "on_hand": round(on_hand, 1),
            "promo_flag": promo_flag,
        })

        if anomaly_class:
            anomaly_truth.append({"date": d.isoformat(), "sku": sku, "class": anomaly_class})

        on_hand = max(0.0, on_hand - units_sold)

# Write sales.csv
with open(output / "sales.csv", "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=["date", "sku", "units_sold", "on_hand", "promo_flag"])
    w.writeheader()
    w.writerows(rows)

# Write sku_params.csv
sku_params = [
    {
        "sku": "WATER-500", "name": "Water 500 ml", "lead_time_days": 5,
        "lead_time_std_days": 1.0, "unit_cost": 8.0, "order_cost": 50,
        "holding_cost_per_unit_per_year": 2.0, "stockout_penalty_per_unit": 6.0,
        "moq": 24, "pack_size": 12, "max_storage": "", "service_level": 0.95,
        "on_hand": 120, "on_order": 0,
    },
    {
        "sku": "JUICE-1L", "name": "Orange Juice 1 L", "lead_time_days": 7,
        "lead_time_std_days": 2.0, "unit_cost": 15.0, "order_cost": 80,
        "holding_cost_per_unit_per_year": 3.0, "stockout_penalty_per_unit": 10.0,
        "moq": 12, "pack_size": 6, "max_storage": "", "service_level": 0.95,
        "on_hand": 60, "on_order": 0,
    },
    {
        "sku": "SNACK-BAR", "name": "Snack Bar", "lead_time_days": 3,
        "lead_time_std_days": 0.5, "unit_cost": 3.0, "order_cost": 30,
        "holding_cost_per_unit_per_year": 1.0, "stockout_penalty_per_unit": 4.0,
        "moq": 48, "pack_size": 24, "max_storage": "", "service_level": 0.90,
        "on_hand": 200, "on_order": 0,
    },
]
with open(output / "sku_params.csv", "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(sku_params[0].keys()))
    w.writeheader()
    w.writerows(sku_params)

# Write anomaly_ground_truth.csv
with open(output / "anomaly_ground_truth.csv", "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=["date", "sku", "class"])
    w.writeheader()
    w.writerows(anomaly_truth)

print(f"Generated {len(rows)} rows for {len(SKUS)} SKUs -> {output}")
print("NOTE: All data is SYNTHETIC and clearly labelled as such.")
