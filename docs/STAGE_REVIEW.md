# 阶段复盘（整合）

## 1. 复盘范围

- 时间范围: 2026-02-11 至 2026-02-23
- 覆盖阶段: 从 MVP 首版联调到 Cloudflare 迁移稳定化

## 2. 时间线摘要

### 2026-02-11

关键进展:

1. 核心 API 链路可运行（场景/会话/消息/改写/总结/复盘/进度）
2. 前后端完成 Vercel 部署并可在线联调
3. 修复核心稳定性问题（Pooler prepared statement、SQL 参数歧义、模型响应容错）

### 2026-02-12

关键进展:

1. 鉴权主链路收敛为 Supabase JWT（线上）
2. `auth.users -> public.users` 自动同步迁移落地（`0003`）
3. RLS 与 claim 兼容修复落地（`0004`, `0005`）
4. 补齐自动化资产（集成测试、RLS 脚本、JWT 冒烟、预检 workflow）

### 2026-02-13

关键进展:

1. 前端重构为引导式 3 步练习流（登录 -> 对练 -> 总结复盘）
2. 新增跨会话历史回看能力（`GET /sessions` + `GET /sessions/{id}/history`）
3. 生产环境部署完成（前端/后端）
4. 线上完整预检通过（含 RLS 与 JWT API smoke）

### 2026-02-15

关键进展:

1. OFNR 评测集扩展到 `v0.2`（30 样本）
2. 新增在线模型回归模式（`--mode online|both`）
3. 行动卡导出扩展（PDF/PNG/分享模板）
4. PWA 第一阶段落地（安装入口、更新提示、离线提示）
5. 历史会话离线快照能力落地

### 2026-02-22

关键进展:

1. 新手引导 UX 落地
2. 安卓 Edge 安装兼容优化
3. 修复“取消安装后入口消失”
4. 图标体系升级（`any + maskable + favicon`）
5. Service Worker 更新策略增强
6. Cloudflare 迁移基础改造启动（前端发布脚本、CORS 扩展）

### 2026-02-23（本次重点）

关键进展:

1. Cloudflare 迁移问题定位完成，形成完整故障链路
2. 新增 Pages Functions API 代理（`/api/*`）
3. 新增 `/health-backend` 代理健康检查入口
4. 前端生产环境强制同域 API（不再依赖旧本地 API 配置）
5. Service Worker 策略收敛（不拦截导航/API，不缓存 `app.js`）
6. SW 版本滚动到 `v10`，解决旧缓存持续命中问题
7. Cloudflare 双项目发布成功并通过全链路烟测

### 2026-02-23（追加：体验方向对齐）

关键结论:

1. 当前页面功能完整，但首屏信息密度过高，影响新用户首轮转化
2. 登录、自检、引导、复盘等次级模块应默认折叠，避免分散注意力
3. 下一轮优化以“练习优先”为核心: 进入页面后先看到可输入、可发送区域
4. 链路策略更新为“先输入后登录，登录后自动续发”

### 2026-06-28（追加：Agora 语音对练集成）

关键进展:

1. 形成三方共识: 保留 Vanilla PWA，不迁移 Next/React
2. 语音后端先并入现有 Vercel FastAPI，Cloudflare 继续做同域代理
3. 去除 quickstart 的内存 `_sessions` 依赖，改为 Supabase 持久化 voice session 状态
4. 数据模型扩展现有 `sessions/messages`，不新增孤立 `voice_sessions` 表
5. 新增 `/api/v1/voice/*`、OpenAPI 契约、PWA 语音模式入口与 smoke 检查

验证结果:

1. `pytest backend/tests -q` 通过（41 passed, 2 skipped）
2. `bash scripts/pwa_smoke_check.sh` 通过
3. `SKIP_RLS_ISOLATION=1 SKIP_REMOTE_API_SMOKE=1 SKIP_OFNR_EVAL=1 bash scripts/release_preflight.sh` 通过
4. 浏览器检查通过: 文字/语音模式切换、未登录禁用语音开始、本地 mock 下语音开始按钮可用

## 3. Cloudflare 迁移故障复盘（详细）

### 3.1 用户侧核心现象

1. 页面可打开，但刷新后偶发无法访问
2. 登录成功后约 1 秒提示“当前离线或网络不可用”
3. 页面可访问但业务 API 不可用
4. 已发布新版本但手机端“看起来没有更新”

### 3.2 根因拆解（前因后果）

#### 根因 A: 平台规则差异

1. 迁移前前端在 Vercel，依赖 `vercel.json` rewrite
2. 迁移到 Cloudflare 后，这些 rewrite 不会自动生效
3. 结果: 页面可访问，但 `/api/*` 没有按预期转发到后端

#### 根因 B: 客户端历史配置与新拓扑冲突

1. 浏览器本地保留旧 `api_base_url`
2. 登录后前端会立即请求历史会话接口
3. 该请求可能命中不可达旧地址，触发 `fetch` 异常
4. 前端错误分类将其展示为“离线”

#### 根因 C: Service Worker 缓存策略过重

1. 旧策略缓存了 `app.js`
2. 新代码发布后客户端仍运行旧脚本
3. 旧逻辑继续触发旧 API/旧行为，造成“修了但用户端无变化”

#### 根因 D: Service Worker 拦截面过大

