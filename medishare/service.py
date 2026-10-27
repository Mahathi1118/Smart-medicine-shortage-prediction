"""Loads data and builds the dashboard payload."""
import os
import pandas as pd
from .predictor import predict_all
from .recommender import recommend, near_expiry_alerts


def build_dashboard(data_dir="data"):
    hospitals = pd.read_csv(os.path.join(data_dir, "hospitals.csv"))
    consumption = pd.read_csv(os.path.join(data_dir, "sample_data.csv"))
    inventory = pd.read_csv(os.path.join(data_dir, "inventory.csv"))

    pred = predict_all(consumption, inventory)
    names = hospitals.set_index("hospital_id")["name"].to_dict()
    pred["hospital"] = pred["hospital_id"].map(names)
    pred["_r"] = pred["risk"].map({"HIGH": 0, "MEDIUM": 1, "LOW": 2})
    shown = pred.sort_values(["_r", "days_of_stock"]).drop(columns="_r")

    alerts = near_expiry_alerts(pred.drop(columns="_r"))
    alerts = alerts.assign(hospital=alerts.hospital_id.map(names))
    return {
        "note": "Decision-support only. Synthetic data. Final decisions rest with authorised hospital staff.",
        "predictions": shown.to_dict(orient="records"),
        "recommendations": recommend(pred.drop(columns="_r"), hospitals),
        "near_expiry": alerts.to_dict(orient="records"),
    }
