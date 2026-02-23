# 文档总览

本文档用于管理当前项目文档结构，目标是保持“少而清晰、单一事实来源”。

更新时间: 2026-02-23（Cloudflare 迁移复盘同步）

## 核心文档（仅保留这些）

1. `docs/PRD.md`
   - 产品目标、范围、用户流程、验收标准
2. `docs/TECHNICAL_SOLUTION.md`
   - 技术架构、鉴权策略、数据库策略、部署策略、迁移故障根因
3. `docs/DEVELOPMENT_PLAN.md`
   - 里程碑、当前任务、下一阶段计划
4. `docs/SETUP_AND_TESTING.md`
   - 本地/线上配置、部署步骤、排障与验收流程
5. `docs/STAGE_REVIEW.md`
   - 阶段复盘、关键决策、问题与修复轨迹

## Cloudflare 迁移复盘阅读路径（建议）

1. 先读 `docs/STAGE_REVIEW.md` 的“2026-02-23”与“迁移故障复盘”
2. 再读 `docs/TECHNICAL_SOLUTION.md` 的“迁移事故复盘”与“防回归规则”
3. 最后读 `docs/SETUP_AND_TESTING.md` 的“迁移排障标准流程”

这样可以按“发生了什么 -> 为什么 -> 怎么修 -> 怎么防复发”完整理解。

## 契约与实现资产（非文档）

- API 契约: `spec/openapi/nvc-practice-coach.v1.yaml`
- AI 回归样本: `spec/evals/ofnr_evalset_v0.2.jsonl`
- AI 回归脚本: `scripts/run_ofnr_eval.py`
- Vercel 发布脚本: `scripts/vercel_release.sh`
- Cloudflare 发布脚本: `scripts/cloudflare_pages_release.sh`
- 数据库迁移: `db/migrations/*.sql`

## 维护规则

1. 不再创建 `v0.x` 多副本文档；直接更新核心文档。
2. 阶段性变更统一写入 `docs/STAGE_REVIEW.md`。
3. 接口字段与错误码以 OpenAPI 为准，文档只写解释与约束。
4. 部署/迁移相关变更必须同时更新:
   - `docs/TECHNICAL_SOLUTION.md`
   - `docs/SETUP_AND_TESTING.md`
   - `docs/STAGE_REVIEW.md`
   - `docs/DEVELOPMENT_PLAN.md`
5. 历史版本通过 Git 提交记录追溯，不再保留同类文档副本。
