# 阶段复盘（2026-02-12）

## 1. 复盘范围

- 复盘日期: 2026-02-12
- 覆盖阶段: 鉴权链路稳定化 + Supabase 注册链路修复 + 联调体验收敛
- 目标: 从“多模式临时联调”收敛到“线上仅 Supabase 的可测试路径”

## 2. 本阶段关键结论

1. 线上测试主链路确定为 `Supabase 注册/登录 -> JWT 调业务接口`。
2. Mock 模式保留给本地开发，不再作为线上测试入口。
3. Supabase 注册后用户数据已可自动同步到业务表 `public.users`。

## 3. 关键问题与根因

1. 注册报错 `429 over_email_send_rate_limit`
   - 根因: Supabase Auth 邮件发送频控触发，导致注册流程中断。
2. Mock 模式报错 `401 invalid or expired access token`
   - 根因: 在线上 `AUTH_MODE=supabase` 路径下，mock token 回退策略与环境开关不一致，导致请求进入 Supabase JWT 校验。
3. 前端测试入口复杂
   - 根因: 联调期保留了过多 mock/supabase 双模式控件，普通测试用户容易误操作。

## 4. 已实施修复

1. 后端鉴权回退能力与边界测试
   - `backend/app/api/deps.py`
   - `backend/tests/test_auth_deps.py`
2. 前端注册/登录容错增强
   - 注册遇到 429 时优先尝试同邮箱直接登录
   - token 失效错误提示更明确
   - 文件: `web/app.js`
3. 用户同步机制上线
   - 新增迁移: `db/migrations/0003_sync_auth_users_to_public_users.sql`
   - 作用: `auth.users` 新增或更新后自动 upsert 到 `public.users`，并回填历史用户
4. 线上入口收敛
   - 线上隐藏 Mock 相关 UI，仅展示 Supabase 流程
   - 本地可通过 `localhost/127.0.0.1` 或 `?dev=1` 显示开发入口
   - 文件: `web/index.html`, `web/app.js`, `web/styles.css`
5. 冒烟脚本可靠性加强
   - `scripts/api_smoke_test.sh` 由“弱校验”改为“非 2xx 立即失败”
6. M1 安全基线首版落地
   - 新增迁移: `db/migrations/0004_enable_rls_core_tables.sql`
   - 覆盖核心表 RLS policy（users/scenes/sessions/messages/feedback/rewrites/summaries/reflections/event_logs/idempotency_keys）
   - 应用侧新增每请求 DB 上下文注入：`SET LOCAL ROLE authenticated` + `request.jwt.claim.sub`
   - 文件: `backend/app/db/security.py` + 相关 router
7. 生产环境 Mock 安全阈值
   - 新增配置约束：生产环境默认禁止 `MOCK_AUTH_ENABLED=true`
   - 紧急回滚可通过 `ALLOW_MOCK_AUTH_IN_PRODUCTION=true` 显式开启
   - 文件: `backend/app/core/config.py`
8. M2 回归基础能力增强
   - 新增 DB 集成测试: `backend/tests/test_api_flow_integration.py`
   - 新增 Postgres service CI 流水线配置: `.github/workflows/backend-tests.yml`
9. 新增可执行验收脚本
   - RLS 隔离校验: `scripts/rls_isolation_check.sh`
   - Supabase JWT API 冒烟: `scripts/supabase_jwt_api_smoke_test.sh`
10. RLS claim 兼容修复迁移
   - 新增 `db/migrations/0005_fix_request_user_id_claim_resolution.sql`
   - 兼容 `auth.uid()` 与 `request.jwt.claims` / `request.jwt.claim.sub` 解析路径
11. 发布前预检自动化
   - 新增 `scripts/release_preflight.sh`
   - 串联单测/集成测试（`RUN_DB_TESTS=1`）、脚本语法检查、RLS 隔离校验与 JWT API 冒烟
12. CI 手动预检入口
   - 新增 `.github/workflows/release-preflight.yml`
   - 支持手动选择是否执行 RLS 隔离和远端 API 冒烟

## 5. 验证结果

1. 后端自动化测试通过: `pytest backend/tests -q` -> `17 passed, 2 skipped`
2. 一键预检通过（本地）: `SKIP_REMOTE_API_SMOKE=1 bash scripts/release_preflight.sh`
3. 前端脚本语法通过: `node --check web/app.js`
4. Supabase 实测链路通过:
   - signup 200
   - password login 200
   - `/auth/v1/user` 200
   - `public.users` 可查到新增用户
5. RLS 隔离脚本通过: `bash scripts/rls_isolation_check.sh`
6. 新增 M2 DB 集成测试可在 CI 路径运行（本地默认跳过，需 `RUN_DB_TESTS=1`）
7. 远端 API 冒烟在当前执行环境存在网络不可达（`nvc-practice-api.vercel.app:443` 超时），建议在开发机或 GitHub Actions 手动 workflow 执行。

## 6. 当前状态评估

- 目前系统已具备“真实用户注册 + 登录 + 业务接口联调”的连续路径。
- 线上入口认知成本下降，后续用户测试可以只围绕 Supabase 主链路执行。

## 7. 遗留风险

1. 线上稳定性观测仍较薄弱（缺统一日志聚合与错误告警）。
2. 公开测试前仍需完成密钥轮换与脱敏。
3. 本地 DB 集成测试依赖 Docker 环境，开发机需保持 daemon 可用。
4. 远端 API 冒烟受执行环境网络约束，需在可达环境补跑并存档结果。

## 8. 下一阶段重点

1. 在 Supabase 生产/测试环境执行 `0004` 并完成用户隔离验证（A/B 用户交叉访问回归）。
2. 补充真实 Supabase JWT 端到端回归脚本，纳入发布检查清单。
3. 将前端从“联调台”升级到“用户可理解的练习流程页”。
4. 增加最小可观测性（请求链路、关键异常、基础告警）。
