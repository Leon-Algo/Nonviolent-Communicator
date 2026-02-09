# MVP PRD: NVC Practice Coach v0.2

## 0. 文档信息

- 版本: v0.2
- 日期: 2026-02-09
- 目的: 在 v0.1 基础上补齐可交付给设计与研发的实现细节
- 覆盖范围:
  - 页面级交互稿
  - API 字段定义
  - 数据表草案

---

## 1. v0.2 增量范围

本版本只补三件事:

1. 页面交互细化到组件、状态、关键文案与验收
2. API 契约细化到字段级（请求/响应/校验/错误码）
3. 数据模型细化到可执行的 PostgreSQL 草案

不在本版本内:

- UI 视觉稿与高保真设计
- 企业权限模型
- 多语言国际化方案

---

## 2. 页面级交互稿

### 2.1 页面清单

1. `P1 场景创建页`
2. `P2 对练会话页`
3. `P3 练习总结页`
4. `P4 次日复盘页`
5. `P5 个人进展页`

### 2.2 P1 场景创建页

**页面目标**

- 让用户在 2 分钟内完成场景配置并进入练习

**组件结构**

1. 模板区:
   - 给同事提反馈
   - 与上级对齐预期
   - 跨部门冲突协调
   - 自定义场景
2. 表单区:
   - 对方身份 `counterparty_role`
   - 关系状态 `relationship_level`
   - 沟通目标 `goal`
   - 主要难点 `pain_points[]`
   - 背景描述 `context`
   - 权力关系 `power_dynamic`
3. CTA:
   - `开始练习`

**关键交互**

1. 点击模板后自动填充示例文本，用户可编辑
2. `goal/context` 为空时禁用 `开始练习`
3. 输入超过上限时实时显示剩余字数与错误提示
4. 每 5 秒自动保存草稿

**关键状态**

- 初始空状态
- 加载状态（读取草稿）
- 校验失败状态（字段级错误）
- 提交失败状态（Toast + 保留输入）

**验收标准**

1. 首次用户从进入页面到发起会话中位时长 <= 120 秒
2. 表单校验错误可定位到字段并给出可操作文案
3. 刷新页面后草稿仍可恢复

### 2.3 P2 对练会话页

**页面目标**

- 完成 5-8 轮高质量练习并输出可执行反馈

**布局建议**

- Desktop: 左侧对话流，右侧反馈面板
- Mobile: 上方对话流，下方折叠反馈抽屉

**核心组件**

1. 对话区:
   - 消息列表
   - 输入框（多行）
   - 发送按钮
2. 反馈区:
   - OFNR 四维状态
   - 风险提示（评判、绝对化、人格化）
   - 建议替代句
   - `一键改写` 按钮
3. 会话控制:
   - 当前轮次 `turn/current`
   - `结束并生成行动卡`

**关键交互时序**

1. 用户发送消息
2. 前端立即展示用户消息（optimistic）
3. 进入 `AI 思考中` 状态并禁用重复发送
4. 返回 AI 回复 + OFNR 反馈 + 风险提示
5. 用户可选择:
   - 继续自然回复
   - 应用改写句后发送

**中断与恢复**

- 用户离开页面后再次进入，可恢复最近未完成会话
- 会话超时（30 分钟无操作）标记为 `abandoned`

**验收标准**

1. P95 响应耗时 < 6 秒
2. 连续 8 轮对话角色不漂移
3. 每轮至少提供 1 条可执行替代句

### 2.4 P3 练习总结页

**页面目标**

- 把练习结果压缩成“真实对话行动卡”

**组件结构**

1. 行动卡:
   - 开场句
   - 请求句
   - 兜底句
   - 触发点提醒
2. 操作区:
   - 编辑
   - 复制
   - 标记 `已计划使用`
3. 后续入口:
   - `开始新一轮练习`
   - `明日复盘提醒已开启`

**验收标准**

1. 用户可在 30 秒内复制可用脚本
2. 编辑后内容持久化
3. 可回跳查看原始会话上下文

### 2.5 P4 次日复盘页

**页面目标**

- 收集行为迁移数据并触发下一次练习

**问题结构**

1. `是否已在真实场景使用` (是/否)
2. `结果评分` (1-5)
3. `最大阻碍` (单选 + 可选备注)

**分支交互**

- 选择“否”时展示 `再练一次` 快捷入口
- 选择“是且评分<=2”时推荐“同场景重练”

**验收标准**

