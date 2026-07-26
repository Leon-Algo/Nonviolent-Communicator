# 部署、配置与测试指南（Cloudflare 迁移稳定版）

## 1. 目标

用最少步骤完成:

1. 数据库迁移
2. 前后端联通验证
3. 发布前预检
4. Cloudflare 前端发布与回滚

当前阶段范围:

1. 仅推进 Web/PWA
2. 微信小程序与原生 App 暂不进入开发与测试范围

当前生产基线:

1. 前端（稳定）: `https://nonviolent-communicator-stable.pages.dev`
2. 前端（主）: `https://nonviolent-communicator.pages.dev`
3. 后端（实际服务）: `https://nvc-practice-api.vercel.app`
4. 后端（前端访问方式）: 同域 `/api/*`（Cloudflare Functions 代理）

## 2. 环境准备

### 2.1 必需资源

1. Supabase 项目（数据库 + Auth）
2. Vercel 项目（后端）
3. Cloudflare 账号（Pages）
4. 本地 Python 运行环境

### 2.2 环境变量

建议统一放在仓库根目录 `.env`。

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
- `CLOUDFLARE_ACCOUNT_ID`
- `CLOUDFLARE_API_TOKEN`
- `CF_PAGES_PROJECT_NAME`
- `AGORA_APP_ID`（启用语音对练时必需）
- `AGORA_APP_CERTIFICATE`（启用语音对练时必需）
- `AGORA_AREA`（可选，`US`/`EU`/`AP`/`CN`，默认 `US`）
- `AGENT_GREETING`（可选，语音 Agent 开场白）

可选（Pages Functions 代理目标）:

- `API_PROXY_ORIGIN`（默认 `https://nvc-practice-api.vercel.app`）

语音联调环境诊断:

```bash
python scripts/check_voice_integration_env.py
```

该脚本只输出变量是否存在、目标 host 和 DNS 解析结果，不打印密钥。若在独立 worktree 中运行，需要先加载主项目 `.env` 和 quickstart 的 `server/.env.local`。

### 2.3 Cloudflare 一次性准备清单

1. Pages 项目绑定 GitHub 仓库
2. 发布目录指向 `web/`
3. 仓库根目录存在 `functions/`（Pages Functions）
4. 确认域名能访问:
   - `/`
   - `/diag`
   - `/ping.txt`
   - `/health-backend`

## 3. 数据库迁移（最简方式）

在 Supabase SQL Editor 按顺序执行:

1. `db/migrations/0001_init_nvc_practice.sql`
2. `db/migrations/0002_add_idempotency_keys.sql`
3. `db/migrations/0003_sync_auth_users_to_public_users.sql`
4. `db/migrations/0004_enable_rls_core_tables.sql`
5. `db/migrations/0005_fix_request_user_id_claim_resolution.sql`
6. `db/migrations/0006_add_voice_session_support.sql`

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

### 4.2.1 前端本地联调（静态 + /api 代理）

本地直接用 `python3 -m http.server` 打开 web/ 时，所有 API 都会失败：
生产依赖 Cloudflare Pages Function 的同源 `/api` 代理，且后端 CORS 不放行
localhost 跨域直连。请改用仓库自带的 dev server，它会补齐这一层代理：

```bash
# 终端 1：本地后端（mock 鉴权默认开启，可用 Mock 用户联调）
cd backend && ../.venv/bin/uvicorn app.main:app --port 8000

# 终端 2：静态 + 代理（默认代理到 http://localhost:8000）
python3 scripts/dev_server.py          # 打开 http://localhost:8787

# 想直连生产后端（需真实 Supabase 账号，Mock 会被生产拒绝）：
BACKEND_URL=https://api.leoalgo.site python3 scripts/dev_server.py
```

开发者面板（API 地址 / Mock 切换 / 调试输出）默认隐藏，用
`http://localhost:8787/index.html?dev=1` 打开即可显示。

#### macOS 系统代理坑（语音/LLM 偶发失效）

httpx 默认 `trust_env=True`，在 macOS 上会经 `urllib.getproxies()`
**回退读取系统代理设置**（即使进程没有任何 `*_PROXY` 环境变量）。
本机代理（Clash 等）节点不可用时，后端到 Agora REST / ModelScope /
Supabase 的请求会 ConnectError 或挂起数分钟，表现为「语音对练一直
加载、最终 500」。后端所有 httpx 客户端已显式 `trust_env=False`
（`voice_agent.py` / `nvc_service.py` / `supabase_auth.py`），
直连这三个服务即可；Agora agent 启动失败会被映射为
`502 voice agent service unavailable`，前端柔性提示而不是卡死。
如确需走代理，请在代码里显式配置，不要依赖系统代理。

### 4.3 前端体验（M3）

1. 打开前端页面（Cloudflare 域名）
2. 按 3 步流程测试:
   - Step 1: 登录并获取 token
   - Step 2: 创建场景并发送首轮消息
   - Step 3: 生成行动卡并提交复盘
3. 点击“刷新历史”，确认历史列表可见
4. 测试历史筛选（状态/关键词/日期范围）
5. 测试“跳到轮次”和“继续当前会话”
6. 测试行动卡导出:
   - 复制
   - Markdown
   - PDF
   - PNG
   - 分享模板

