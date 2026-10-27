"""Generates SYNTHETIC hospital data (no real patient or hospital data is used).

Run:  python generate_data.py
Creates: data/hospitals.csv, data/sample_data.csv (daily consumption), data/inventory.csv
"""
import os
import numpy as np
import pandas as pd

rng = np.random.default_rng(42)
OUT = "data"
os.makedirs(OUT, exist_ok=True)

# Fictional hospitals (coordinates are around Chennai, for distance calculation only)
hospitals = pd.DataFrame([
    ("H01", "City General Hospital", 13.0827, 80.2707),
    ("H02", "Greenway Medical Centre", 13.0418, 80.2341),
    ("H03", "Sunrise Multispeciality Hospital", 13.0012, 80.2565),
    ("H04", "Lakeview Hospital", 13.1067, 80.2206),
    ("H05", "Riverside Community Hospital", 12.9249, 80.1000),
    ("H06", "Harmony Care Hospital", 13.1500, 80.3000),
], columns=["hospital_id", "name", "lat", "lon"])
hospitals.to_csv(f"{OUT}/hospitals.csv", index=False)

# medicine: (average daily use for a mid-size hospital, supply lead time in days)
medicines = {
    "Paracetamol 500mg": (120, 3),
    "Amoxicillin 250mg": (60, 4),
    "Insulin Regular": (25, 5),
    "ORS Sachet": (80, 3),
    "Metformin 500mg": (70, 4),
    "Atropine Injection": (8, 6),
}

# (days of stock cover, days until expiry) forced to create realistic scenarios
overrides = {
    ("H01", "Insulin Regular"): (1.5, 150),      # shortage
    ("H03", "Paracetamol 500mg"): (2.0, 200),    # shortage
    ("H05", "ORS Sachet"): (3.0, 180),           # shortage
    ("H02", "Atropine Injection"): (2.5, 120),   # shortage
    ("H04", "Insulin Regular"): (35, 160),       # surplus
    ("H06", "Insulin Regular"): (30, 25),        # surplus, near expiry
    ("H02", "Paracetamol 500mg"): (40, 220),     # surplus
    ("H06", "Paracetamol 500mg"): (30, 20),      # surplus, near expiry
    ("H01", "ORS Sachet"): (38, 210),            # surplus
    ("H04", "ORS Sachet"): (30, 24),             # surplus, near expiry
    ("H04", "Atropine Injection"): (40, 22),     # surplus, near expiry
    ("H06", "Atropine Injection"): (35, 140),    # surplus
}

END = pd.Timestamp("2026-10-26")
dates = pd.date_range(END - pd.Timedelta(days=89), END)
consumption, inventory = [], []
for h in hospitals.hospital_id:
    scale = rng.uniform(0.6, 1.6)
    for med, (base, lead) in medicines.items():
        trend = rng.uniform(-0.002, 0.01)
        t = np.arange(len(dates))
        weekly = 1 + 0.12 * np.sin(2 * np.pi * dates.dayofweek.values / 7)
        mean = base * scale * (1 + trend * t) * weekly
        units = rng.poisson(np.clip(mean, 1, None))
        consumption += [(d.strftime("%Y-%m-%d"), h, med, int(u)) for d, u in zip(dates, units)]
        recent = float(np.mean(units[-14:]))
        cover, exp_days = overrides.get((h, med), (rng.uniform(12, 25), int(rng.integers(60, 300))))
        inventory.append((h, med, int(recent * cover),
                          (END + pd.Timedelta(days=1 + exp_days)).strftime("%Y-%m-%d"), lead))

pd.DataFrame(consumption, columns=["date", "hospital_id", "medicine", "units_used"]).to_csv(f"{OUT}/sample_data.csv", index=False)
pd.DataFrame(inventory, columns=["hospital_id", "medicine", "stock", "expiry_date", "lead_time_days"]).to_csv(f"{OUT}/inventory.csv", index=False)
print("Synthetic data written to", OUT)
