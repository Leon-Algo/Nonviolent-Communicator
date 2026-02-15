# 文档总览

本文档用于管理当前项目的文档结构，目标是保持“少而清晰、单一事实来源”。

更新时间: 2026-02-13

## 核心文档（仅保留这些）

1. `docs/PRD.md`
   - 产品目标、范围、用户流程、验收标准
2. `docs/TECHNICAL_SOLUTION.md`
   - 技术架构、鉴权策略、数据库策略、部署策略
3. `docs/DEVELOPMENT_PLAN.md`
   - 里程碑、优先级、当前待开发事项
4. `docs/SETUP_AND_TESTING.md`
   - 本地/线上配置、迁移执行、冒烟和预检步骤
5. `docs/STAGE_REVIEW.md`
   - 阶段复盘与关键决策记录

## 契约与实现资产（非文档）

- API 契约: `spec/openapi/nvc-practice-coach.v1.yaml`
- AI 回归样本: `spec/evals/ofnr_evalset_v0.2.jsonl`
- AI 回归脚本: `scripts/run_ofnr_eval.py`
- 数据库迁移: `db/migrations/*.sql`

## 维护规则

1. 不再创建 `v0.x` 多副本文档；直接更新核心文档。
2. 阶段性变更写入 `docs/STAGE_REVIEW.md`，避免按日期分裂成多个文件。
3. 接口字段与错误码以 OpenAPI 为准，文档只写解释与约束，不重复堆字段细节。
4. 历史版本通过 Git 提交记录追溯，不再保留大量同类文档副本。