### 4.4 PWA 验收

1. Manifest 生效（名称、图标、display）
2. 可安装到桌面
3. 取消安装后入口仍可再次点击
4. 刷新后页面仍可正常打开
5. 发布新版本后可更新

## 5. 冒烟与预检（仓库根目录）

### 5.1 本地 mock 冒烟

```bash
bash scripts/api_smoke_test.sh http://127.0.0.1:8000
```

### 5.2 RLS 隔离校验（直连 Supabase）

```bash
bash scripts/rls_isolation_check.sh
```

### 5.3 Supabase JWT API 冒烟（推荐走前端域名）

```bash
bash scripts/supabase_jwt_api_smoke_test.sh https://nonviolent-communicator-stable.pages.dev
```

备用（直接打后端）:

```bash
bash scripts/supabase_jwt_api_smoke_test.sh https://nvc-practice-api.vercel.app
```

### 5.4 一键发布前预检

```bash
bash scripts/release_preflight.sh https://nonviolent-communicator-stable.pages.dev
```

含集成测试:

```bash
RUN_DB_TESTS=1 bash scripts/release_preflight.sh https://nonviolent-communicator-stable.pages.dev
```

### 5.5 OFNR 回归评测

```bash
python scripts/run_ofnr_eval.py --mode offline
```

可选在线回归:

```bash
python scripts/run_ofnr_eval.py --mode online
```

### 5.6 Vercel 发布与回滚（后端）

```bash
bash scripts/vercel_release.sh preview api
bash scripts/vercel_release.sh prod api
bash scripts/vercel_release.sh rollback api <deployment_url_or_id>
```

### 5.7 Cloudflare 前端发布

```bash
bash scripts/cloudflare_pages_release.sh deploy <cf_pages_project_name> [branch] [publish_dir] [functions_dir]
```

示例:

```bash
bash scripts/cloudflare_pages_release.sh deploy nonviolent-communicator-stable main web functions
bash scripts/cloudflare_pages_release.sh deploy nonviolent-communicator main web functions
```

### 5.8 PWA 冒烟检查

```bash
bash scripts/pwa_smoke_check.sh
```

该检查会同时执行 `node scripts/check_voice_pwa_contract.js`，确认语音模式 DOM、前端 API 路径和 JS 入口没有被误删。

## 6. 迁移排障标准流程（必须按顺序）

### 6.1 第一步: 静态站点是否可达

检查:

1. `/`
2. `/diag`
3. `/ping.txt`

若失败:

1. 先排查域名/DNS/网络
2. 不要先改业务代码

### 6.2 第二步: 后端代理是否可达

检查:

1. `/health-backend` 必须返回 JSON（示例: `{"status":"ok","app_env":"production"}`）

若返回 HTML:

1. 说明 Functions 未生效或路由未命中

### 6.3 第三步: API 路径是否穿透

检查:

1. `OPTIONS /api/v1/scenes`（预检）
2. `POST /api/v1/scenes`（无鉴权应返回 `401 missing Authorization`，不是 `404/405`）

### 6.4 第四步: 业务全链路

执行:

1. `scripts/supabase_jwt_api_smoke_test.sh <front_domain>`

期望:

1. 7 步全部通过

### 6.5 第五步: 客户端缓存排查

若“页面能开但功能异常”:

1. 打开 `?pwa=0` 一次，触发清理旧 SW
2. 关闭所有标签页后重开页面
3. 再做登录与主链路测试

## 7. 常见问题（含本次迁移经验）

1. `over_email_send_rate_limit`
   - 原因: Supabase 邮件发送频控
   - 处理: 开发期可临时关闭 Email Confirm，或用已注册账号登录

2. 登录后 1 秒提示“当前离线或网络不可用”
   - 原因: 登录后立即请求历史接口失败（旧 API 基址或旧 SW 缓存）
   - 处理: 生产强制同域 API + SW 版本升级 + 清理旧 SW

3. 页面可打开但 API 全失败
   - 原因: Cloudflare 仅发布静态资源，未启用 `/api/*` Functions 代理
   - 处理: 检查 `functions/api/[[path]].js`、`/health-backend`、重新部署

4. `/health-backend` 返回 HTML
   - 原因: 路由落到静态站点，Functions 未生效
   - 处理: 用 `wrangler --cwd <repo_root> pages deploy` 重新发布

5. 发布后用户端“像没更新”
   - 原因: SW 缓存旧脚本
   - 处理: 提升 `SW_VERSION`，并避免缓存 `app.js`

6. Cloudflare 发布报错 `Unknown internal error occurred`
   - 原因: Cloudflare 平台侧偶发错误
   - 处理: 不改代码先重试发布，成功后再继续验收

## 8. 迁移验收清单（A 方案当前标准）

1. 前端域名可稳定打开（手机网络验证）
2. `/health-backend` 返回后端 JSON
3. `/api/*` 预检与业务请求可达
4. 主链路通过:
   - 注册/登录
   - 创建场景
   - 发送消息并获得反馈
   - 生成总结与复盘
5. 历史会话列表/筛选/回看正常
6. PWA 安装、刷新、更新能力正常
7. 预检通过:
   - `release_preflight`
   - `pwa_smoke_check`
8. 回滚预案可执行（15 分钟内切回上个稳定版本）
