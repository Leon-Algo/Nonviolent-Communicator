# Nonviolent-Communicator

NVC (Nonviolent Communication) 练习产品的 MVP 项目仓库。
当前目标是让用户通过“登录 -> 对练 -> 复盘”的 3 步流程，形成可迁移到真实对话的沟通能力。

## 当前能力

- 后端: FastAPI + PostgreSQL（Supabase）
- 前端: 引导式 3 步练习页（当前 Vercel，迁移目标 Cloudflare Pages）
- 鉴权: Supabase JWT（线上）+ Mock（本地开发）
- AI: ModelScope OpenAI-compatible 接口
- 核心链路: 场景 -> 会话 -> 消息反馈 -> 改写/总结 -> 复盘 -> 周进度
- 历史回看: 跨会话历史列表 + 单会话完整回看 + 分页/风险分组
- 可观测性: 结构化请求日志 + `/ops/metrics` 慢请求/5xx 聚合
- AI 回归: `spec/evals/ofnr_evalset_v0.2.jsonl` 离线回归（预检内置）+ 在线模型回归模式
- 行动卡导出: 复制、Markdown、PDF（打印导出）、PNG 图片、分享模板（复制/导出）
- PWA: 安装入口（取消后可再次点击）、安装引导弹层、更新提示、离线状态提示、历史会话离线快照

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
bash scripts/release_preflight.sh https://api.leonalgo.site
```

可选: 执行在线模型回归（默认关闭）:

```bash
RUN_ONLINE_OFNR_EVAL=1 bash scripts/release_preflight.sh https://api.leonalgo.site
```

说明: 在线回归依赖模型配额，若供应商返回 429（配额耗尽）会导致该步骤失败。

5. 发布与回滚（仓库根目录）

```bash
bash scripts/vercel_release.sh preview all
bash scripts/vercel_release.sh prod all
# 回滚示例:
bash scripts/vercel_release.sh rollback web <deployment_url_or_id>
```

Cloudflare Pages（方案 A）发布:

```bash
bash scripts/cloudflare_pages_release.sh deploy <cf_pages_project_name>
```

## 文档入口

- 文档总览: `docs/README.md`
- 产品 PRD: `docs/PRD.md`
- 技术方案: `docs/TECHNICAL_SOLUTION.md`
- 开发计划: `docs/DEVELOPMENT_PLAN.md`
- 部署与测试: `docs/SETUP_AND_TESTING.md`
- 阶段复盘: `docs/STAGE_REVIEW.md`

## 部署说明

当前生产基线:

1. 前后端均在 Vercel
2. GitHub Actions 用于自动化测试/预检，不替代托管平台

迁移计划（M4）:

1. 方案 A（优先）: Cloudflare Pages 前端 + Vercel 后端
2. 方案 B（条件触发）: Cloudflare Pages 前端 + Render 后端

迁移实施细节见: `docs/TECHNICAL_SOLUTION.md`、`docs/DEVELOPMENT_PLAN.md`、`docs/SETUP_AND_TESTING.md`

生产地址:

- 前端: `https://nvc-practice-web.vercel.app`
- 后端: `https://api.leonalgo.site`（备用: `https://nvc-practice-api.vercel.app`）