1. 填写完成时长 <= 60 秒
2. 结构化字段完整率 >= 95%

### 2.6 P5 个人进展页

**页面目标**

- 反馈训练成效，促进持续练习

**展示指标 (MVP)**

1. 本周练习次数
2. 行动卡生成次数
3. 真实使用次数
4. 最近 4 周结果评分趋势

**验收标准**

1. 指标与埋点数据一致性 >= 99%
2. 页面打开时间 < 2 秒（缓存命中）

---

## 3. API 字段定义（v1）

### 3.1 通用约定

- Base Path: `/api/v1`
- 鉴权: `Authorization: Bearer <token>`
- 时间: ISO-8601 UTC（如 `2026-02-09T08:30:00Z`）
- ID: UUID v4
- 幂等: 关键 POST 支持 `Idempotency-Key`

### 3.2 枚举定义

- `template_id`: `PEER_FEEDBACK | MANAGER_ALIGNMENT | CROSS_TEAM_CONFLICT | CUSTOM`
- `counterparty_role`: `PEER | MANAGER | REPORT | CLIENT | OTHER`
- `relationship_level`: `SMOOTH | NEUTRAL | TENSE`
- `power_dynamic`: `USER_HIGHER | PEER_LEVEL | COUNTERPART_HIGHER`
- `session_state`: `ACTIVE | COMPLETED | ABANDONED`
- `ofnr_status`: `MISSING | WEAK | GOOD`
- `risk_level`: `LOW | MEDIUM | HIGH`
- `blocker_code`: `NO_CHANCE | EMOTION_SPIKE | POWER_GAP | WORDING_ISSUE | OTHER`

### 3.3 创建场景

`POST /api/v1/scenes`

请求体:

```json
{
  "title": "和同事沟通延期风险",
  "template_id": "PEER_FEEDBACK",
  "counterparty_role": "PEER",
  "relationship_level": "TENSE",
  "goal": "确认新的里程碑并明确责任",
  "pain_points": ["对方容易防御", "我会急躁"],
  "context": "这个需求已经两次延期，影响发布节奏",
  "power_dynamic": "PEER_LEVEL"
}
```

字段校验:

- `title`: 1-80 字符
- `goal`: 1-240 字符
- `pain_points`: 0-5 项，每项 1-80 字符
- `context`: 1-1200 字符

响应体:

```json
{
  "scene_id": "f8851597-86dd-4b77-91d8-2648f6308f86",
  "status": "ACTIVE",
  "created_at": "2026-02-09T08:30:00Z"
}
```

### 3.4 开始会话

`POST /api/v1/sessions`

请求体:

```json
{
  "scene_id": "f8851597-86dd-4b77-91d8-2648f6308f86",
  "target_turns": 6
}
```

字段校验:

- `target_turns`: 5-8

响应体:

```json
{
  "session_id": "f6a764cd-f5da-4d2b-91b1-73e0939a8a50",
  "state": "ACTIVE",
  "current_turn": 0,
  "created_at": "2026-02-09T08:32:00Z"
}
```

### 3.5 发送消息并获取反馈

`POST /api/v1/sessions/{session_id}/messages`

请求体:

```json
{
  "client_message_id": "4c16e607-2c2f-4a89-bf20-4a33317b640a",
  "content": "你们总是拖延，导致我们每次都很被动。"
}
```

响应体:

```json
{
  "user_message_id": "de6bb68c-3c35-4fdb-a94c-f2eb1020a7b9",
  "assistant_message": {
    "message_id": "f20b8b24-17a3-4b63-b0a4-48ac6ba2f200",
    "content": "我理解你的着急，但你这句话让我有些被指责。你希望我们先对齐什么？"
  },
  "feedback": {
    "overall_score": 48,
    "risk_level": "HIGH",
    "ofnr": {
      "observation": {
        "status": "WEAK",
        "reason": "包含绝对化词语“总是”",
        "suggestion": "改为可观察事实，如“这个需求过去两周延期了两次”"
      },
      "feeling": {
        "status": "GOOD",
        "reason": "表达了被动和压力",
        "suggestion": ""
      },
      "need": {
        "status": "WEAK",
        "reason": "未明确具体需要",
        "suggestion": "补充需要确定性交付节奏"
      },
      "request": {
        "status": "MISSING",
        "reason": "缺少可执行请求",
        "suggestion": "提出具体时间点和动作"
      }
    },
    "next_best_sentence": "我观察到这个需求在过去两周延期了两次，我有些焦虑，因为我需要可预测的交付节奏。你愿意今天下班前一起确认里程碑吗？"
  },
  "turn": 1
}
```

