# 开发计划 v0.4（执行版）

## 1. 目标

- 把项目从“可联调”推进到“可稳定迭代 + 可小范围试用”。
- 优先解决稳定性、可回归性和上线前安全底线。

## 2. 里程碑

### M1 稳定性基线（本轮）

1. 统一错误响应契约（`error_code/message/request_id`）
2. 消息接口幂等（`client_message_id`）
3. 基础自动化测试（后端）
4. CI 自动跑测试

验收标准:

- 常见错误响应均符合统一结构
- 同一 `client_message_id` 重试返回同一条业务结果
- `pytest backend/tests -q` 通过
- GitHub Actions `backend-tests` 工作流通过

### M2 上线前安全基线

1. Mock Token 切换真实鉴权（JWT/Supabase Auth）
2. Supabase RLS 策略上线
3. 密钥治理（轮换、分环境、脱敏）

验收标准:

- 未授权用户无法访问他人资源
- RLS 策略通过隔离测试
- 明文敏感信息不再出现在仓库与日志

### M3 产品可用性提升

1. 前端从联调台升级为完整 MVP 交互流
2. 会话历史、改写采纳、总结卡片可视化
3. 关键指标看板（练习次数、采纳率、复盘转化）

验收标准:

- 用户可在页面完成完整练习闭环，无需手工复制 ID
- 关键行为可追踪并可复盘

## 3. 本轮已落地（M1）

1. 错误契约:
   - `backend/app/core/errors.py`
   - `backend/app/main.py`
2. 消息幂等:
   - `db/migrations/0002_add_idempotency_keys.sql`
   - `backend/app/api/routers/sessions.py`
3. 自动化测试:
   - `backend/tests/test_error_contract.py`
   - `backend/tests/test_errors_module.py`
   - `backend/tests/test_nvc_service.py`
4. CI:
   - `.github/workflows/backend-tests.yml`

## 4. 下一步（按顺序）

1. 确认目标环境已执行 `0002_add_idempotency_keys.sql`
2. 运行并确认 `scripts/api_smoke_test.sh` 幂等检查通过
3. 推进 M2（鉴权 + RLS）设计与实现
4. 推进 M3 前端可用性改造

## 5. 需要你配合的事项

1. 鉴权选型确认（建议优先 Supabase Auth + JWT）
2. 确认是否同时存在其他 Supabase 环境（如 staging），若有则同步执行 `0002`

备注:

- 当前 `.env` 指向的 Supabase 库已执行 `0002_add_idempotency_keys.sql`，并通过本地 smoke 幂等回归。
