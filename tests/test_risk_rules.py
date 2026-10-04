import json
import unittest
from pathlib import Path

from app.services.risk_rule_engine import RiskRuleEngine


class RiskRuleEngineTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        rules = json.loads((Path(__file__).parents[1] / "config" / "risk_rules.json").read_text(encoding="utf-8"))
        cls.engine = RiskRuleEngine(rules)

    def evaluate(self, filename, text, labels=None, confidence=0.92):
        material = {"filename": filename, "file_type": "txt", "content": {"text": text}}
        ai = {"scene_labels": labels or [], "confidence": confidence}
        return self.engine.evaluate(material, ai)

    def test_farmland_is_decline(self):
        result = self.evaluate("备案证.txt", "项目类型：农光")
        self.assertTrue(result["matched_rules"])

    def test_fishery_is_decline(self):
        result = self.evaluate("备案证.txt", "渔光互补")
        self.assertTrue(result["matched_rules"])

    def test_normal_material_is_clear(self):
        result = self.evaluate("普通屋顶.txt", "普通屋顶光伏")
        summary = self.engine.summarize([result])
        self.assertEqual(summary["decision"], "未发现本阶段高风险拒保场景")

    def test_low_confidence_requires_review(self):
        result = self.evaluate("全景.jpg", "", labels=["farmland"], confidence=0.4)
        summary = self.engine.summarize([result])
        self.assertEqual(summary["decision"], "建议人工复核")


if __name__ == "__main__":
    unittest.main()
