import json
from pathlib import Path

from app.schemas import RiskInput, RiskOutput


class ScoringEngine:
    def __init__(self, config_dir: Path):
        self.rules = json.loads((config_dir / "disaster_rules.json").read_text(encoding="utf-8"))
        self.thresholds = json.loads((config_dir / "component_thresholds.json").read_text(encoding="utf-8"))
        if self.rules["version"] != self.thresholds["version"]:
            raise ValueError("Configuration versions must match")
        weights = [item["weight"] for item in self.rules["disasters"].values()]
        if any(w <= 0 for w in weights) or abs(sum(weights) - 1) > 1e-8:
            raise ValueError("Disaster weights must be positive and sum to one")
        for item in self.rules["disasters"].values():
            if any(w <= 0 for w in item["factors"].values()) or abs(sum(item["factors"].values()) - 1) > 1e-8:
                raise ValueError("Factor weights must be positive and sum to one")
        for exposure in self.rules["regions"].values():
            if set(exposure) != set(self.rules["disasters"]) or any(not 0 <= v <= 100 for v in exposure.values()):
                raise ValueError("Region exposure must cover all disasters within 0-100")

    def level(self, score):
        if score is None:
            return "资料不足"
        limits = self.rules["risk_levels"]
        return "低" if score <= limits["low_max"] else "中" if score <= limits["medium_max"] else "高"

    def evaluate(self, request: RiskInput) -> RiskOutput:
        payload = request.model_dump()
        region = None if request.location is None else f"{request.location.province.strip()}-{request.location.city.strip()}"
        exposure = self.rules["regions"].get(region)
        missing = [] if exposure is not None else ["location" if region is None else "region_exposure"]
        breakdown = []
        for disaster, rule in self.rules["disasters"].items():
            absent, evidence, resilience = [], [], 0.0
            for field, weight in rule["factors"].items():
                section, key = field.split(".")
                value = payload[section][key]
                if value is None:
                    absent.append(field)
                    continue
                if isinstance(value, bool):
                    score = self.thresholds["boolean_scores"][str(value).lower()]
                    evidence.append(f"{field}：{'是' if value else '否'}")
                else:
                    threshold = self.thresholds["thresholds"][field]
                    score = min(100, value / threshold * 100)
                    evidence.append(f"{field}：{value}；演示参考值：{threshold}")
                resilience += score * weight
            # Incomplete evidence is never averaged into a reassuring score.
            resilience = None if absent else resilience
            hazard = None if exposure is None else exposure[disaster]
            risk = None if resilience is None or hazard is None else hazard * (1 - resilience / 100)
            if hazard is not None:
                evidence.append(f"地区灾害程度：{hazard}（演示数据）")
            missing.extend(absent)
            breakdown.append(dict(disaster=disaster, name=rule["name"], exposure_score=hazard,
                                  resilience_score=resilience, risk_score=risk,
                                  risk_level=self.level(risk), evidence=evidence, missing_fields=absent))
        highlighted = [item["name"] for item in breakdown if item["risk_level"] == "高"]
        complete_resilience = all(item["resilience_score"] is not None for item in breakdown)
        total_resilience = sum(item["resilience_score"] * self.rules["disasters"][item["disaster"]]["weight"] for item in breakdown) if complete_resilience else None
        total_risk = None if missing else sum(item["risk_score"] * self.rules["disasters"][item["disaster"]]["weight"] for item in breakdown)
        # A known high-risk disaster raises the overall level even if its weight is small.
        level = "高" if highlighted else "资料不足" if missing else self.level(total_risk)
        for item in breakdown:
            for field in ("resilience_score", "risk_score"):
                if item[field] is not None:
                    item[field] = round(item[field], 2)
        return RiskOutput(
            project_id=request.project_id, rule_version=self.rules["version"],
            assessment_status="资料不足，需复核" if missing else "评估完成",
            disaster_resilience_score=None if total_resilience is None else round(total_resilience, 2),
            claim_risk_score=None if total_risk is None else round(total_risk, 2), risk_level=level,
            decision_support="资料不足，需复核" if missing else "高风险，建议人工复核" if highlighted else "建议补充防护措施并复核" if level == "中" else "可供核保人员参考",
            highlighted_risks=highlighted, risk_breakdown=breakdown,
            required_follow_up_materials=[self.rules["materials"][field] for field in dict.fromkeys(missing)],
            evidence_references=request.evidence_references,
            data_source={"mode": "demo", "region": region, "region_source": self.rules["source"], "threshold_source": self.thresholds["source"]},
            limitations=["仅表示相对风险，不代表真实出险概率、赔款或加费比例。", "演示阈值及地区数据尚未校准，不可直接作为正式核保依据。", "输入资料由提交方提供，本服务未验证检测报告或现场情况。"],
        )
