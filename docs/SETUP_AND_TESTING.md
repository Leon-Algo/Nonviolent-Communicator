# 部署、配置与测试指南

## 1. 目标

用最少步骤完成：

1. 数据库迁移
2. 本地或线上 API 可用性验证
3. 发布前预检

当前阶段范围:

1. 仅推进 Web/PWA
2. 微信小程序与原生 App 暂不进入开发与测试范围

当前生产地址:

- 前端: `https://nvc-practice-web.vercel.app`
- 后端: `https://nvc-practice-api.vercel.app`

## 2. 环境准备

### 2.1 必需资源

1. Supabase 项目（数据库 + Auth）
2. Vercel 项目（前端/后端）
3. 本地 Python 运行环境

### 2.2 环境变量

建议统一放在仓库根目录 `.env`（后端已支持读取根目录和 `backend/.env`）。

关键变量:

- `APP_ENV`
- `DATABASE_URL`
- `AUTH_MODE`
- `MOCK_AUTH_ENABLED`
- `SUPABASE_URL`
- `SUPABASE_ANON_KEY`
- `LLM_API_KEY`
- `LLM_MODEL`
- `OPENAI_BASE_URL`

## 3. 数据库迁移（最简方式）

在 Supabase SQL Editor 按顺序执行：

1. `db/migrations/0001_init_nvc_practice.sql`
2. `db/migrations/0002_add_idempotency_keys.sql`
3. `db/migrations/0003_sync_auth_users_to_public_users.sql`
4. `db/migrations/0004_enable_rls_core_tables.sql`
5. `db/migrations/0005_fix_request_user_id_claim_resolution.sql`

## 4. 本地运行

### 4.1 后端

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -e "[dev]"
uvicorn app.main:app --reload --port 8000
```

### 4.2 后端测试

```bash
cd backend
pytest tests -q
```

### 4.3 前端体验（M3）

1. 打开前端页面（本地或 Vercel 域名）
2. 按 3 步流程测试:
   - Step 1: 登录并获取 token
   - Step 2: 创建场景并发送首轮消息
   - Step 3: 生成行动卡并提交复盘
3. 点击“刷新历史”，确认能看到跨会话历史列表并可回看
4. 在历史区测试筛选（状态/关键词/日期范围）并验证结果变化
5. 加载历史会话后测试“跳到轮次”和“继续当前会话”交互
6. 生成行动卡后测试导出能力:
   - 复制行动卡
   - 导出 Markdown
   - 导出 PDF（打印窗口）
   - 导出图片（PNG）
   - 分享模板（复制/导出）
7. 访问 `GET /ops/metrics`，确认可看到 `slow_request_count` 与 `server_error_count`
8. 修改历史筛选条件并刷新页面，确认筛选条件会保留
9. 历史列表测试上一页/下一页，确认分页生效

### 4.4 PWA 验收（当前阶段重点）

1. 打开 `Application` 面板确认 Manifest 生效（名称、图标、display）
2. 触发安装入口，验证可成功安装到桌面（或应用列表）
3. 断网后刷新页面，验证应用壳可打开
4. 断网发送 API 请求，验证出现明确错误提示而非白屏
5. 重新联网后验证可继续正常练习
6. 发布新版本后验证出现更新提示并可切换到新版本

## 5. 冒烟与预检（仓库根目录）

### 5.1 本地 mock 冒烟

```bash
bash scripts/api_smoke_test.sh http://127.0.0.1:8000
```

### 5.2 RLS 隔离校验（直连 Supabase）

```bash
bash scripts/rls_isolation_check.sh
```

### 5.3 Supabase JWT API 冒烟

```bash
bash scripts/supabase_jwt_api_smoke_test.sh https://nvc-practice-api.vercel.app
```

### 5.4 一键发布前预检

```bash
bash scripts/release_preflight.sh https://nvc-practice-api.vercel.app
```

含集成测试时可执行：

```bash
RUN_DB_TESTS=1 bash scripts/release_preflight.sh https://nvc-practice-api.vercel.app
```

### 5.5 OFNR 回归评测

```bash
python scripts/run_ofnr_eval.py
```

可选门禁参数:

- `OFNR_EVAL_MIN_OVERALL`（默认 `0.72`）
- `OFNR_EVAL_MIN_RISK_ACCURACY`（默认 `0.75`）

在线模型回归（可选）:

```bash
python scripts/run_ofnr_eval.py --mode online
```

在线回归门禁参数:

- `OFNR_ONLINE_EVAL_MIN_OVERALL`（默认 `0.45`）
- `OFNR_ONLINE_EVAL_MIN_SUCCESS`（默认 `0.6`）
- `OFNR_ONLINE_EVAL_CONCURRENCY`（默认 `1`）
- `OFNR_ONLINE_EVAL_MAX_CASES`（默认 `8`，`0` 表示全量）

注意:

- 在线回归依赖模型供应商可用额度；当日配额耗尽会触发 429，导致在线回归失败。

发布前预检启用在线回归:

```bash
RUN_ONLINE_OFNR_EVAL=1 bash scripts/release_preflight.sh https://nvc-practice-api.vercel.app
```

## 6. GitHub Actions 手动预检

工作流: `.github/workflows/release-preflight.yml`

作用:

1. 在 GitHub 云端执行预检（避免本地网络/环境差异）
2. 可选执行 RLS 校验与远端 API 冒烟

可选 Secrets:

- `SUPABASE_URL`
- `SUPABASE_ANON_KEY`
- `LLM_API_KEY`（仅在启用在线 OFNR 回归时需要）

关键输入参数（`workflow_dispatch`）:

1. `api_base_url`
2. `run_rls_isolation`
3. `run_remote_api_smoke`
4. `run_online_ofnr_eval`（默认 `false`，灰度启用）

当前仓库状态:

- 已配置上述两个 Secrets，可直接运行完整线上预检。
- 最近一次通过的完整预检（含 RLS + JWT API smoke）:
  - `https://github.com/Leon-Algo/Nonviolent-Communicator/actions/runs/21979380349`
- 在线 OFNR 回归默认不在每次预检中强制执行，建议在发布前/每日固定时段手动开启。

## 7. 常见问题

1. `over_email_send_rate_limit`
   - Supabase 邮件发送限流导致，开发期可临时关闭 Email Confirm 或改走已注册账户登录。
2. `invalid or expired access token`
   - 通常是 token 过期或 auth mode 与 token 类型不匹配。
3. 远端 API 冒烟超时
   - 优先在可达网络环境或 GitHub Actions 中复测。
