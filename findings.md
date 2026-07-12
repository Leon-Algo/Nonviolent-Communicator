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

---

## 2026-06-28 Agora Voice Integration Findings

### Architecture Findings
- Quickstart server README confirms the default managed vendor chain only requires `AGORA_APP_ID` and `AGORA_APP_CERTIFICATE`; third-party STT/LLM/TTS keys are not required for the default Deepgram/OpenAI/MiniMax managed setup.
- `agora-agent-server-sdk` can be lazy-imported from the voice service so the main FastAPI app still imports without Agora credentials or SDK runtime use.
- Voice start/stop is modeled as stateless control-plane HTTP work; browser RTC/RTM remains the media plane.
- Persisting `voice_agent_id`, `voice_channel_name`, user/agent UIDs, status, and expiry on `sessions` is sufficient for cross-instance stop/recovery.
- Extending `sessions/messages` keeps history and review queries unified; separate `voice_sessions` tables are unnecessary for this phase.

### Frontend Findings
- The current PWA can host a voice mode without introducing React/Next.
- Service Worker did not need a version bump because no new cached shell asset was added and `app.js` is intentionally not cached.
- Browser smoke found and fixed one real issue: `renderVoiceState()` initially re-enabled the voice start button even when unauthenticated.
- Local review found and fixed one backend boundary issue: voice stop/transcript endpoints now reject non-voice sessions instead of mutating text sessions.
- Local review found and fixed one frontend cleanup risk: if RTC initialization throws after backend voice session creation, the PWA now best-effort stops the backend agent and clears local voice state.

### Verification Findings
- Local backend unit tests pass: `40 passed, 2 skipped`.
- DB integration tests remain skipped by default; local Postgres was not available for `RUN_DB_TESTS=1`.
- In-app Browser plugin could not start due `sandboxCwd` metadata error, so Playwright CLI was used for local browser verification.

### Remaining Decisions
- No product decision is blocked. Best-practice next step is to add/bundle Agora RTC/RTM SDK assets for the Vanilla PWA and run real credential-based voice start/stop on a preview deployment.

### 2026-06-29 Integration Findings
- Quickstart frontend uses browser-safe Agora assets already suitable for the Vanilla PWA: `agora-rtc-sdk-ng`, `agora-rtm`, and the framework-agnostic core of `agora-agent-client-toolkit`.
- `agora-agent-client-toolkit` emits `TRANSCRIPT_UPDATED`; it does not own RTC join/publish, so the PWA still needs to create/join/publish the Agora RTC client directly.
- Quickstart normalizes transcript items with `uid === "0"` to the local user before rendering. The PWA now applies the same rule so local speech is persisted as `USER`, not `ASSISTANT`.
- Root `.env` has Supabase/database settings; quickstart `server/.env.local` has `AGORA_APP_ID` and `AGORA_APP_CERTIFICATE`. Local integration needs both files loaded without printing secret values.
- The main project `.env` also has `DATABASE_URL_5432`, but it still targets the Supabase pooler host instead of a true direct Postgres host.
- Local Clash Verge is available on `127.0.0.1:7897`; it can proxy `https://api.agora.io/health`, but it does not restore TLS connectivity to Supabase or Agora regional API hosts from this runtime.
- Forcing Python through SOCKS5 with `PySocks` does not change the outcome: Supabase REST still fails TLS, `asyncpg` against the pooler still reports tenant/sni issues, and direct `db.<project>.supabase.co` still drops the connection.

---

## 2026-07-12 Go-Live Findings（Agora 语音品牌域名闭环）

### Integration Findings
- 上一 session 遗留的两个 external blocker 都是"连接层"问题，不是产品/代码问题；一旦网络路径打通即可无缝落地
- Supabase pooler + RLS 的正确配置组合是 `DATABASE_URL` 走 pooler IPv4；直连 `db.<project>.supabase.co` 因 SNI/tenant 问题反而不稳
- Agora ConvoAI 区域配置只要与 Agora 项目区域一致就能跑通；`AGORA_AREA` 外置化在这次证明是必需的抽象
- 品牌域名比 vercel.app 直连是**更强的验收路径**，能同时覆盖 DNS/SSL/前端代理/后端服务四个层次；未来所有验收都应以"真实用户路径"为准

### Verification Findings
- 45 passed（新增 datetime 回归断言），比上轮 43 多 2，回归保护更完整
- 全链路验收方法沉淀：真实 Supabase JWT + 从前端域名发起 → 走品牌域名同源代理 → 后端 → DB + 语音；不再接受"health/契约通过就上线"的弱验收

### 下一阶段 Findings（产品化打磨方向）
- M5 收官后，语音相关的技术风险已消解，剩余投资回报最高的方向是"用户可感知的语音体验"：
  - 实时转录 UI 的呈现（当前只落库，未做流式渲染优化）
  - 语音会话中断、超时、掉线的自动恢复策略
  - 语音会话的复盘视图与文字复盘链路的统一/分化决策
  - 移动端麦克风权限引导（首次开麦的权限拒绝失败率是主要流失点）
- Agora 是按分钟计费，需要建立用量/成本可观测：至少能看到当日会话数、总时长、异常终止率
- Phase A-4 UX3/UX4 采取"最小侵入"策略：不重排 DOM，只通过 CSS 视觉降权 + `<details>` 折叠实现"练习优先"目标；如果后续要更彻底的信息架构改造，再走完整的 UX 迭代（对齐 `web/ui-practice-focus-draft.html` 草稿）

### Technical Decisions（本轮追加）
| Decision | Rationale |
|----------|-----------|
| UX4 不引入新的自检入口，只把现有 `quickCheckPanel` 折叠 | 现有 `showError` 已完整分类到 network/proxy/auth/server/offline，UX 层只需减少常驻噪音 |
| UX3 不做 DOM 重排，只做 CSS 层视觉降权 | DOM 重排风险高、需回归大量交互测试；视觉降权可以先验证信息架构是否奏效 |
| Planning 文件与代码进度对齐 | 之前 planning 停留在 7-5 的"blocked"状态，会误导后续 session；对齐后再讨论下一步 |
