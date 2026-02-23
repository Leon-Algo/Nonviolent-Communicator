# Nonviolent-Communicator

NVC（Nonviolent Communication）练习产品的 MVP 仓库。
当前目标是让用户通过“登录 -> 对练 -> 复盘”的 3 步流程，形成可迁移到真实对话的沟通能力。

## 当前能力

- 后端: FastAPI + PostgreSQL（Supabase）
- 前端: 引导式 3 步练习页（Cloudflare Pages）
- 鉴权: Supabase JWT（线上）+ Mock（本地开发）
- AI: ModelScope OpenAI-compatible 接口
- 核心链路: 场景 -> 会话 -> 消息反馈 -> 总结 -> 复盘 -> 周进度
- 历史回看: 跨会话历史列表 + 单会话完整回看 + 分页/筛选
- 行动卡导出: 复制、Markdown、PDF、PNG、分享模板
- PWA: 安装入口、更新提示、离线提示、历史会话离线快照
- 前后端联通: Cloudflare Pages Functions 同域代理 `/api/*`

## 仓库结构

- `backend/`: API 服务、业务逻辑与测试
- `web/`: 前端页面
- `functions/`: Cloudflare Pages Functions（API 代理与健康检查）
- `db/migrations/`: SQL 迁移脚本
- `scripts/`: 冒烟与预检脚本
- `spec/`: OpenAPI 与评测集
- `docs/`: 产品、技术、计划与运行文档

## 本地快速开始

1. 准备环境变量

```bash
cp backend/.env.example backend/.env
# 或使用仓库根目录 .env（当前已支持）
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
cd backend
pytest tests -q
```

4. 运行项目级预检（仓库根目录）

```bash
bash scripts/release_preflight.sh https://nonviolent-communicator-stable.pages.dev
```

可选: 执行在线模型回归（默认关闭）

```bash
RUN_ONLINE_OFNR_EVAL=1 bash scripts/release_preflight.sh https://nonviolent-communicator-stable.pages.dev
```

5. 发布

Cloudflare 前端发布:

```bash
bash scripts/cloudflare_pages_release.sh deploy nonviolent-communicator-stable main web functions
bash scripts/cloudflare_pages_release.sh deploy nonviolent-communicator main web functions
```

Vercel 后端发布:

```bash
bash scripts/vercel_release.sh preview api
bash scripts/vercel_release.sh prod api
```

## 文档入口

- 文档总览: `docs/README.md`
- 产品 PRD: `docs/PRD.md`
- 技术方案: `docs/TECHNICAL_SOLUTION.md`
- 开发计划: `docs/DEVELOPMENT_PLAN.md`
- 部署与测试: `docs/SETUP_AND_TESTING.md`
- 阶段复盘: `docs/STAGE_REVIEW.md`

## 当前部署基线

- 前端稳定域名: `https://nonviolent-communicator-stable.pages.dev`
- 前端主域名: `https://nonviolent-communicator.pages.dev`
- 后端服务域名: `https://nvc-practice-api.vercel.app`
- 前端健康检查: `<front-domain>/health-backend`

## 迁移复盘入口

本次 Cloudflare 迁移故障的完整前因后果、修复路径和防复发规则见:

1. `docs/STAGE_REVIEW.md`
2. `docs/TECHNICAL_SOLUTION.md`
3. `docs/SETUP_AND_TESTING.md`