### 3.6 改写

`POST /api/v1/sessions/{session_id}/rewrite`

请求体:

```json
{
  "source_message_id": "de6bb68c-3c35-4fdb-a94c-f2eb1020a7b9",
  "rewrite_style": "NEUTRAL"
}
```

响应体:

```json
{
  "rewrite_id": "88b56a74-92a7-4d9f-aebf-bc63e4f2e160",
  "rewritten_content": "我观察到这个需求近期延期了两次，我有些焦虑，因为我需要更稳定的节奏。你愿意和我一起确认一个新的里程碑吗？"
}
```

### 3.7 生成行动卡

`POST /api/v1/sessions/{session_id}/summary`

响应体:

```json
{
  "summary_id": "7711eb7c-98f5-42e6-9e86-5a0a3c9dc1ac",
  "opening_line": "我观察到这个需求近期延期了两次，我有些焦虑。",
  "request_line": "你愿意今天下班前和我一起确认新的里程碑吗？",
  "fallback_line": "如果今天不方便，我们可否约明早 10:00 快速对齐？",
  "risk_triggers": ["绝对化词语", "人格评价"],
  "created_at": "2026-02-09T08:45:00Z"
}
```

### 3.8 提交复盘

`POST /api/v1/reflections`

请求体:

```json
{
  "session_id": "f6a764cd-f5da-4d2b-91b1-73e0939a8a50",
  "used_in_real_world": true,
  "outcome_score": 4,
  "blocker_code": "WORDING_ISSUE",
  "blocker_note": "开场有点生硬，但后半段顺利"
}
```

响应体:

```json
{
  "reflection_id": "6b4aab56-6a65-4d0c-8f3f-5cd5f5be4f7f",
  "created_at": "2026-02-10T09:10:00Z"
}
```

### 3.9 获取周进展

`GET /api/v1/progress/weekly?week_start=2026-02-09`

响应体:

```json
{
  "week_start": "2026-02-09",
  "practice_count": 3,
  "summary_count": 3,
  "real_world_used_count": 1,
  "avg_outcome_score": 4.0
}
```

### 3.10 错误码

- `400 VALIDATION_ERROR`
- `401 UNAUTHORIZED`
- `403 FORBIDDEN`
- `404 NOT_FOUND`
- `409 CONFLICT`
- `422 SAFETY_BLOCKED`
- `429 RATE_LIMITED`
- `500 INTERNAL_ERROR`

错误响应统一结构:

```json
{
  "error_code": "VALIDATION_ERROR",
  "message": "goal is required",
  "request_id": "f2cf1f5e-3d4d-4f1f-bffc-e103a7f03a8a"
}
```

---

## 4. 数据表草案（PostgreSQL）

### 4.1 ER 关系

- `users` 1:N `scenes`
- `scenes` 1:N `sessions`
- `sessions` 1:N `messages`
- `messages(user)` 1:1 `feedback_items`
- `messages(user)` 1:N `rewrites`
- `sessions` 1:1 `summaries`
- `sessions` 1:0..1 `reflections`

### 4.2 字段草案

### users

- `id` UUID PK
- `email` TEXT UNIQUE NOT NULL
- `display_name` TEXT
- `locale` TEXT NOT NULL DEFAULT `zh-CN`
- `timezone` TEXT NOT NULL DEFAULT `UTC`
- `created_at` TIMESTAMPTZ NOT NULL DEFAULT NOW()
- `updated_at` TIMESTAMPTZ NOT NULL DEFAULT NOW()

### scenes

- `id` UUID PK
- `user_id` UUID NOT NULL FK -> users(id)
- `title` VARCHAR(80) NOT NULL
- `template_id` VARCHAR(32) NOT NULL
- `counterparty_role` VARCHAR(16) NOT NULL
- `relationship_level` VARCHAR(16) NOT NULL
- `goal` VARCHAR(240) NOT NULL
- `pain_points` JSONB NOT NULL DEFAULT `[]`
- `context` TEXT NOT NULL
- `power_dynamic` VARCHAR(24) NOT NULL
- `status` VARCHAR(16) NOT NULL DEFAULT `ACTIVE`
- `created_at` TIMESTAMPTZ NOT NULL DEFAULT NOW()
- `updated_at` TIMESTAMPTZ NOT NULL DEFAULT NOW()

