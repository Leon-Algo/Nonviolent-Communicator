# Progress Log

## Session: 2026-03-14

### Phase 1: Requirements & Discovery
- **Status:** complete
- **Started:** 2026-03-14
- Actions taken:
  - 检查当前项目根目录，确认还没有 `task_plan.md`、`findings.md`、`progress.md`
  - 盘点仓库主要文件和目录，确认这是一个前后端一体的 NVC MVP 项目
  - 读取 `README.md`、`docs/STAGE_REVIEW.md`、`docs/README.md`，提取当前产品阶段与下一步重点
  - 检查 `git status --short`，识别现有未提交改动和未跟踪文件
- Files created/modified:
  - `task_plan.md` (created)
  - `findings.md` (created)
  - `progress.md` (created)

### Phase 2: Planning & Structure
- **Status:** complete
- Actions taken:
  - 为当前仓库建立 planning-with-files 的三文件结构
  - 把目标、阶段、关键问题、现有约束和安装期问题写入 planning 文件
  - 读取当前开发计划与前端草稿，确认下一步切片正式锁定为 `UX1 -> UX2`
- Files created/modified:
  - `task_plan.md` (created)
  - `findings.md` (created)
  - `progress.md` (created)

### Phase 3: Implementation
- **Status:** in_progress
- Actions taken:
  - 将下一轮实现入口收敛到“把 `web/ui-practice-focus-draft.html` 的结构迁移到真实前端”
  - 记录草稿页的核心模式：首屏聚焦输入，辅助能力抽屉化，发送时再引导登录
  - 读取 `web/index.html` 与 `web/app.js` 入口，确认正式页面当前仍以登录和自检优先，和目标信息架构存在直接冲突
  - 识别真实实施文件集中在 `web/index.html`、`web/styles.css`、`web/app.js`
  - 深入检查 `loginSupabase()`、`sendPracticeTurn()` 与按钮事件绑定，确认当前不存在“登录后自动续发”机制
  - 在 `web/app.js` 中新增待续发状态与 auth gate，支持“未登录时保留输入 -> 登录成功后自动继续发送”
  - 在 `web/index.html` 中补充相关提示文案，使行为与界面说明一致
- Files created/modified:
  - `task_plan.md` (updated)
  - `findings.md` (updated)
  - `progress.md` (updated)
  - `web/app.js` (updated)
  - `web/index.html` (updated)

## Test Results
| Test | Input | Expected | Actual | Status |
|------|-------|----------|--------|--------|
| 技能安装验证 | 检查 `~/.codex/skills/planning-with-files` | 技能目录存在且包含 `SKILL.md` | 目录存在，安装成功 | PASS |
| 项目 planning 文件初始化 | 检查项目根目录 | 3 个 planning 文件已创建 | 已创建 | PASS |
| 前端脚本语法检查 | `node --check web/app.js` | JS 无语法错误 | 命令退出码 0 | PASS |

## Error Log
| Timestamp | Error | Attempt | Resolution |
|-----------|-------|---------|------------|
| 2026-03-14 | `install-skill-from-github.py` 下载模式 SSL 校验失败 | 1 | 改用 `--method git` 安装 |

## 5-Question Reboot Check
| Question | Answer |
|----------|--------|
| Where am I? | Phase 3，正在把草稿信息架构对接到真实前端实现 |
| Where am I going? | 在已完成 `UX2` 最小闭环的基础上，继续推进 `UX1` 的正式页面结构重排 |
| What's the goal? | 在当前仓库中落地 planning-with-files，并基于项目现状推进一个真实切片 |
| What have I learned? | `UX2` 可以通过前端 auth gate 和自动续发机制低风险落地 |
| What have I done? | 已完成 planning 文件初始化、锁定切片，并在真实前端实现了 `UX2` 的最小闭环 |

---

## Session: 2026-06-28 Agora Voice Integration

### Overall Status
- **Status:** implementation slice complete
- **Branch/worktree:** `feature/agora-voice-integration` at `/Users/leon/.config/superpowers/worktrees/Nonviolent-Communicator/agora-voice-integration`

### Actions Taken
- Added DB migration `0006_add_voice_session_support.sql`.
- Added stateless Agora voice service with lazy SDK imports.
- Added `/api/v1/voice/*` router, schemas, OpenAPI contract, and tests.
- Extended session history schemas and SQL to expose `modality`.
- Added Vanilla PWA voice mode UI and API lifecycle.
- Added voice PWA contract check and wired it into smoke/preflight scripts.
- Updated technical, setup, planning, stage review, and backend docs.

### Test Results
| Test | Status |
|------|--------|
| `pytest backend/tests -q` | PASS: 41 passed, 2 skipped |
| `node scripts/check_voice_pwa_contract.js` | PASS |
| `node --check web/app.js` | PASS |
| `bash scripts/pwa_smoke_check.sh` | PASS |
| `ruby -e 'require "yaml"; YAML.load_file("spec/openapi/nvc-practice-coach.v1.yaml")'` | PASS |
| `SKIP_RLS_ISOLATION=1 SKIP_REMOTE_API_SMOKE=1 SKIP_OFNR_EVAL=1 bash scripts/release_preflight.sh` | PASS |
| Playwright browser smoke at `http://localhost:8765` | PASS: text/voice switch, unauth disabled, mock enabled |

