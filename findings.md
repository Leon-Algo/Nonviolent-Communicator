# Findings & Decisions

## Requirements
- 用户希望在当前项目内快速起手，并用 planning-with-files 的最佳实践进行深入实践。
- 本轮不只是解释技能，而是要在仓库里实际建立可持续使用的 planning 文件体系。
- 需要在不破坏现有未提交改动的前提下推进下一步实践。

## Research Findings
- 仓库是 NVC 练习产品 MVP，技术栈覆盖 `backend/` FastAPI、`web/` 前端静态页、`functions/` Cloudflare Pages Functions、`db/migrations/` SQL 迁移和 `scripts/` 验证脚本。
- `README.md` 显示当前产品主链路是“登录 -> 对练 -> 复盘”，并且前后端部署、PWA、历史会话和导出能力都已经具备。
- `docs/STAGE_REVIEW.md` 表明项目当前已完成 Cloudflare 迁移稳定化，下一阶段重点转向“练习优先”信息架构和“先输入后登录”体验优化。
- `docs/README.md` 说明文档体系已经收敛，核心事实来源集中在 `PRD`、`TECHNICAL_SOLUTION`、`DEVELOPMENT_PLAN`、`SETUP_AND_TESTING`、`STAGE_REVIEW`。
- 当前工作区不是干净状态：`docs/DEVELOPMENT_PLAN.md`、`docs/PRD.md`、`docs/README.md`、`docs/STAGE_REVIEW.md` 有未提交修改，`web/ui-practice-focus-draft.html` 是未跟踪文件。
- `docs/DEVELOPMENT_PLAN.md` 把当前优先级明确设为 `UX1 -> UX2`，也就是先做“练习优先”信息架构，再做“先输入后登录”的交互续发链路。
- `web/ui-practice-focus-draft.html` 已经给出一套清晰的草稿：首屏只保留场景、目标、消息输入和主 CTA；登录、连接自检、新手引导、历史复盘全部降级到辅助抽屉。
- `web/index.html` 的正式实现仍是典型三步流：Hero -> Stepper -> 新手引导 -> 登录面板 -> 快速自检 -> 练习面板 -> 反馈/历史/总结。
- `web/app.js` 已经拥有较完整的练习、登录、历史和失败态逻辑，因此下一步的关键不是重写业务逻辑，而是把现有逻辑重新挂接到新的界面信息架构上。
- 正式实现里已经有可复用的能力入口：`gotoPracticeFromAuthBtn`、`runQuickCheckBtn`、`/health-backend` 提示、`sendPracticeTurn()`、错误分类提示等，这意味着 `UX2` 可能主要是交互编排而不是底层 API 新增。
- `loginSupabase()` 登录成功后会拉取历史，但不会继续任何“发送前被打断”的动作。
- `sendPracticeTurn()` 在函数开头调用 `getConfig({ requireAuthToken: true })`，因此用户即使已经填写场景和消息，也会在发送时直接因为未登录而失败。
- 当前事件绑定里，`startPracticeBtn` 和 `sendMessageBtn` 都是直接调用 `sendPracticeTurn()`；这说明要实现“先输入后登录”，至少需要在按钮层或发送函数外层新增一个登录门禁与续发机制。
- 已实现的最小闭环如下：
- `web/app.js` 新增 `pendingPracticeAction`、`queuePendingPracticeAction()`、`resumePendingPracticeAction()`、`handlePracticeAttempt()`。
- `startPracticeBtn` 现在先经过 auth gate；若未登录，会保留当前输入并滚动到登录区。
- `loginSupabase()` 与自动登录注册分支在成功后会尝试恢复待发送动作。
- `web/index.html` 已补充对应文案，明确告诉用户“可先填写，登录后自动继续”。

## Technical Decisions
| Decision | Rationale |
|----------|-----------|
| planning 文件放在项目根目录 | 这是技能定义的标准用法，便于后续每次进入仓库都能恢复上下文 |
| 将首个深入实践切片优先对准“练习优先 UX / 信息架构”方向 | 这是文档里已经明确的下一阶段重点，也与现有 `web/ui-practice-focus-draft.html` 形成自然衔接 |
| 先记录脏工作区，再决定是否吸收现有草稿 | 先识别约束可以避免后续误覆盖用户已有工作 |
| 下一步先读真实前端入口，再决定如何迁移草稿 | 草稿已经足够清晰，当前缺的不是继续发散，而是与现有实现对位 |
| 先做结构重排，再决定是否深改发送链路 | 从现有代码看，页面信息架构是更大的摩擦点，且能最快体现 `planning-with-files` 的阶段推进价值 |
| `UX2` 的最低可行实现应优先做“登录成功后自动续发” | 这样能最小改动验证“先输入后登录”是否成立，再决定是否进一步重构认证体验 |
| 本轮不同时推进大范围 DOM 重排 | 先把真实交互闭环做通，再处理 `UX1` 的布局收纳，风险更低且更容易验证 |

## Issues Encountered
| Issue | Resolution |
|-------|------------|
| skill 安装的下载模式依赖 Python HTTPS 证书链，本机校验失败 | 改用 git sparse checkout 安装成功 |
| planning-with-files 的 `session-catchup.py` 在 Codex 中不会解析原生 session | 本轮按手动文件化上下文管理执行，不依赖自动会话恢复 |

## Resources
- 项目概览: `README.md`
- 阶段复盘: `docs/STAGE_REVIEW.md`
- 文档索引: `docs/README.md`
- 当前执行计划: `docs/DEVELOPMENT_PLAN.md`
- 现有技能定义: `~/.codex/skills/planning-with-files/SKILL.md`
- 前端草稿文件: `web/ui-practice-focus-draft.html`
- 真实前端入口: `web/index.html`
- 前端交互实现: `web/app.js`
- 关键发送逻辑: `sendPracticeTurn()` / `loginSupabase()` in `web/app.js`
- 本轮改动文件: `web/index.html`, `web/app.js`

## Visual/Browser Findings
- 本轮尚未进行图片、PDF 或浏览器视觉检查。
