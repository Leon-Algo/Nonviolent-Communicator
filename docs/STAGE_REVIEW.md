# 阶段复盘（整合）

## 1. 复盘范围

- 时间范围: 2026-02-11 至 2026-02-13
- 覆盖阶段: 从 MVP 首版联调到安全基线、回归闭环与 M3 可用性落地

## 2. 时间线摘要

### 2026-02-11

关键进展:

1. 核心 API 链路可运行（场景/会话/消息/改写/总结/复盘/进度）
2. 前后端完成 Vercel 部署并可在线联调
3. 修复核心稳定性问题（Pooler prepared statement、SQL 参数歧义、模型响应容错）

### 2026-02-12

关键进展:

1. 鉴权主链路收敛为 Supabase JWT（线上）
2. `auth.users -> public.users` 自动同步迁移落地（`0003`）
3. RLS 与 claim 兼容修复落地（`0004`, `0005`）
4. 补齐自动化资产（集成测试、RLS 脚本、JWT 冒烟、预检 workflow）

### 2026-02-13

关键进展:

1. 前端重构为引导式 3 步练习流（登录 -> 对练 -> 总结复盘）
2. 新增跨会话历史回看能力（`GET /sessions` + `GET /sessions/{id}/history`）
3. 生产环境部署完成（前端/后端）
4. 线上完整预检通过（含 RLS 与 JWT API smoke）

## 3. 关键问题与根因

1. 前端 `Failed to fetch`
   - 根因: 跨域配置与历史本地配置混用，导致请求目标不稳定。
2. 消息接口 500
   - 根因: DB 连接策略与 SQL 参数处理在特定链路下不稳定。
3. Supabase 注册 429
   - 根因: Auth 邮件发送频控触发。
4. 云端预检早期失败（Event loop is closed）
   - 根因: `APP_ENV=test` 下 asyncpg 连接在 CI 中出现事件循环污染。
   - 处理: `test` 环境改用 `NullPool`，预检恢复通过。

## 4. 本阶段关键决策

1. 线上仅开放 Supabase 鉴权入口，隐藏 mock 入口。
2. mock 仅用于本地联调，并加生产安全开关限制。
3. 发布前必须执行自动化预检，且至少覆盖:
   - 后端测试
   - RLS 隔离校验
   - Supabase JWT API 冒烟

## 5. 验证结果

本地验证:

1. `pytest backend/tests -q` 通过（17 passed, 2 skipped）
2. `node --check web/app.js` 通过
3. `SKIP_REMOTE_API_SMOKE=1 bash scripts/release_preflight.sh` 通过
4. 历史回看本地冒烟通过（列表 + 单会话详情）

云端验证:

1. GitHub Actions 完整预检通过:
   - `https://github.com/Leon-Algo/Nonviolent-Communicator/actions/runs/21979380349`
2. 该次预检已包含并通过:
   - RLS isolation check
   - Supabase JWT API smoke（含历史回看接口路径）

## 6. 当前状态结论

项目已进入“可上线演示、可回归验证、具备基础安全隔离”的阶段，且 M3 核心可用性已落地。

## 7. 下一阶段重点

1. 会话历史筛选与回看体验增强（状态/时间/关键词、按轮跳转）
2. 行动卡与复盘可视化优化（复制、导出、可读性）
3. 最小可观测性建设（结构化日志、5xx/慢请求告警）
4. OFNR 评测集回归自动化（并入预检）
