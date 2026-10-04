# 组件抗灾能力与出险风险量化

独立 FastAPI 演示服务，评估风灾、积雪、冰雹、暴雨进水和雷击。输入结构化资料，输出评分、判断依据和补充材料清单。中文评估页面为 `/` 或 `/docs`，开发者接口页面为 `/api-docs`。

## 启动

在本目录运行（Windows 可将 python 替换为已安装的 Python 完整路径）：

```powershell
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8011
```

打开 http://127.0.0.1:8011/docs，在中文表单中填写资料并评估，或提交示例：

```powershell
$body = Get-Content -Raw -Encoding utf8 data/samples/normal.json
Invoke-RestMethod http://127.0.0.1:8011/api/v1/quantify-risk -Method Post -ContentType 'application/json; charset=utf-8' -Body ([System.Text.Encoding]::UTF8.GetBytes($body))
```

## 接口与资料

`GET /health` 检查状态；`POST /api/v1/quantify-risk` 评估；两个 `/api/v1/config/` 接口分别查看 `disaster-rules` 和 `component-thresholds`。完整字段与返回类型见 `/api-docs`。

位置使用省、市名称精确匹配配置（自动去除首尾空格）。容量单位 kW；承载参数 Pa；冰雹直径 mm；离地高度 m。布尔字段只接受 true/false。遗漏或 null 表示未知，false 表示已知不具备该条件。非正容量、非正承载参数、负高度、未知字段会返回 422。

`project_id` 和 `evidence_references` 用于关联信息提取、照片识别及报告模块，原样返回；首版不自动调用其他模块，也不读取或验证引用材料。

## 评分说明

数值因素评分 = min(实际值 / 演示参考值 × 100, 100)；布尔因素按配置评分。各灾害抗灾能力由配置中的因素权重加权得到。风险 = 地区灾害程度 × (1 - 抗灾能力 / 100)。整体评分使用灾害权重加权，范围均为 0–100。

风险 ≤30 为低、>30 且 ≤60 为中、>60 为高。任何单项为高，整体等级直接标为高，即使整体加权分数较低；`highlighted_risks` 列出这些项目。分类使用未舍入分数，显示分数保留两位小数。

关键因素缺失时，对应灾害的抗灾与风险分数为 null，整体抗灾分数也为 null。地区未知时全部灾害程度与风险为 null，但完整的设备资料仍可计算抗灾分数。任何缺失导致整体风险分数为 null、状态为“资料不足，需复核”。已知高风险仍保留高等级。缺失项去重后列入补充材料清单。

正常示例返回抗灾 100、相对风险 0，这只是演示公式的结果，不代表真实项目无风险。

## 数据与后续接入

两份配置必须使用相同版本。当前宁波、哈尔滨的灾害程度及设备阈值均为人工演示假设，不是气象统计或工程认证要求。结果返回来源及限制，不输出出险概率、赔款或加费比例。

后续在 `config/disaster_rules.json` 的 regions 中接入经核验的地区数据，在 `config/component_thresholds.json` 中维护有依据的阈值，同步更新版本和 source，再通过真实案例校准公式。配置启动时加载，修改后需重启服务。真实事件概率与损失模型需另行验证后接入。

## 测试

```powershell
.venv\Scripts\python.exe -m unittest discover -s tests -v
```

覆盖正常评估、高风险不被平均掩盖、五类灾害、缺失资料、未知地区、输入校验及评分变化方向。
