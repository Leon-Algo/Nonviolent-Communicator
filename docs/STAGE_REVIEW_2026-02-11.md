# 阶段复盘（2026-02-11）

## 1. 复盘范围

- 复盘日期: 2026-02-11
- 覆盖阶段: MVP 从方案定义到首版可用联调（v0.1 -> v0.3 + 可运行代码）
- 目标: 明确已完成内容、关键问题根因、修复结果与下一阶段重点

## 2. 已完成交付

1. 产品与方案文档
   - `docs/MVP_PRD_NVC_Practice_Coach.md`
   - `docs/MVP_PRD_NVC_Practice_Coach_v0.2.md`
   - `docs/MVP_PRD_NVC_Practice_Coach_v0.3.md`
   - `docs/TECHNICAL_SOLUTION_PYTHON_SUPABASE_VERCEL.md`
2. 契约与数据资产
   - `spec/openapi/nvc-practice-coach.v1.yaml`
   - `spec/evals/ofnr_evalset_v0.1.jsonl`
   - `db/migrations/0001_init_nvc_practice.sql`
3. 后端可运行能力（FastAPI + Supabase）
   - 场景、会话、消息反馈、改写、总结、复盘、周进度接口全部落地
4. 前端联调页
   - `web/` 已支持创建场景、创建会话、发送消息与结果展示
5. 部署链路
   - 前端与后端已部署到 Vercel，可用于在线联调

## 3. 本阶段关键问题与根因

1. `Failed to fetch`（前端）
   - 根因: 前端跨域直连 API + 历史本地存储配置导致请求路径不稳定
2. 后端启动即 500（Vercel）
   - 根因: 环境变量中布尔值包含空白字符，配置解析失败
3. 发送消息接口 500（核心）
   - 根因 A: Supabase Pooler (6543) 与 asyncpg prepared statements 冲突，触发 `DuplicatePreparedStatementError`
   - 根因 B: `UPDATE sessions` 中参数类型推断歧义，触发 `AmbiguousParameterError`
4. 模型调用脆弱性
   - 根因: 默认假设 `choices[0].message.content` 始终是字符串，异常返回结构可能触发未捕获异常

## 4. 修复与结果

1. 数据库连接兼容修复
   - 文件: `backend/app/db/session.py`
   - 动作: `create_async_engine` 增加 `connect_args={"statement_cache_size": 0}`
   - 结果: 规避 Pooler prepared statement 冲突
2. 会话更新 SQL 修复
   - 文件: `backend/app/api/routers/sessions.py`
   - 动作: 引入 `is_completed` 布尔参数，避免同一参数同时参与赋值和比较
   - 结果: 消除 `AmbiguousParameterError`
3. 模型响应容错增强
   - 文件: `backend/app/services/nvc_service.py`
   - 动作: 增强 `choices/message/content` 提取逻辑，兼容字符串与文本片段列表
   - 结果: 模型异常响应下可平稳降级，不再直接 500
4. 配置健壮性修复
   - 文件: `backend/app/core/config.py`
   - 动作: `SettingsConfigDict(extra="ignore")`，忽略无关键并保留主配置解析
   - 结果: 本地统一 `.env` 下后端可稳定启动
5. 依赖补齐
   - 文件: `backend/pyproject.toml`
   - 动作: 显式加入 `greenlet`
   - 结果: 避免部分本地运行环境的 SQLAlchemy 异步执行异常

## 5. 当前验证结论

已完成联调验证链路（本地与线上数据写入均验证）:

1. 创建场景 -> 成功
2. 创建会话 -> 成功
3. 发送消息并获取反馈 -> 成功（返回 assistant 回复 + OFNR 反馈）
4. 改写接口 -> 成功
5. 总结接口 -> 成功
6. 复盘接口 -> 成功
7. 周进度接口 -> 成功

## 6. 阶段结论

- 结论: MVP 核心流程已从“可设计”进入“可运行、可联调、可迭代”阶段。
- 当前系统已具备继续做小范围真实用户测试的工程基础。

## 7. 遗留风险与技术债

1. 鉴权仍为 Mock Token，尚未接入真实身份体系
2. 尚未引入系统化自动化测试（集成测试/回归测试）
3. Supabase RLS 未开启（公开测试前必须完成）
4. 秘钥仍处于开发期明文管理，正式环境前需轮换与脱敏

## 8. 下一阶段计划（v0.4）

1. 建立最小集成测试（覆盖 `scenes -> sessions -> messages` 主链路）
2. 完成 RLS 方案并验证用户级数据隔离
3. 增加消息接口幂等（基于 `client_message_id`）
4. 增加线上错误观测（请求 ID、关键异常聚合）
5. 优化前端交互层（会话历史、可视化反馈、错误提示分级）

对应执行方案文档:

- `docs/DEV_PLAN_v0.4.md`
