# Task Plan: planning-with-files 深入实践

## Goal
在当前仓库中落地 planning-with-files 工作流，建立稳定的文件化上下文，并基于现有项目状态推进一个可执行的下一阶段实践切片。

## Current Phase
Phase 3

## Phases

### Phase 1: Requirements & Discovery
- [x] 确认用户目标是以当前项目为样本，快速起手并深入实践 planning-with-files
- [x] 盘点仓库结构、现有文档、工作区改动与潜在切入点
- [x] 将首轮发现写入 findings.md
- **Status:** complete

### Phase 2: Planning & Structure
- [x] 在项目根目录创建 task_plan.md、findings.md、progress.md
- [x] 明确本轮实践的目标、阶段和边界
- [x] 锁定下一步要执行的具体切片
- **Status:** complete

### Phase 3: Implementation
- [x] 读取真实前端入口并评估如何把 `web/ui-practice-focus-draft.html` 的思路迁移进去
- [x] 为 `UX2` 落一个最小可验证实现：未登录时保留输入、引导登录、登录成功后自动续发
- [ ] 继续推进 `UX1` 的正式页面结构重排
- [ ] 每个关键发现和决策同步到 planning 文件
- [ ] 避免覆盖现有未提交改动
- **Status:** in_progress

### Phase 4: Testing & Verification
- [x] 运行与改动范围匹配的验证命令
- [ ] 将验证结果和残留风险记录到 progress.md
- [ ] 复核是否满足本轮切片目标
- **Status:** in_progress

### Phase 5: Delivery
- [ ] 总结本轮输出与剩余事项
- [ ] 给出下一轮如何继续使用 planning-with-files 的明确入口
- [ ] 向用户交付结果
- **Status:** pending

## Key Questions
1. 当前仓库里最适合拿来做 planning-with-files 深入实践的切片是什么？
2. 已存在的未提交文档改动和 `web/ui-practice-focus-draft.html` 应如何纳入计划而不互相覆盖？
3. 哪些验证步骤能最快证明下一轮改动是有效的？

## Decisions Made
| Decision | Rationale |
|----------|-----------|
| 先在当前项目根目录落地 planning 文件，而不是只讲方法论 | 该技能的核心价值是把上下文写入项目磁盘，先建工作内存比继续口头规划更有效 |
| 将本轮目标定义为“建立工作流 + 锁定一个具体实践切片” | 用户要快速起手，先把方法跑通，再进入代码/产品层面的连续迭代 |
| 将现有脏工作区视为约束条件写入计划 | 当前 `docs/*` 与 `web/ui-practice-focus-draft.html` 已有改动，后续实施必须避让或吸收这些变更 |
| 将首个真实实践切片锁定为 `UX1 -> UX2` | `docs/DEVELOPMENT_PLAN.md` 已把它列为当前 P0，且仓库里已有对应草稿页可作为实现锚点 |
| 真实实施入口聚焦 `web/index.html`、`web/styles.css`、`web/app.js` | 正式页面结构、样式和交互逻辑都集中在这三个文件中，迁移草稿必须同时调整它们 |
| `UX2` 需要显式的“待续发”状态，而不是只改按钮文案 | 当前 `sendPracticeTurn()` 在入口就要求 auth token，登录成功后也不会自动恢复发送动作 |
| 本轮先实现 `UX2` 最小闭环，不同时大改 `UX1` 页面结构 | 这样可以在低风险下验证“先输入后登录”链路，并保留后续继续重排页面的空间 |

## Errors Encountered
| Error | Attempt | Resolution |
|-------|---------|------------|
| `install-skill-from-github.py` 默认下载模式触发 Python SSL 证书校验失败 | 1 | 改用 `--method git` 完成安装 |

## Notes
- 后续每完成一个阶段，都要同步更新本文件状态。
- 若继续读取多份文档或网页结果，需要立即把关键信息写入 findings.md。
- 在开始具体实现前，先重新读取本文件，避免偏离“练习优先”的项目方向。
- 当前已确认的实践入口是把 `web/ui-practice-focus-draft.html` 对接到真实前端入口，而不是继续抽象讨论。
- 当前发现的核心结构冲突：正式首页把登录、自检放在练习区之前，这与 `UX1` 的目标直接相反。
- 当前发现的核心交互冲突：发送按钮没有“保存输入 -> 引导登录 -> 登录后自动续发”的机制。
- 当前已完成的真实实现：`startPracticeBtn` 支持 auth gate，`loginSupabase()` / `signupSupabase()` 支持自动续发。
