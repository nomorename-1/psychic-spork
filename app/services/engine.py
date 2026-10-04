import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from PIL import Image, ImageStat

from app.services.ai_adapter import AIVisionAdapter


class RiskEngine:
    def __init__(self, rules_path: Path) -> None:
        self.rules = json.loads(rules_path.read_text(encoding="utf-8"))
        self.ai_adapter = AIVisionAdapter(enabled=False)

    def analyze(
        self, image_path: Path, photo_id: str, project_id: str, original_filename: str
    ) -> dict[str, Any]:
        with Image.open(image_path) as image:
            width, height = image.size
            brightness = sum(ImageStat.Stat(image.convert("L")).mean) / 1

        findings = []
        for rule in self.rules["rules"]:
            if rule["id"] == "image_quality_low_resolution" and min(width, height) < rule["threshold"]:
                findings.append(self._finding(rule, f"照片尺寸为 {width}×{height}，小于建议值。"))
            if rule["id"] == "image_quality_too_dark" and brightness < rule["threshold"]:
                findings.append(self._finding(rule, f"照片平均亮度为 {brightness:.1f}，现场可能过暗。"))

        ai_result = self.ai_adapter.analyze(image_path)
        risk_level = self._risk_level(findings)
        return {
            "photo_id": photo_id,
            "project_id": project_id,
            "original_filename": original_filename,
            "analyzed_at": datetime.now(timezone.utc).isoformat(),
            "decision": self._decision(risk_level),
            "risk_level": risk_level,
            "summary": self._summary(risk_level, findings),
            "image": {"width": width, "height": height, "brightness": round(brightness, 1)},
            "findings": findings,
            "ai": ai_result,
        }

    @staticmethod
    def _finding(rule: dict[str, Any], detail: str) -> dict[str, Any]:
        return {
            "rule_id": rule["id"],
            "category": rule["category"],
            "level": rule["level"],
            "title": rule["title"],
            "detail": detail,
            "recommendation": rule["recommendation"],
        }

    @staticmethod
    def _risk_level(findings: list[dict[str, Any]]) -> str:
        levels = {finding["level"] for finding in findings}
        if "high" in levels:
            return "high"
        if "medium" in levels:
            return "medium"
        if "low" in levels:
            return "low"
        return "normal"

    @staticmethod
    def _decision(level: str) -> str:
        return {"high": "人工复核", "medium": "补充材料", "low": "提示关注", "normal": "初步通过"}[level]

    @staticmethod
    def _summary(level: str, findings: list[dict[str, Any]]) -> str:
        if not findings:
            return "未发现基础规则风险。注意：Demo 不等同于正式核保结论。"
        return f"发现 {len(findings)} 项基础规则提示，建议结合人工核验。"

