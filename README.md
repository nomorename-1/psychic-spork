# 分布式光伏智能核保：高风险场景识别 Demo

本阶段只实现两个功能：

1. 接收图片、PDF、DOCX、TXT、JSON 等多模态材料；
2. 识别农田、森林、林地、渔光互补、涉水、滩涂、集中式等场景，并按规则输出拒保或人工复核。

当前为 Demo：AI 适配器默认使用明确标记的模拟识别，图片场景演示主要依据文件名；接入真实视觉模型后，可替换 `app/services/ai_adapter.py`。

## 本地运行

```powershell
.\\.venv\\Scripts\\python.exe -m pip install -r requirements.txt
.\\.venv\\Scripts\\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

打开 `http://127.0.0.1:8000`。

## 接口

- `POST /api/v1/analyze`：上传单个材料
- `POST /api/v1/analyze-package`：上传多个材料，任一材料命中明确拒保规则则材料包拒保
- `GET /api/v1/rules`：查看当前拒保规则
- `GET /health`：健康检查

支持：JPG、JPEG、PNG、WEBP、PDF、DOCX、TXT、JSON，单文件最大 20 MB。

## 当前结论范围

- `拒保`：高置信度命中高风险场景
- `建议人工复核`：疑似命中但置信度不足
- `未发现本阶段高风险拒保场景`：未命中本阶段规则，不代表最终承保

本阶段明确不实现加减费、组件抗灾量化、气象数据、完整 OCR 交叉验证、保费计算和完整核保报告。

## 测试

```powershell
.\\.venv\\Scripts\\python.exe -m unittest discover -s tests -v
```

## Docker

当前项目需要 Docker Desktop 能访问 Docker Hub，因为基础镜像来自 `python:3.12-slim`。

```powershell
docker login
docker pull python:3.12-slim
docker compose -p pv-risk-engine up --build -d
```

如果国内网络访问 Docker Hub 不稳定，可在 Docker Desktop 中配置镜像加速：

1. 打开 Docker Desktop。
2. 进入 `Settings` -> `Docker Engine`。
3. 在 JSON 中加入或合并 `registry-mirrors`，例如：

```json
{
  "registry-mirrors": [
    "https://docker.m.daocloud.io"
  ]
}
```

4. 点击 `Apply & Restart`，然后重新执行：

```powershell
docker pull python:3.12-slim
docker compose -p pv-risk-engine up --build -d
```

如果构建时卡在 Python 依赖下载，可临时使用国内 PyPI 源：

```powershell
docker compose -p pv-risk-engine build --build-arg PIP_INDEX_URL=https://pypi.tuna.tsinghua.edu.cn/simple
docker compose -p pv-risk-engine up -d
```

如果 Docker 命令未加入 PATH，可尝试完整路径：

```powershell
& "C:\Program Files\Docker\Docker\resources\bin\docker.exe" version
```