1. 早期 SW 参与导航/API 请求路径
2. 在部分移动浏览器中，缓存或网络异常会被放大成页面/接口失败

### 3.3 修复矩阵

1. 现象: 页面可开但 API 失败
   - 修复: 增加 `functions/api/[[path]].js` 同域反向代理
2. 现象: 登录后秒变“离线”
   - 修复: 生产强制同域 API；旧配置不再影响线上
3. 现象: 页面刷新后不稳定
   - 修复: SW 不拦截导航
4. 现象: 已发布但逻辑不更新
   - 修复: SW 版本升级 + 停止缓存 `app.js`
5. 现象: 无法快速判断后端是否连通
   - 修复: 增加 `/health-backend` 可视化健康检查

### 3.4 本次经验沉淀

1. “静态页可访问”不等于“应用可用”
2. 迁移必须按顺序验收:
   - 静态 -> 代理健康 -> API 预检 -> 业务全链路
3. 对 PWA 项目，迁移时必须先处理 SW 策略与版本
4. 同域 API 代理比跨域直连更稳，尤其在移动网络环境

## 4. 本阶段关键决策

1. 线上仅开放 Supabase 鉴权入口，隐藏 mock 入口
2. Cloudflare A 方案落地后，前端生产 API 固定同域 `/api/*`
3. 保留 Vercel 后端作为稳定服务与回滚锚点
4. Service Worker 长期策略:
   - 不缓存主业务脚本
   - 仅缓存低风险静态资源
5. B 方案（Cloudflare + Render）暂不实施，仅作为备选

## 5. 验证结果

本地验证:

1. `pytest backend/tests -q` 通过（25 passed, 2 skipped）
2. `bash scripts/pwa_smoke_check.sh` 通过
3. `python scripts/run_ofnr_eval.py --mode offline` 通过
4. `bash scripts/rls_isolation_check.sh` 通过

线上验证:

1. Cloudflare Pages 发布完成（stable/main 双项目）
2. `/health-backend` 返回后端 JSON
3. `OPTIONS /api/v1/scenes` 预检通过
4. `scripts/supabase_jwt_api_smoke_test.sh <front_domain>` 全 7 步通过

## 6. 当前状态结论

项目已进入“Cloudflare 前端可稳定访问 + 功能全链路可用 + 可回归验证”的状态。

## 7. 下一阶段重点

1. 完成练习优先 IA 重排（首屏只保留核心练习区）
2. 完成“先输入后登录”链路，减少首轮阻断
3. 次级模块统一折叠/抽屉化（登录、自检、引导、历史、复盘）
4. 在不影响稳定性的前提下继续优化新手体验与转化

### 2026-07-12（追加：Agora 语音上线 + 品牌域名闭环）

关键进展:

1. Agora ConvoAI v2 真实 start/stop 全链路打通（agent_id=A46AR98KF98TV33CC58FR34DV87AV26E）
2. 上一 session 遗留的 Supabase pooler 连接与 Agora 区域 TLS 两个 external blocker 全部解除
3. 品牌域名 `api.leoalgo.site` 上线（Volcengine DNS CNAME + Vercel SSL 签发生效）
4. 前端同源 `/api/*` 代理切换到品牌域名，脱离直连 vercel.app
5. 修复 datetime 编码 bug 并追加回归断言，新增至 45 passed
6. Service Worker 滚动到 v11，清理旧缓存
7. 全链路真实用户路径验收通过：`前端 pages.dev → 品牌域名 → 后端 → Supabase(pooler+RLS) → Agora ConvoAI`
8. 上线后清理测试数据（scenes=0, users=0）

验证方法（沉淀最佳实践）:

1. 不再接受"health/契约通过就上线"的弱验收
2. 上线验收统一采用"真实 Supabase JWT + 从前端品牌域名发起"的真实用户路径
3. 覆盖 DNS/SSL/前端代理/后端服务四个层次同时成立

上线基线:

1. 代码: main（commit e6b7ade），含 datetime 回归测试
2. 后端服务域名: `https://api.leoalgo.site`
3. 前端主域名: `https://nonviolent-communicator.pages.dev`
4. DB: Supabase `nvc-mentor`，pooler IPv4，RLS 隔离生效
5. 语音: Agora ConvoAI v2，DB 持久化正确
6. 回归保护: 45 tests passed

结论: M5 收官，无遗留功能阻塞，语音链路上线就绪。

### 2026-07-12（追加：Phase A-4 UX 收官）

关键进展:

1. **UX4 失败态可恢复**已落地：`quickCheckPanel` 由常驻面板改为 `<details>` 折叠，`showError` 在失败时自动展开自检入口
2. **UX3 视觉层级强化**已落地：主 CTA 按钮放大、主输入区高对比；次级面板通过 `.panel--secondary` 灰阶降权
3. 采取"最小侵入"策略：不重排 DOM，只通过 CSS + `<details>` 折叠实现"练习优先"目标；如需更彻底的 IA 改造，可后续对齐 `web/ui-practice-focus-draft.html` 草稿

下一阶段重点建议:

1. 语音体验产品化打磨（转录 UI 流式渲染、掉线恢复、麦克风权限引导）
2. Agora 用量/成本可观测（每日会话数、总时长、异常终止率）
3. 语音复盘视图与文字复盘的统一/分化决策
