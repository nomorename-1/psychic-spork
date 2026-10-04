from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import HTMLResponse

from app.schemas import RiskInput, RiskOutput
from app.scoring_engine import ScoringEngine

engine = ScoringEngine(Path(__file__).resolve().parent.parent / "config")
app = FastAPI(title="组件抗灾能力与出险风险量化", version="0.1.0", docs_url="/api-docs")


@app.get("/", include_in_schema=False)
@app.get("/docs", include_in_schema=False, response_class=HTMLResponse)
def home():
    return HTMLResponse((Path(__file__).resolve().parent / "index.html").read_text(encoding="utf-8"))


@app.get("/health", summary="检查服务状态", tags=["服务状态"])
def health():
    return {"status": "ok", "service": "pv-disaster-risk", "rule_version": engine.rules["version"]}


@app.post("/api/v1/quantify-risk", response_model=RiskOutput, summary="评估抗灾能力与出险风险", tags=["风险评估"])
def quantify_risk(request: RiskInput):
    return engine.evaluate(request)


@app.get("/api/v1/config/disaster-rules", summary="查看灾害评估规则", tags=["评估规则"])
def disaster_rules():
    return engine.rules


@app.get("/api/v1/config/component-thresholds", summary="查看组件参考要求", tags=["评估规则"])
def component_thresholds():
    return engine.thresholds
