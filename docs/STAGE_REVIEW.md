# 阶段复盘（整合）

## 1. 复盘范围

- 时间范围: 2026-02-11 至 2026-02-22
- 覆盖阶段: 从 MVP 首版联调到安全基线、回归闭环、M3 PWA 上线与安装体验优化

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
2. 新增在线模型回归模式（`--mode online|both`，支持并发与超时控制）
3. 预检脚本支持在线回归开关（`RUN_ONLINE_OFNR_EVAL=1`）
4. 行动卡导出扩展：PDF（打印导出）、PNG 图片、分享模板（复制/导出）
5. GitHub Actions 预检工作流新增在线回归灰度开关（`run_online_ofnr_eval`）
6. 代码已推送主干（`62032f8`, `ee27b6c`）并完成 Vercel Preview 部署
7. 阶段策略调整为 PWA-first（暂停微信小程序与原生 App 开发）
8. PWA 第一阶段完成（Manifest + SW + 离线提示 + 安装/更新入口）
9. 历史会话离线快照能力落地（列表与单会话回看）
10. 预检集成 PWA 冒烟脚本（`scripts/pwa_smoke_check.sh`）
11. PWA 离线快照策略增强（会话上限/TTL/启动清理/手动清理入口）
12. 发布与回滚流程脚本化（`scripts/vercel_release.sh`）
13. 代码已推送主干（`ad8c6ef`, `073f554`）
14. 最新前后端 Vercel Preview 已同步部署

### 2026-02-22

关键进展:

1. 新手引导 UX 落地（首轮任务条、下一步导航、常用开场句快捷填充）
2. 安卓 Edge 安装兼容优化（避免误导提示，改为菜单安装引导）
3. 修复“取消安装后入口消失”问题（安装入口在未安装状态下持续可见）
4. PWA 图标体系升级（`any + maskable + favicon`），桌面图标可识别
5. 安装提示升级为可关闭弹层（分步骤文案，手机端可见性增强）
6. Service Worker 版本升级并强化更新检查（降低旧缓存导致的“无变化”概率）
7. 多次生产发布同步完成，前端生产域名已切换到最新构建

## 3. 关键问题与根因

1. 前端 `Failed to fetch`
   - 根因: 跨域配置与历史本地配置混用，导致请求目标不稳定。
2. 消息接口 500
   - 根因: DB 连接策略与 SQL 参数处理在特定链路下不稳定。
3. Supabase 注册 429
   - 根因: Auth 邮件发送频控触发。
4. 云端预检早期失败（Event loop is closed）
   - 根因: `APP_ENV=test` 下 asyncpg 连接在 CI 中出现事件循环污染。
   - 处理: `test` 环境改用 `NullPool`，预检恢复通过。
5. 生产页面“已更新但手机无变化”
   - 根因: Service Worker 缓存版本未滚动，客户端持续命中旧静态资源。
   - 处理: 提升 SW 版本、启动时主动 `registration.update()`、引导用户清理旧站点缓存。
6. 安装入口“一次取消后找不到”
   - 根因: 安装按钮显隐依赖 `beforeinstallprompt`，取消后事件对象失效导致入口被隐藏。
   - 处理: 改为“未安装状态下始终可见安装入口”，无 prompt 时回退手动安装引导。
7. 桌面图标不明显
   - 根因: 早期图标资源为纯色块，缺少可识别视觉元素。
   - 处理: 替换为品牌图标并补齐 `maskable` 资源。

## 4. 本阶段关键决策

1. 线上仅开放 Supabase 鉴权入口，隐藏 mock 入口。
2. mock 仅用于本地联调，并加生产安全开关限制。
3. 发布前必须执行自动化预检，且至少覆盖:
   - 后端测试
   - RLS 隔离校验
   - Supabase JWT API 冒烟
4. 当前阶段不做外接可观测性（日志平台/告警通道），仅保留内建 `/ops/metrics`。
5. 在线模型回归采用灰度策略：
   - 默认关闭
   - 在有 `LLM_API_KEY` 且配额健康时手动开启
6. 当前阶段仅推进 PWA，不启动小程序/安卓/iOS 的开发。

## 5. 验证结果

本地验证:

1. `pytest backend/tests -q` 通过（25 passed, 2 skipped）
2. `node --check web/app.js` 通过
3. `SKIP_REMOTE_API_SMOKE=1 SKIP_RLS_ISOLATION=1 bash scripts/release_preflight.sh` 通过
4. OFNR 离线回归（`v0.2`）通过
5. 在线回归模式脚本路径验证通过（`--mode online`，空 key 回退场景）
6. `RUN_ONLINE_OFNR_EVAL` 联动脚本与 CI 开关逻辑验证通过
7. `bash scripts/pwa_smoke_check.sh` 通过
8. `bash -n scripts/vercel_release.sh` 通过
9. 预检已包含 PWA 冒烟检查并通过
10. `sw.js` 版本升级与资源缓存列表校验通过

云端验证:

1. GitHub Actions 完整预检通过:
   - `https://github.com/Leon-Algo/Nonviolent-Communicator/actions/runs/21979380349`
2. 该次预检已包含并通过:
   - RLS isolation check
   - Supabase JWT API smoke（含历史回看接口路径）
3. 最新 Vercel Production 部署:
   - 前端: `https://nvc-practice-web.vercel.app`
   - 后端: `https://api.leonalgo.site`

## 6. 当前状态结论

项目已进入“可上线演示、可回归验证、具备基础安全隔离”的阶段，且 M3 PWA 关键体验（安装、图标、更新、入口可恢复）已完成一轮收口。

## 7. 下一阶段重点

1. PWA 离线能力深化（离线可读内容扩展）
2. 发布流程自动化增强（预检 + 发布一体化，减少人工命令）
3. 在线 OFNR 回归灰度策略持续验证
4. 小程序/原生 App 仅保留技术预研，不进入实现阶段
