# One-Time Setup Checklist (Local + Vercel + Supabase)

## 1. 当前已完成

1. 后端项目已部署到 Vercel  
   - `https://nvc-practice-api.vercel.app`
2. Vercel 项目已配置核心生产环境变量
   - 鉴权模式建议:
     - `AUTH_MODE=supabase`
     - `MOCK_AUTH_ENABLED=false`
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

## 3. 最简单迁移方式（推荐）

1. 打开 Supabase Dashboard -> SQL Editor
2. 新建 Query
3. 粘贴文件内容:
   - `/Users/leon/Documents/CodeProject/Nonviolent-Communicator/db/migrations/0001_init_nvc_practice.sql`
   - `/Users/leon/Documents/CodeProject/Nonviolent-Communicator/db/migrations/0002_add_idempotency_keys.sql`
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

## 5. 后续最佳实践建议（等你确认后我再执行）

1. 绑定自有域名
   - `leonalgo.site` -> 前端
   - `api.leonalgo.site` -> 后端
2. 上线前再做密钥轮换与脱敏
3. 开启 Supabase RLS（公开测试前必须做）
