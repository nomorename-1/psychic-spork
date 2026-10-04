import json
from pathlib import Path
from uuid import uuid4

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import HTMLResponse

from app.services.ai_adapter import AIVisionAdapter
from app.services.material_service import save_material
from app.services.risk_rule_engine import RiskRuleEngine

BASE_DIR = Path(__file__).resolve().parent.parent
RULES_PATH = BASE_DIR / "config" / "risk_rules.json"
UPLOAD_DIR = BASE_DIR / "data" / "uploads"
rules = json.loads(RULES_PATH.read_text(encoding="utf-8"))
ai_adapter = AIVisionAdapter(enabled=False)
rule_engine = RiskRuleEngine(rules)

app = FastAPI(title="分布式光伏智能核保 - 光伏照片风险识别引擎", version="0.2.0")


@app.get("/", response_class=HTMLResponse)
def home() -> str:
    return """<!doctype html><html lang='zh-CN'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'><title>光伏高风险场景识别</title><style>
    *{box-sizing:border-box}body{max-width:850px;margin:36px auto;padding:0 18px;font-family:Arial,sans-serif;color:#243342;background:#f5f7fa}h1{margin-bottom:8px}.panel{background:#fff;border:1px solid #dce4ea;border-radius:8px;padding:22px;margin-top:20px}label{display:block;font-weight:600;margin:12px 0 6px}input,button{font-size:16px;padding:11px}input{width:100%;border:1px solid #bdc9d3;border-radius:5px}button{width:100%;margin-top:16px;color:#fff;background:#176b87;border:0;border-radius:5px;cursor:pointer}button:disabled{background:#9aa8b1}#result{display:none}.decision{padding:16px;border-left:5px solid #176b87;background:#eef7fa}.decision strong{font-size:24px}.item{padding:13px 0;border-top:1px solid #e4e9ed}.muted{font-size:13px;color:#71808b}.error{padding:12px;color:#9c332b;background:#fff0ee;border-radius:5px}
    </style></head><body><h1>光伏高风险场景识别</h1><p>本阶段仅识别农田、森林、渔光互补等高风险拒保场景。</p><section class='panel'><label>单个材料</label><input id='single' type='file' accept='.jpg,.jpeg,.png,.webp,.pdf,.docx,.txt,.json'><button id='single-btn'>分析单个材料</button><label>材料包（可多选）</label><input id='package' type='file' multiple accept='.jpg,.jpeg,.png,.webp,.pdf,.docx,.txt,.json'><button id='package-btn'>分析材料包</button></section><section id='result' class='panel'></section><script>
    const result=document.getElementById('result');const show=(p)=>{const rules=(p.matched_rules||[]).map(x=>`<div class='item'><b>${x.rule_name}</b><p>${x.evidence}</p><p>${x.explanation}</p><p>置信度：${(x.confidence*100).toFixed(0)}%</p></div>`).join('')||'<p>未命中本阶段拒保规则。</p>';result.innerHTML=`<div class='decision'><div class='muted'>分析结论</div><strong>${p.decision}</strong></div><p>${p.summary}</p><h2>识别结果</h2>${rules}<p class='muted'>AI 模式：${p.ai_mode||'demo'}（当前为演示识别，不代表真实模型结论）</p>`;result.style.display='block'};const run=async(multiple)=>{const input=document.getElementById(multiple?'package':'single');if(!input.files.length){result.innerHTML='<div class="error">请先选择材料。</div>';result.style.display='block';return}const data=new FormData();[...input.files].forEach(f=>data.append(multiple?'files':'file',f));const btn=document.getElementById(multiple?'package-btn':'single-btn');btn.disabled=true;btn.textContent='分析中...';try{const r=await fetch(multiple?'/api/v1/analyze-package':'/api/v1/analyze',{method:'POST',body:data});const p=await r.json();if(!r.ok)throw Error(p.detail||'分析失败');show(p)}catch(e){result.innerHTML=`<div class='error'>${e.message}</div>`;result.style.display='block'}finally{btn.disabled=false;btn.textContent=multiple?'分析材料包':'分析单个材料'}};document.getElementById('single-btn').onclick=()=>run(false);document.getElementById('package-btn').onclick=()=>run(true);
    </script></body></html>"""


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "service": "pv-photo-risk-engine"}


async def analyze_material(file: UploadFile) -> tuple[dict, dict]:
    try:
        material = await save_material(file, UPLOAD_DIR)
        ai_result = ai_adapter.analyze_multimodal(material)
        evaluation = rule_engine.evaluate(material, ai_result)
        material["analysis"] = ai_result
        material["status"] = "risk_detected" if evaluation["matched_rules"] else "review" if evaluation["uncertain_rules"] else "clear"
        return material, evaluation
    except (ValueError, json.JSONDecodeError, OSError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/api/v1/analyze")
async def analyze_photo(file: UploadFile = File(...)) -> dict:
    material, evaluation = await analyze_material(file)
    summary = rule_engine.summarize([evaluation])
    return {**summary, "material_id": material["material_id"], "filename": material["filename"], "evidence": evaluation["matched_rules"] or evaluation["uncertain_rules"], "ai_mode": material["analysis"]["ai_mode"]}


@app.post("/api/v1/analyze-package")
async def analyze_package(files: list[UploadFile] = File(...)) -> dict:
    if not files:
        raise HTTPException(status_code=400, detail="请至少上传一个材料。")
    materials, evaluations = [], []
    for file in files:
        material, evaluation = await analyze_material(file)
        materials.append({"material_id": material["material_id"], "filename": material["filename"], "file_type": material["file_type"], "status": material["status"], "evidence": material["analysis"]["evidence"], "confidence": material["analysis"]["confidence"]})
        evaluations.append(evaluation)
    return {"analysis_id": str(uuid4()), **rule_engine.summarize(evaluations), "materials": materials, "ai_mode": "demo"}


@app.get("/api/v1/rules")
def get_rules() -> dict:
    return rules
