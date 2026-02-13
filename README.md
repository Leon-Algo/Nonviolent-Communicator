# Nonviolent-Communicator

NVC (Nonviolent Communication) 练习产品的 MVP 项目仓库。
当前目标是让用户通过“登录 -> 对练 -> 复盘”的 3 步流程，形成可迁移到真实对话的沟通能力。

## 当前能力

- 后端: FastAPI + PostgreSQL（Supabase）
- 前端: 引导式 3 步练习页（Vercel）
- 鉴权: Supabase JWT（线上）+ Mock（本地开发）
- AI: ModelScope OpenAI-compatible 接口
- 核心链路: 场景 -> 会话 -> 消息反馈 -> 改写/总结 -> 复盘 -> 周进度
- 历史回看: 跨会话历史列表 + 单会话完整回看
- 可观测性: 结构化请求日志 + `/ops/metrics` 慢请求/5xx 聚合
- AI 回归: `spec/evals/ofnr_evalset_v0.1.jsonl` 自动回归（预检内置）

## 仓库结构

- `backend/`: API 服务、业务逻辑与测试
- `web/`: 前端页面
- `db/migrations/`: SQL 迁移脚本
- `scripts/`: 冒烟与预检脚本
- `spec/`: OpenAPI 与评测集
- `docs/`: 产品、技术、计划与运行文档

## 本地快速开始

1. 准备环境变量

```bash
cp backend/.env.example backend/.env
# 或使用项目根目录 .env（当前仓库已支持）
```

2. 启动后端

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -e "[dev]"
uvicorn app.main:app --reload --port 8000
```

3. 运行后端测试

```bash
pytest tests -q
```

4. 运行项目级预检（仓库根目录）

```bash
bash scripts/release_preflight.sh https://nvc-practice-api.vercel.app
```

## 文档入口

- 文档总览: `docs/README.md`
- 产品 PRD: `docs/PRD.md`
- 技术方案: `docs/TECHNICAL_SOLUTION.md`
- 开发计划: `docs/DEVELOPMENT_PLAN.md`
- 部署与测试: `docs/SETUP_AND_TESTING.md`
- 阶段复盘: `docs/STAGE_REVIEW.md`

## 部署说明

前后端均可部署在 Vercel；GitHub Actions 用于自动化测试/预检，不替代 Vercel 的托管能力。

生产地址:

- 前端: `https://nvc-practice-web.vercel.app`
- 后端: `https://nvc-practice-api.vercel.app`
