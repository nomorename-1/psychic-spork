from pathlib import Path
from typing import Any


class AIVisionAdapter:
    """统一多模态模型边界；默认使用明确标记的 Demo 识别。"""

    def __init__(self, enabled: bool = False) -> None:
        self.enabled = enabled

    def analyze_image(self, image_path: Path, filename: str = "") -> dict[str, Any]:
        if self.enabled:
            raise NotImplementedError("请接入企业批准的视觉大模型。")
        return self._demo_detection(filename, source="image")

    def analyze_text(self, text: str, filename: str = "") -> dict[str, Any]:
        if self.enabled:
            raise NotImplementedError("请接入企业批准的文本/多模态大模型。")
        return self._demo_detection(f"{filename} {text}", source="text")

    def analyze_document(self, text: str, filename: str = "") -> dict[str, Any]:
        return self.analyze_text(text, filename)

    def analyze_multimodal(self, material: dict[str, Any]) -> dict[str, Any]:
        if material.get("file_type") == "image":
            return self.analyze_image(Path(material["stored_path"]), material["filename"])
        return self.analyze_document(material.get("content", {}).get("text", ""), material["filename"])

    @staticmethod
    def _demo_detection(value: str, source: str) -> dict[str, Any]:
        text = value.lower()
        aliases = {
            "farmland": ["农田", "农光", "农业光伏"],
            "forest": ["森林", "林地", "林光", "森林光伏"],
            "fishery": ["渔业", "鱼塘", "渔光", "渔光互补"],
            "water": ["水面", "湖泊", "河流", "池塘", "沿海", "涉水"],
            "tidal_flat": ["滩涂"],
            "centralized": ["集中式"],
        }
        labels = [label for label, words in aliases.items() if any(word in text for word in words)]
        return {"ai_mode": "demo", "status": "simulated", "scene_labels": labels, "risk_labels": labels, "evidence": [{"source": source, "description": f"Demo 模式根据文件名/文本命中：{label}"} for label in labels], "confidence": 0.92 if labels else 0.0}