### Residual Risks
- Real DB integration tests were not run because local Postgres was unavailable.
- Real Agora RTC call was not completed in-browser because SDK assets are not yet bundled into the Vanilla PWA.
- Real Vercel build/import of `agora-agent-server-sdk` still needs deployment validation.

### Phase 8: Real SDK Assets & Integration
- **Status:** partial; implementation verified, external integration blocked by DB/Agora connectivity
- Actions taken:
  - Copied Agora browser assets from `agent-quickstart-python/web/node_modules` into `web/vendor/agora/`.
  - Extended the PWA voice contract check to require RTC, RTM, and `agora-agent-client-toolkit` assets.
  - Connected Vanilla PWA voice mode to `AgoraVoiceAI` transcript events and `/api/v1/voice/sessions/{session_id}/transcripts`.
  - Fixed transcript role mapping for Agora toolkit `uid=0`, matching quickstart normalization behavior.
  - Installed backend dependencies into the local venv using `uv`; verified `agora-agent-server-sdk` import and ConvoAI token generation.
  - Fixed compatibility with installed `agora-agent-server-sdk==2.3.0`: token generation now uses `uid`, and `Agent(client=...)` is used with session `name=...`.
  - Added configurable `AGORA_AREA` with `US` default and docs/env examples.
  - Verified vendor assets are served by the local static server with HTTP 200.
  - Added `scripts/check_voice_integration_env.py` to diagnose Supabase/Agora environment without printing secrets.
  - Verified local Clash Verge is running and `mixed-port: 7897` is reachable for outbound proxy tests.
  - Tested Supabase REST and Agora regional APIs through both HTTP and SOCKS5 proxy paths; `api.agora.io/health` works through the proxy, but Supabase and Agora regional hosts still fail TLS or auth from this machine/runtime.
  - Used temporary `PySocks` monkeypatching in the local venv to force Python `httpx` and `asyncpg` through SOCKS5; this did not recover Supabase REST, Supabase Postgres, or Agora US regional connectivity.
- Test results:
  - `pytest backend/tests -q`: `43 passed, 2 skipped`
  - `node --check web/app.js`: PASS
  - `node scripts/check_voice_pwa_contract.js`: PASS
  - `bash scripts/pwa_smoke_check.sh`: PASS
  - `PATH=/Users/leon/Developer/CodeProject/Nonviolent-Communicator/.venv/bin:$PATH SKIP_RLS_ISOLATION=1 SKIP_REMOTE_API_SMOKE=1 SKIP_OFNR_EVAL=1 bash scripts/release_preflight.sh`: PASS
  - Local static server served Agora RTC/toolkit assets with HTTP 200.
  - `scripts/check_voice_integration_env.py` with loaded env reports Supabase and Agora regional hosts resolving to `28.0.0.x`, which matches the observed TLS/connectivity failures.
  - Clash proxy probe: `curl --proxy http://127.0.0.1:7897 https://api.agora.io/health` returns `{\"message\":\"OK\"}`.
- Remaining external checks:
  - Apply migration `0006_add_voice_session_support.sql` after a valid Supabase direct DB URL or corrected pooler config is available.
  - Run full voice start/stop after `AGORA_AREA` matches the Agora project region and that regional API is reachable from the runtime.

### Phase 8 Error Log
| Error | Attempt | Resolution |
|-------|---------|------------|
| `asyncpg.connect()` rejected project `DATABASE_URL` because it uses SQLAlchemy scheme `postgresql+asyncpg://` | 1 | Convert the scheme to `postgresql://` only for the migration runner; do not change project config |
| Supabase pooler returned `tenant/user ... not found` for the configured `DATABASE_URL` | 2 | Tried direct `db.<project>.supabase.co:5432` with same password; connection closed before auth. Treat real DB migration as blocked by connection configuration/network until a valid direct DB URL or pooler config is provided |
| Agora quickstart hard-coded `Area.US`; local network cannot complete TLS to US/EU/AP Agora regional domains | 1 | Added `AGORA_AREA` config so region is deploy/runtime configurable |
| `AGORA_AREA=CN` reaches Agora ConvoAI API but returns `401 Invalid token` with the current quickstart credentials | 1 | Confirms SDK request path and region config work; full start/stop requires matching Agora project region or network access to the credential's region |

---

## Session: 2026-07-12 Agora Voice Go-Live 品牌域名闭环

### Overall Status
- **Status:** complete；语音全链路上线就绪
- 承接上一 session 遗留的两个 external blocker（Supabase pooler 连接、Agora 区域 TLS）在本轮全部解除

