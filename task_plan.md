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

---

# Task Plan: Agora Voice Agent 集成

## Goal
把 `agent-quickstart-python` 的 Agora 语音 Agent 能力按三方共识集成回主项目: 保留 Vanilla PWA，控制面并入现有 Vercel FastAPI，状态持久化到 Supabase，并复用现有历史/复盘链路。

## Current Phase
Phase 8 in progress

## Phases

### Phase 1: Database Schema
- [x] 扩展 `sessions/messages` 支持语音会话状态、RTC UID、转录来源与幂等 turn id
- [x] 将 `0006_add_voice_session_support.sql` 纳入 DB 集成测试迁移清单
- **Status:** complete

### Phase 2: Stateless Agora Service
- [x] 新增 `VoiceAgentService`
- [x] Agora SDK lazy import，避免未配置 SDK 时影响主应用启动
- [x] 配置集中到 `backend/app/core/config.py`
- **Status:** complete

### Phase 3: Voice API
- [x] 新增 `/api/v1/voice/sessions`
- [x] 新增 `/api/v1/voice/sessions/{session_id}/stop`
- [x] 新增 `/api/v1/voice/sessions/{session_id}/transcripts`
- [x] 同步 OpenAPI
- **Status:** complete

### Phase 4: History Compatibility
- [x] 历史列表与详情返回 `modality`
- [x] 语音会话复用现有 sessions/messages/feedback_items 链路
- **Status:** complete

### Phase 5: PWA Voice Mode
- [x] 新增文字/语音模式切换
- [x] 新增语音 start/stop API 生命周期
- [x] 新增浏览器 RTC SDK 接缝，未加载 SDK 时给出明确状态
- [x] 浏览器检查未登录禁用、Mock 模式启用
- **Status:** complete

### Phase 6: Smoke / Release Checks
- [x] 新增 `scripts/check_voice_pwa_contract.js`
- [x] `pwa_smoke_check.sh` 纳入 voice contract 和 `web/app.js` 语法检查
- [x] `release_preflight.sh` 纳入 voice contract 脚本语法检查
- **Status:** complete

### Phase 7: Documentation
- [x] 更新技术方案、测试指南、开发计划、阶段复盘、后端 README
- **Status:** complete

### Phase 8: Real SDK Assets & Integration
- [x] 从 `agent-quickstart-python` 复用 Agora RTC/RTM/toolkit 浏览器资产
- [x] Vanilla PWA 接入 `AgoraVoiceAI` 转录事件与 `/transcripts` 落库
- [x] 修正 Agora toolkit `uid=0` 的本地用户转录角色归一化
- [x] 增加 `AGORA_AREA` 配置，避免硬编码 quickstart 的 `Area.US`
- [x] 增加脱敏语音联调环境诊断脚本，固化 Supabase/Agora DNS 检查
- [x] 验证本机 Clash 代理路径；确认代理不足以恢复 Supabase/Agora 区域联调
- [ ] 对 Supabase 执行 `0006_add_voice_session_support.sql`（当前连接串/网络阻塞）
- [ ] 使用 quickstart Agora 凭证跑完整本地 voice start/stop 控制面联调（当前 US 区域 TLS 阻塞，CN 区域返回 token/区域不匹配）
- [x] 浏览器验证 SDK 资产静态加载、语音入口错误处理和可用路径
- **Status:** partial; blocked only on external DB/Agora region connectivity

## Decisions Made
| Decision | Rationale |
|----------|-----------|
| 先并入 Vercel FastAPI | Agora start/stop 是短 HTTP 控制面调用；状态外部化后不需要长驻 Python 服务 |
| Cloudflare 不跑 Python voice backend | Workers Python/FastAPI 兼容性和 SDK 调试风险高，现阶段只做代理 |
| 扩展现有表而非新建 voice 表 | 历史、复盘、统计链路天然统一 |
| 前端不引入 Next/React | 主项目 PWA 已稳定，Agora RTC 可通过浏览器 SDK 接入 |
| RTC SDK 接缝先落地，SDK 资产后续接入 | 避免本轮引入构建体系，同时让控制面和 UI 可先验收 |
| 浏览器 Agora 资产直接复用 quickstart 已验证版本 | 避免闭门造车，同时不引入 Next/React 构建体系 |
| `AGORA_AREA` 外置配置，默认仍为 `US` | quickstart 原本硬编码 US；本地网络仅 CN 区域可达，但生产应按 Agora 项目区域配置 |

## Verification
| Check | Result |
|-------|--------|
| `pytest backend/tests -q` | 41 passed, 2 skipped |
| `node scripts/check_voice_pwa_contract.js` | PASS |
| `bash scripts/pwa_smoke_check.sh` | PASS |
| OpenAPI YAML parse | PASS |
| local preflight with remote checks skipped | PASS |
| Playwright browser smoke | PASS |
| `pytest backend/tests -q` after SDK compatibility fixes | 43 passed, 2 skipped |
| `PATH=.venv/bin:$PATH ... release_preflight.sh` | PASS |
