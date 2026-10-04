from typing import Any


class RiskRuleEngine:
    def __init__(self, rules: dict[str, Any]) -> None:
        self.rules = rules["rules"]

    def evaluate(self, material: dict[str, Any], ai_result: dict[str, Any]) -> dict[str, Any]:
        labels = set(ai_result.get("scene_labels", []))
        text = material.get("content", {}).get("text", "")
        searchable = f"{material.get('filename', '')} {text}"
        matched, uncertain = [], []
        for rule in self.rules:
            if material["file_type"] not in rule["source_types"]:
                continue
            label_hit = labels.intersection(rule["trigger_labels"])
            keyword_hit = next((word for word in rule["trigger_keywords"] if word in searchable), None)
            if label_hit or keyword_hit:
                confidence = float(ai_result.get("confidence", 0.92 if keyword_hit else 0.0))
                evidence = keyword_hit or next(iter(label_hit))
                item = {"rule_id": rule["rule_id"], "rule_name": rule["rule_name"], "decision": rule["decision"], "risk_level": rule["risk_level"], "confidence": confidence, "evidence": f"{material['filename']} 命中：{evidence}", "explanation": rule["explanation"]}
                (matched if confidence >= rule["confidence_threshold"] else uncertain).append(item)
        return {"matched_rules": matched, "uncertain_rules": uncertain}

    @staticmethod
    def summarize(results: list[dict[str, Any]]) -> dict[str, Any]:
        matched = [item for result in results for item in result["matched_rules"]]
        uncertain = [item for result in results for item in result["uncertain_rules"]]
        if matched:
            return {"decision": "拒保", "risk_level": "high", "summary": "材料中识别到本阶段明确拒保场景。", "matched_rules": matched}
        if uncertain:
            return {"decision": "建议人工复核", "risk_level": "unknown", "summary": "发现疑似高风险场景，但识别置信度不足。", "matched_rules": uncertain}
        return {"decision": "未发现本阶段高风险拒保场景", "risk_level": "normal", "summary": "当前材料未命中本阶段拒保规则。", "matched_rules": []}
