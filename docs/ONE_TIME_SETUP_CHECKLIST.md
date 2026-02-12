# One-Time Setup Checklist (Local + Vercel + Supabase)

## 1. 当前已完成

1. 后端项目已部署到 Vercel  
   - `https://nvc-practice-api.vercel.app`
2. Vercel 项目已配置核心生产环境变量
   - 鉴权模式建议:
     - `AUTH_MODE=supabase`
     - `MOCK_AUTH_ENABLED=false`（线上仅 Supabase）
     - `ALLOW_MOCK_AUTH_IN_PRODUCTION=false`
     - `SUPABASE_ANON_KEY=<anon key>`
3. 统一本地配置文件已创建  
   - `/Users/leon/Documents/CodeProject/Nonviolent-Communicator/.env`
4. 后端支持 Mock Token 鉴权与核心 API

## 2. 你还需要一次性准备的内容

1. 域名解析权限（DNS 控制台账号）
   - 目标是后续绑定:
     - 前端: `leonalgo.site`
     - 后端: `api.leonalgo.site`（推荐）
2. Supabase SQL Editor 可访问权限
   - 用于执行首个迁移脚本
3. 前端代码仓（或目录）准备好后告诉我
   - 我会按同样方式部署 `web` 项目并配置 CORS
4. （可选）若要启用 GitHub 手动预检流水线
   - 在 GitHub 仓库 Secrets 配置:
     - `SUPABASE_URL`
     - `SUPABASE_ANON_KEY`

## 3. 最简单迁移方式（推荐）

1. 打开 Supabase Dashboard -> SQL Editor
2. 新建 Query
3. 粘贴文件内容:
   - `/Users/leon/Documents/CodeProject/Nonviolent-Communicator/db/migrations/0001_init_nvc_practice.sql`
   - `/Users/leon/Documents/CodeProject/Nonviolent-Communicator/db/migrations/0002_add_idempotency_keys.sql`
   - `/Users/leon/Documents/CodeProject/Nonviolent-Communicator/db/migrations/0003_sync_auth_users_to_public_users.sql`
   - `/Users/leon/Documents/CodeProject/Nonviolent-Communicator/db/migrations/0004_enable_rls_core_tables.sql`
   - `/Users/leon/Documents/CodeProject/Nonviolent-Communicator/db/migrations/0005_fix_request_user_id_claim_resolution.sql`
4. 点击 Run
5. 运行后执行校验 SQL:

```sql
SELECT table_name
FROM information_schema.tables
WHERE table_schema = 'public'
  AND table_name IN (
    'users','scenes','sessions','messages','feedback_items',
    'rewrites','summaries','reflections','event_logs'
  )
ORDER BY table_name;
```

## 4. 冒烟测试（你本机可直接跑）

脚本路径:

- `/Users/leon/Documents/CodeProject/Nonviolent-Communicator/scripts/api_smoke_test.sh`

运行示例:

```bash
bash scripts/api_smoke_test.sh https://nvc-practice-api.vercel.app
```

RLS 隔离验收（Supabase 直连）:

```bash
bash scripts/rls_isolation_check.sh
```

Supabase JWT 端到端冒烟（后端 API）:

```bash
bash scripts/supabase_jwt_api_smoke_test.sh https://nvc-practice-api.vercel.app
```

发布前一键预检:

```bash
bash scripts/release_preflight.sh https://nvc-practice-api.vercel.app
```

GitHub 手动预检:

- Workflow: `.github/workflows/release-preflight.yml`
- 触发方式: Actions -> `release-preflight` -> Run workflow
- 默认包含 Postgres 集成测试（`RUN_DB_TESTS=1`）

前端 Supabase 鉴权联调:

1. 打开 `https://nvc-practice-web.vercel.app`
2. 填写 Supabase 邮箱和密码，点击 `登录并获取 Token`
3. 按顺序点击创建场景、创建会话、发送消息
4. 线上默认仅开放 Supabase 模式，Mock 入口已隐藏
5. 若本地开发需要 Mock 联调，可在 URL 加 `?dev=1` 或使用 localhost
6. 若你要持续做“真实邮箱注册”联调，建议在 Supabase 控制台临时关闭 Email Confirm（开发期），避免邮件发送限流

## 5. 后续最佳实践建议（等你确认后我再执行）

1. 绑定自有域名
   - `leonalgo.site` -> 前端
   - `api.leonalgo.site` -> 后端
2. 上线前再做密钥轮换与脱敏
3. 开启 Supabase RLS（公开测试前必须做）
4. RLS 上线后，建议后端请求启用 `SET LOCAL ROLE authenticated + request.jwt.claim.sub`（代码已实现）