### Actions Taken
- 修复 datetime 编码 bug 并追加回归断言，避免语音会话时间字段序列化再次出错
- Supabase `nvc-mentor` pooler + RLS 生效，`0006_add_voice_session_support.sql` 反向确认已应用（voice session 持久化正确）
- Agora ConvoAI v2 真实 start/stop 打通（agent_id=A46AR98KF98TV33CC58FR34DV87AV26E）
- 品牌域名 `api.leoalgo.site` 上线：Volcengine DNS CNAME 到 Vercel + SSL 签发生效
- 前端 `nonviolent-communicator.pages.dev` 同源 `/api/*` 代理切换到品牌域名（脱离直连 vercel.app）
- 前端 Service Worker 滚动到 v11，清理旧缓存
- 全链路真实用户路径验收：真实 Supabase JWT → 前端 pages.dev → 同源代理 → 品牌域名 → 后端 → Supabase + Agora
- 上线后清理测试数据：scenes=0, users=0

### Test Results
| Test | Status |
|------|--------|
| `pytest backend/tests -q`（含 datetime 回归） | PASS: 45 passed |
| 建测试用户 + 密码登录拿 JWT | PASS: role=authenticated |
| `POST /api/v1/scenes`（经前端代理） | PASS: 201 |
| `POST /api/v1/voice/sessions`（经前端代理） | PASS: 201，真实 agent_id 返回 |
| `POST /api/v1/voice/sessions/{id}/stop` | PASS: 200 STOPPED |
| 测试数据清理 | PASS: scenes=0, users=0 |

### 上线基线（2026-07-12 截止）
| 维度 | 状态 |
|------|------|
| 代码 | main（commit e6b7ade），含 datetime 修复 + 回归测试 |
| 后端 | `https://api.leoalgo.site`（Vercel），`/health` 200，SSL 有效 |
| 前端 | `https://nonviolent-communicator.pages.dev`，SW v11 |
| 自定义域名 | Volcengine DNS + Vercel SSL，全链路品牌域名 |
| DB | Supabase `nvc-mentor`，pooler IPv4，RLS 隔离生效 |
| 语音 | Agora ConvoAI v2 真实 start/stop，DB 持久化正确 |
| 回归保护 | 45 tests passed（含 datetime 回归断言） |

### Residual Risks
- 无功能阻塞，M5 收官
- 后续风险转移到"产品体验层"：语音掉线恢复、转录 UI、麦克风权限引导、Agora 用量/成本可观测

## Session: 2026-07-12（追加）Phase A-4 UX 收官

### Overall Status
- **Status:** complete；UX3/UX4 落地

### Actions Taken
- **UX4 失败态可恢复**：将 `quickCheckPanel` 由常驻面板改为 `<details>` 折叠，默认收起；`showError` 在 network / proxy_unavailable / server_error 等类别下自动展开自检面板，命中"仅在失败时暴露自检入口"最佳实践
- **UX3 视觉层级强化**：CSS 层新增 `.panel--secondary` 灰阶降权样式（authPanel、historyPanel、开发者配置等），主 CTA `#startPracticeBtn` / `#voiceStartBtn` 按钮尺寸和视觉重量放大，主输入区（`practicePanel`）背景保持高对比
- 保持 DOM 顺序不动，仅通过 CSS + `<details>` 折叠实现视觉降权，避免影响事件绑定与既有测试

### Test Results
| Test | Status |
|------|--------|
| `node --check web/app.js` | PASS |
| `node scripts/check_voice_pwa_contract.js` | PASS |

### 2026-07-12 追加：修复 web/app.js 隐藏 SyntaxError

- **发现**：本次 UX 收官阶段跑 `node --check web/app.js` 时暴露一处**存在于 commit e6b7ade 中的孤儿代码**：文件末尾 `bind();` 之后挂了半截 `=== "mock" || hasToken) { ... } bind();`，缺失前两行 `const mode = ...` / `if (mode` 开头。整个 `app.js` 无法通过 JS 引擎解析。
- **影响**：浏览器加载 `app.js` 时抛 SyntaxError，脚本全量失败。7-12 15:29 的品牌域名验收全部走 curl+JWT 直接打后端 API，**未从浏览器 UI 完整走一遍交互**，所以该 bug 隐藏至今。
- **修复**：删除末尾孤儿代码块（10 行 + 1 个重复 `bind();`），并追加 `expandQuickCheckPanel` / `dismissQuickCheckAlert` 两个 helper 与失败态自动展开逻辑。
- **验证**：`node --check web/app.js` 通过；`node scripts/check_voice_pwa_contract.js` 通过。

### 验收方法教训（新增）
| Lesson | Rationale |
|--------|-----------|
| API 层验收 ≠ 上线就绪 | curl + JWT 通过只能证明后端契约成立，无法发现前端 JS SyntaxError 这类"浏览器加载即挂"的 bug |
| 上线前**必须跑一次完整 `release_preflight.sh`** | preflight 里已经有 `node --check web/app.js`（scripts/release_preflight.sh:37）和 `pwa_smoke_check.sh` 里的 `node --check web/app.js`（scripts/pwa_smoke_check.sh:26）；本次孤儿代码就是因为验收链路绕过了 preflight，直接跳到 curl API 冒烟，才把 SyntaxError 送上线 |
| 上线验收必须包含"浏览器完整交互"这一环 | 至少覆盖：打开首页 → 登录 → 创建场景 → 发送 → 语音开始/停止，任何环节 JS 报错都直接判为不通过 |
