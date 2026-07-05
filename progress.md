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
