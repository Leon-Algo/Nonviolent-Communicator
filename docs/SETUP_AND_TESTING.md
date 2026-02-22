# 部署、配置与测试指南

## 1. 目标

用最少步骤完成：

1. 数据库迁移
2. 本地或线上 API 可用性验证
3. 发布前预检
4. 部署迁移实施（方案 A / 方案 B）

当前阶段范围:

1. 仅推进 Web/PWA
2. 微信小程序与原生 App 暂不进入开发与测试范围

当前生产地址（基线）:

1. 前端: `https://nvc-practice-web.vercel.app`
2. 后端: `https://api.leonalgo.site`（备用: `https://nvc-practice-api.vercel.app`）

迁移目标地址（规划）:

1. 方案 A: 前端迁到 Cloudflare Pages，后端继续 Vercel
2. 方案 B: 前端在 Cloudflare Pages，后端迁到 Render

## 2. 环境准备

### 2.1 必需资源

1. Supabase 项目（数据库 + Auth）
2. Vercel 项目（当前后端与现网基线）
3. Cloudflare 账号（前端迁移必需）
4. Render 账号（仅方案 B 需要）
5. 本地 Python 运行环境

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

### 2.3 迁移准备清单（一次性）

1. Cloudflare Pages 已完成 GitHub 授权
2. Cloudflare Pages 已确认可读取仓库 `web/` 目录
3. 后端 CORS 预留 Cloudflare 域名:
   - `https://<project>.pages.dev`
   - `https://<your-custom-domain>`（可选）
4. 如启用方案 B，Render 服务区域固定 `Singapore`
5. `.env` 保持单一事实来源，新增迁移变量需同步 `backend/.env.example`

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
3. 点击安装入口后取消，再次回到页面时确认安装入口仍可点击
4. 在 Edge Android 测试“菜单安装”引导弹层是否可见且步骤可执行
5. 断网后刷新页面，验证应用壳可打开
6. 断网发送 API 请求，验证出现明确错误提示而非白屏
7. 重新联网后验证可继续正常练习
8. 发布新版本后验证出现更新提示并可切换到新版本
9. 如桌面图标未更新，删除旧快捷方式后重新安装验证新图标资源

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
bash scripts/supabase_jwt_api_smoke_test.sh https://api.leonalgo.site
```

### 5.4 一键发布前预检

```bash
bash scripts/release_preflight.sh https://api.leonalgo.site
```

含集成测试时可执行：

```bash
RUN_DB_TESTS=1 bash scripts/release_preflight.sh https://api.leonalgo.site
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
RUN_ONLINE_OFNR_EVAL=1 bash scripts/release_preflight.sh https://api.leonalgo.site
```

### 5.6 Vercel 发布与回滚

推荐统一使用发布脚本：

1. Preview 发布（前后端）:

```bash
bash scripts/vercel_release.sh preview all
```

2. Production 发布（前后端）:

```bash
bash scripts/vercel_release.sh prod all
```

3. Production 回滚（按端执行）:

```bash
bash scripts/vercel_release.sh rollback web <deployment_url_or_id>
bash scripts/vercel_release.sh rollback api <deployment_url_or_id>
```

4. 把指定部署晋升到当前生产（可选）:

```bash
bash scripts/vercel_release.sh promote web <deployment_url_or_id>
bash scripts/vercel_release.sh promote api <deployment_url_or_id>
```

### 5.7 PWA 冒烟检查

```bash
bash scripts/pwa_smoke_check.sh
```

检查项:

1. `manifest.webmanifest` 字段完整性
2. `sw.js` 语法检查
3. 图标资源完整性（192/512）
4. `maskable` 图标资源存在性（192/512）

### 5.8 方案 A 部署步骤（Cloudflare 前端 + Vercel 后端）

1. 在 Cloudflare Pages 新建项目并连接仓库
2. 构建根目录配置到 `web/`（静态站点）
3. 首次先使用 `*.pages.dev` 地址联调，不立即切生产域名
4. 前端默认 API 地址改为 Vercel API 域名（避免同域代理依赖）
5. 后端 `CORS_ORIGINS`、`CORS_ORIGIN_REGEX` 增加 Cloudflare 域名
6. 完成回归测试后，再决定是否将自定义域名切换到 Cloudflare

### 5.9 方案 B 部署步骤（Cloudflare 前端 + Render 后端）

1. Render 新建 Web Service，仓库根目录指向 `backend/`
2. 启动命令:

```bash
uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

3. 设置健康检查路径: `/health`
4. 完整迁移后端环境变量（与 Vercel 保持一致）
5. 前端 API 地址切换到 Render 域名
6. 回归通过后保留 Vercel API 作为回滚目标

### 5.10 Cloudflare Pages 发布脚本（方案 A）

```bash
bash scripts/cloudflare_pages_release.sh deploy <cf_pages_project_name> [branch] [publish_dir]
```

环境变量（必填）:

1. `CLOUDFLARE_API_TOKEN`
2. `CLOUDFLARE_ACCOUNT_ID`

可选:

1. `CF_PAGES_PROJECT_NAME`（不传命令参数时使用）

示例:

```bash
bash scripts/cloudflare_pages_release.sh deploy nvc-practice-web-cf
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

## 7. 迁移验收清单（A/B 通用）

1. 前端域名可稳定打开（手机 4G 与家宽各验证 1 次）
2. 完整主链路通过:
   - 注册/登录
   - 创建场景
   - 发送消息并获得反馈
   - 生成总结与复盘
3. 历史会话列表/筛选/回看正常
4. PWA 安装、取消后重试、更新提示、离线壳均正常
5. `release_preflight` 与 `pwa_smoke_check` 均通过
6. 预案验证: 可在 15 分钟内切回 Vercel 前端或 Vercel API

## 8. 常见问题

1. `over_email_send_rate_limit`
   - Supabase 邮件发送限流导致，开发期可临时关闭 Email Confirm 或改走已注册账户登录。
2. `invalid or expired access token`
   - 通常是 token 过期或 auth mode 与 token 类型不匹配。
3. 远端 API 冒烟超时
   - 优先在可达网络环境或 GitHub Actions 中复测。
4. 手机端“取消安装后找不到入口”
   - 当前策略为安装入口在未安装状态下持续可见；若未显示，优先清理该站点缓存后重试。
5. 手机桌面图标仍为旧样式
   - 删除旧快捷方式并重新安装；旧图标通常不会自动刷新。
6. Cloudflare 页面能打开但 API 全部失败
   - 通常是 `apiBaseUrl` 仍指向同域或后端 CORS 未加入 `*.pages.dev` 域名。
7. Render API 首次请求明显变慢
   - 免费实例空闲后会休眠，首个请求存在冷启动延迟；需要稳定体验时建议升级付费实例。
