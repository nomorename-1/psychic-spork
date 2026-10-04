import copy
import json
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

from app.main import app, engine

BASE = Path(__file__).resolve().parent.parent


class RiskTests(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)
        self.sample = json.loads((BASE / "data/samples/normal.json").read_text(encoding="utf-8"))

    def evaluate(self, payload=None):
        response = self.client.post("/api/v1/quantify-risk", json=payload or self.sample)
        self.assertEqual(response.status_code, 200)
        return response.json()

    def test_normal_and_endpoints(self):
        result = self.evaluate()
        self.assertEqual(result["risk_level"], "低")
        self.assertEqual(len(result["risk_breakdown"]), 5)
        self.assertEqual(result["disaster_resilience_score"], 100)
        for path in ("/health", "/api/v1/config/disaster-rules", "/api/v1/config/component-thresholds"):
            self.assertEqual(self.client.get(path).status_code, 200)

    def test_high_wind_not_hidden_by_average(self):
        self.sample["component"]["wind_load_pa"] = 1
        self.sample["mounting_system"]["secure"] = False
        self.sample["building"]["roof_sound"] = False
        result = self.evaluate()
        self.assertLess(result["claim_risk_score"], 60)
        self.assertEqual(result["risk_level"], "高")
        self.assertIn("风灾", result["highlighted_risks"])

    def test_snow_drainage_lightning_hail(self):
        cases = [("snow", "component", "snow_load_pa", 1), ("flood", "protection", "drainage_good", False), ("lightning", "protection", "lightning_protection", False), ("hail", "component", "hail_diameter_mm", 1)]
        for disaster, section, field, value in cases:
            with self.subTest(disaster=disaster):
                payload = copy.deepcopy(self.sample)
                payload[section][field] = value
                result = self.evaluate(payload)
                item = next(x for x in result["risk_breakdown"] if x["disaster"] == disaster)
                self.assertGreater(item["risk_score"], 0)

    def test_missing_and_unknown_region(self):
        for field in ("component", "location"):
            payload = copy.deepcopy(self.sample)
            del payload[field]
            result = self.evaluate(payload)
            self.assertIsNone(result["claim_risk_score"])
            self.assertEqual(result["assessment_status"], "资料不足，需复核")
            self.assertTrue(result["required_follow_up_materials"])
        self.sample["location"]["city"] = "未知地区"
        self.assertTrue(all(x["exposure_score"] is None for x in self.evaluate()["risk_breakdown"]))

    def test_known_high_risk_survives_missing_data(self):
        self.sample["protection"]["drainage_good"] = False
        self.sample["protection"]["equipment_height_m"] = 0
        del self.sample["component"]
        result = self.evaluate()
        self.assertEqual(result["risk_level"], "高")
        self.assertEqual(result["assessment_status"], "资料不足，需复核")

    def test_monotonicity(self):
        from app.schemas import RiskInput
        self.sample["component"]["wind_load_pa"] = 500
        first = self.evaluate()["risk_breakdown"][0]["risk_score"]
        self.sample["component"]["wind_load_pa"] = 1000
        second = self.evaluate()["risk_breakdown"][0]["risk_score"]
        self.assertLess(second, first)
        local = copy.deepcopy(engine)
        local.rules["regions"]["浙江-宁波"]["wind"] = 100
        self.assertGreater(local.evaluate(RiskInput(**self.sample)).risk_breakdown[0].risk_score, second)

    def test_invalid_inputs(self):
        for section, field, value in [(None, "installed_capacity_kw", -1), ("component", "wind_load_pa", 0), ("protection", "drainage_good", "false"), ("protection", "equipment_height_m", -1), (None, "unexpected", 1)]:
            payload = copy.deepcopy(self.sample)
            (payload if section is None else payload[section])[field] = value
            self.assertEqual(self.client.post("/api/v1/quantify-risk", json=payload).status_code, 422)


if __name__ == "__main__":
    unittest.main()
