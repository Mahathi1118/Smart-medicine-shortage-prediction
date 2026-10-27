"""Hospital recommendation and near-expiry detection."""
import math
import numpy as np


def haversine_km(lat1, lon1, lat2, lon2):
    r = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = p2 - p1, math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def near_expiry_alerts(pred, near_expiry_days=30):
    """Stock expiring soon that the hospital is unlikely to use in time."""
    df = pred[(pred.days_to_expiry >= 0) & (pred.days_to_expiry <= near_expiry_days)].copy()
    df["units_likely_wasted"] = (
        (df.stock - df.avg_daily_forecast * df.days_to_expiry).clip(lower=0).round().astype(int)
    )
    return df[df.units_likely_wasted > 0]


def recommend(pred, hospitals, safety_factor=1.2, min_shelf_days=7, near_expiry_days=30):
    """For each at-risk hospital-medicine, suggest donor hospitals.

    Rules:
      * A donor only gives what exceeds its own 14-day forecast x safety_factor,
        so the donor is never pushed into a shortage.
      * Batches with fewer than `min_shelf_days` left are not shipped.
      * Near-expiry stock is used first (reduces wastage), then nearest hospital.
      * Most urgent requests (least days of stock) are served first.
    """
    info = hospitals.set_index("hospital_id")
    surplus = {}
    for r in pred.itertuples():
        surplus[(r.hospital_id, r.medicine)] = int(max(0, np.floor(r.stock - r.forecast_14d * safety_factor)))

    at_risk = pred[pred.risk.isin(["HIGH", "MEDIUM"])].sort_values("days_of_stock")
    results = []
    for r in at_risk.itertuples():
        need = int(np.ceil(max(0.0, r.forecast_14d * safety_factor - r.stock)))
        if need == 0:
            continue
        me = info.loc[r.hospital_id]
        cands = []
        for c in pred[(pred.medicine == r.medicine) & (pred.hospital_id != r.hospital_id)].itertuples():
            if c.days_to_expiry < min_shelf_days:
                continue
            d = info.loc[c.hospital_id]
            dist = haversine_km(me.lat, me.lon, d.lat, d.lon)
            near = c.days_to_expiry <= near_expiry_days
            cands.append((not near, dist, c, near))
        cands.sort(key=lambda x: (x[0], x[1]))

        remaining, suppliers = need, []
        for _, dist, c, near in cands:
            avail = surplus[(c.hospital_id, c.medicine)]
            if avail <= 0 or remaining <= 0:
                continue
            qty = min(avail, remaining)
            surplus[(c.hospital_id, c.medicine)] -= qty
            remaining -= qty
            suppliers.append({
                "hospital_id": c.hospital_id,
                "hospital": str(info.loc[c.hospital_id]["name"]),
                "units": int(qty),
                "distance_km": round(dist, 1),
                "expiry_date": c.expiry_date,
                "near_expiry": bool(near),
            })
        results.append({
            "hospital_id": r.hospital_id,
            "hospital": str(me["name"]),
            "medicine": r.medicine,
            "risk": r.risk,
            "days_of_stock": r.days_of_stock,
            "units_needed": need,
            "units_covered": need - remaining,
            "fully_covered": remaining == 0,
            "suppliers": suppliers,
        })
    return results