索引:

- `idx_scenes_user_updated (user_id, updated_at DESC)`

### sessions

- `id` UUID PK
- `user_id` UUID NOT NULL FK -> users(id)
- `scene_id` UUID NOT NULL FK -> scenes(id)
- `state` VARCHAR(16) NOT NULL DEFAULT `ACTIVE`
- `target_turns` SMALLINT NOT NULL
- `current_turn` SMALLINT NOT NULL DEFAULT 0
- `started_at` TIMESTAMPTZ NOT NULL DEFAULT NOW()
- `ended_at` TIMESTAMPTZ
- `created_at` TIMESTAMPTZ NOT NULL DEFAULT NOW()

约束:

- `target_turns BETWEEN 5 AND 8`
- `current_turn >= 0`

索引:

- `idx_sessions_scene_state (scene_id, state)`
- `idx_sessions_user_created (user_id, created_at DESC)`

### messages

- `id` UUID PK
- `session_id` UUID NOT NULL FK -> sessions(id)
- `role` VARCHAR(16) NOT NULL (`USER | ASSISTANT | SYSTEM`)
- `turn_no` SMALLINT NOT NULL
- `content` TEXT NOT NULL
- `latency_ms` INTEGER
- `token_in` INTEGER
- `token_out` INTEGER
- `created_at` TIMESTAMPTZ NOT NULL DEFAULT NOW()

索引:

- `idx_messages_session_turn (session_id, turn_no, created_at)`

### feedback_items

- `id` UUID PK
- `session_id` UUID NOT NULL FK -> sessions(id)
- `user_message_id` UUID NOT NULL UNIQUE FK -> messages(id)
- `overall_score` SMALLINT NOT NULL
- `risk_level` VARCHAR(16) NOT NULL
- `ofnr_detail` JSONB NOT NULL
- `next_best_sentence` TEXT NOT NULL
- `created_at` TIMESTAMPTZ NOT NULL DEFAULT NOW()

约束:

- `overall_score BETWEEN 0 AND 100`

### rewrites

- `id` UUID PK
- `session_id` UUID NOT NULL FK -> sessions(id)
- `source_message_id` UUID NOT NULL FK -> messages(id)
- `rewrite_style` VARCHAR(16) NOT NULL
- `rewritten_content` TEXT NOT NULL
- `accepted` BOOLEAN NOT NULL DEFAULT FALSE
- `created_at` TIMESTAMPTZ NOT NULL DEFAULT NOW()

索引:

- `idx_rewrites_source (source_message_id, created_at DESC)`

### summaries

- `id` UUID PK
- `session_id` UUID NOT NULL UNIQUE FK -> sessions(id)
- `opening_line` TEXT NOT NULL
- `request_line` TEXT NOT NULL
- `fallback_line` TEXT
- `risk_triggers` JSONB NOT NULL DEFAULT `[]`
- `edited_by_user` BOOLEAN NOT NULL DEFAULT FALSE
- `created_at` TIMESTAMPTZ NOT NULL DEFAULT NOW()
- `updated_at` TIMESTAMPTZ NOT NULL DEFAULT NOW()

### reflections

- `id` UUID PK
- `user_id` UUID NOT NULL FK -> users(id)
- `session_id` UUID NOT NULL UNIQUE FK -> sessions(id)
- `used_in_real_world` BOOLEAN NOT NULL
- `outcome_score` SMALLINT
- `blocker_code` VARCHAR(24)
- `blocker_note` TEXT
- `created_at` TIMESTAMPTZ NOT NULL DEFAULT NOW()

约束:

- `outcome_score IS NULL OR (outcome_score BETWEEN 1 AND 5)`

### event_logs

- `id` BIGSERIAL PK
- `user_id` UUID NOT NULL FK -> users(id)
- `session_id` UUID FK -> sessions(id)
- `event_name` VARCHAR(64) NOT NULL
- `event_props` JSONB NOT NULL DEFAULT `{}`
- `client_ts` TIMESTAMPTZ
- `server_ts` TIMESTAMPTZ NOT NULL DEFAULT NOW()

索引:

- `idx_event_logs_event_time (event_name, server_ts DESC)`
- `idx_event_logs_user_time (user_id, server_ts DESC)`

### 4.3 SQL 草案（可直接给后端起步）

