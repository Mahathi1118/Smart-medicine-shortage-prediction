"""Run with:  python -m unittest discover tests"""
import os
import sys
import unittest

import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app import create_app
from medishare.predictor import forecast_daily, predict_all, risk_level
from medishare.recommender import haversine_km, near_expiry_alerts, recommend

DATA = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")


def load():
    return (pd.read_csv(f"{DATA}/hospitals.csv"), pd.read_csv(f"{DATA}/sample_data.csv"),
            pd.read_csv(f"{DATA}/inventory.csv"))


class TestPredictor(unittest.TestCase):
    def test_forecast_length_and_non_negative(self):
        s = pd.Series(range(60), index=pd.date_range("2026-01-01", periods=60))
        f = forecast_daily(s)
        self.assertEqual(len(f), 14)
        self.assertTrue((f >= 0).all())

    def test_risk_levels(self):
        self.assertEqual(risk_level(2, 4), "HIGH")
        self.assertEqual(risk_level(6, 4), "MEDIUM")
        self.assertEqual(risk_level(20, 4), "LOW")

    def test_known_shortage_detected(self):
        _, cons, inv = load()
        pred = predict_all(cons, inv)
        row = pred[(pred.hospital_id == "H01") & (pred.medicine == "Insulin Regular")].iloc[0]
        self.assertEqual(row.risk, "HIGH")


class TestRecommender(unittest.TestCase):
    def setUp(self):
        self.hosp, cons, inv = load()
        self.pred = predict_all(cons, inv)

    def test_distance_zero_for_same_point(self):
        self.assertAlmostEqual(haversine_km(13.0, 80.0, 13.0, 80.0), 0.0)

    def test_donor_never_pushed_into_shortage(self):
        recs = recommend(self.pred, self.hosp)
        given = {}
        for r in recs:
            for s in r["suppliers"]:
                key = (s["hospital_id"], r["medicine"])
                given[key] = given.get(key, 0) + s["units"]
        for (hid, med), units in given.items():
            row = self.pred[(self.pred.hospital_id == hid) & (self.pred.medicine == med)].iloc[0]
            self.assertGreaterEqual(row.stock - units, row.forecast_14d * 1.2 - 1)

    def test_near_expiry_used_first(self):
        recs = recommend(self.pred, self.hosp)
        r = next(x for x in recs if x["hospital_id"] == "H01" and x["medicine"] == "Insulin Regular")
        self.assertTrue(r["suppliers"][0]["near_expiry"])

    def test_near_expiry_alerts_found(self):
        self.assertGreater(len(near_expiry_alerts(self.pred)), 0)


class TestApi(unittest.TestCase):
    def test_dashboard_endpoint(self):
        client = create_app().test_client()
        self.assertEqual(client.get("/").status_code, 200)
        res = client.get("/api/dashboard")
        self.assertEqual(res.status_code, 200)
        self.assertIn("recommendations", res.get_json())


if __name__ == "__main__":
    unittest.main()
