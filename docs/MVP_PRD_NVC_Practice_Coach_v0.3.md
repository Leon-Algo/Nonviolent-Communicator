# MVP PRD: NVC Practice Coach v0.3

## 0. 文档信息

- 版本: v0.3
- 日期: 2026-02-10
- 目标: 把 v0.2 的产品定义推进到可执行实现资产

## 1. 本次新增交付物

1. OpenAPI 初版
   - 路径: `spec/openapi/nvc-practice-coach.v1.yaml`
   - 作用: 作为前后端联调契约与接口 Mock 输入
2. OFNR 评测集样例（10 条）
   - 路径: `spec/evals/ofnr_evalset_v0.1.jsonl`
   - 作用: 用于提示词迭代与模型回归测试
3. 数据库迁移脚本草案
   - 路径: `db/migrations/0001_init_nvc_practice.sql`
   - 作用: 初始化 MVP 阶段核心表结构与索引

## 2. 与 v0.2 的对齐说明

- API 路由与字段命名对齐 v0.2 第 3 章
- 表结构与业务关系对齐 v0.2 第 4 章
- 评测集围绕 v0.2 的质量目标:
  - 角色一致性
  - OFNR 可执行反馈
  - 改写不偏离原意

## 3. 使用方式

### 3.1 后端联调

1. 先以 OpenAPI 文件生成服务端/客户端模型
2. 在 staging 使用迁移脚本建表
3. 逐个对齐接口响应结构与错误码

### 3.2 AI 质量回归

1. 读取 `ofnr_evalset_v0.1.jsonl`
2. 对每条输入生成:
   - 风险等级
   - OFNR 四维判定
   - 一条改写建议
3. 与 `expected` 对比计算命中率

建议最低通过线:

- 风险等级命中率 >= 80%
- OFNR 四维平均命中率 >= 75%
- `must_flag` 命中率 >= 80%

### 3.3 数据库初始化

1. 在 PostgreSQL 14+ 执行 `db/migrations/0001_init_nvc_practice.sql`
2. 确认表、索引、约束均创建成功
3. 以最小种子数据验证 6 条核心 API

## 4. 验收清单（v0.3）

1. OpenAPI 能通过语法校验（OpenAPI 3.1）
2. 迁移脚本可在空库执行成功
3. 评测集可被脚本按 JSONL 逐行读取
4. 字段命名在 PRD、OpenAPI、SQL 三处一致

## 5. 当前假设

1. 鉴权采用 Bearer Token（具体身份系统后续接入）
2. 时区统一存储 UTC，前端按用户时区展示
3. MVP 暂不引入组织级多租户隔离

## 6. v0.4 建议

1. 补充 OpenAPI 示例响应覆盖错误路径（422/429）
2. 增加评测脚本与 CI 回归任务
3. 为 `event_logs` 增加分区策略（按月）
4. 补齐复盘提醒任务调度表与重试机制