```sql
CREATE TABLE users (
  id UUID PRIMARY KEY,
  email TEXT UNIQUE NOT NULL,
  display_name TEXT,
  locale TEXT NOT NULL DEFAULT 'zh-CN',
  timezone TEXT NOT NULL DEFAULT 'UTC',
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE scenes (
  id UUID PRIMARY KEY,
  user_id UUID NOT NULL REFERENCES users(id),
  title VARCHAR(80) NOT NULL,
  template_id VARCHAR(32) NOT NULL,
  counterparty_role VARCHAR(16) NOT NULL,
  relationship_level VARCHAR(16) NOT NULL,
  goal VARCHAR(240) NOT NULL,
  pain_points JSONB NOT NULL DEFAULT '[]'::jsonb,
  context TEXT NOT NULL,
  power_dynamic VARCHAR(24) NOT NULL,
  status VARCHAR(16) NOT NULL DEFAULT 'ACTIVE',
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE sessions (
  id UUID PRIMARY KEY,
  user_id UUID NOT NULL REFERENCES users(id),
  scene_id UUID NOT NULL REFERENCES scenes(id),
  state VARCHAR(16) NOT NULL DEFAULT 'ACTIVE',
  target_turns SMALLINT NOT NULL CHECK (target_turns BETWEEN 5 AND 8),
  current_turn SMALLINT NOT NULL DEFAULT 0 CHECK (current_turn >= 0),
  started_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  ended_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE messages (
  id UUID PRIMARY KEY,
  session_id UUID NOT NULL REFERENCES sessions(id),
  role VARCHAR(16) NOT NULL,
  turn_no SMALLINT NOT NULL,
  content TEXT NOT NULL,
  latency_ms INTEGER,
  token_in INTEGER,
  token_out INTEGER,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE feedback_items (
  id UUID PRIMARY KEY,
  session_id UUID NOT NULL REFERENCES sessions(id),
  user_message_id UUID UNIQUE NOT NULL REFERENCES messages(id),
  overall_score SMALLINT NOT NULL CHECK (overall_score BETWEEN 0 AND 100),
  risk_level VARCHAR(16) NOT NULL,
  ofnr_detail JSONB NOT NULL,
  next_best_sentence TEXT NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE rewrites (
  id UUID PRIMARY KEY,
  session_id UUID NOT NULL REFERENCES sessions(id),
  source_message_id UUID NOT NULL REFERENCES messages(id),
  rewrite_style VARCHAR(16) NOT NULL,
  rewritten_content TEXT NOT NULL,
  accepted BOOLEAN NOT NULL DEFAULT FALSE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE summaries (
  id UUID PRIMARY KEY,
  session_id UUID UNIQUE NOT NULL REFERENCES sessions(id),
  opening_line TEXT NOT NULL,
  request_line TEXT NOT NULL,
  fallback_line TEXT,
  risk_triggers JSONB NOT NULL DEFAULT '[]'::jsonb,
  edited_by_user BOOLEAN NOT NULL DEFAULT FALSE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE reflections (
  id UUID PRIMARY KEY,
  user_id UUID NOT NULL REFERENCES users(id),
  session_id UUID UNIQUE NOT NULL REFERENCES sessions(id),
  used_in_real_world BOOLEAN NOT NULL,
  outcome_score SMALLINT CHECK (outcome_score BETWEEN 1 AND 5),
  blocker_code VARCHAR(24),
  blocker_note TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE event_logs (
  id BIGSERIAL PRIMARY KEY,
  user_id UUID NOT NULL REFERENCES users(id),
  session_id UUID REFERENCES sessions(id),
  event_name VARCHAR(64) NOT NULL,
  event_props JSONB NOT NULL DEFAULT '{}'::jsonb,
  client_ts TIMESTAMPTZ,
  server_ts TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
```

---

## 5. 需求到实现映射

1. `实时 OFNR 反馈`
   - API: `/sessions/{id}/messages`
   - 表: `feedback_items`
2. `一键改写`
   - API: `/sessions/{id}/rewrite`
   - 表: `rewrites`
3. `行动卡`
   - API: `/sessions/{id}/summary`
   - 表: `summaries`
4. `次日复盘`
   - API: `/reflections`
   - 表: `reflections`

---

## 6. v0.3 建议输入

进入 v0.3 前建议先补:

1. 10 条标准化评测集（检验角色稳定与改写偏移）
2. 前端低保真线框图（P1-P5）
3. 错误恢复策略（超时重试、幂等冲突、断网重连）
