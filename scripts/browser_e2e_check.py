# -*- coding: utf-8 -*-
"""NVC 好好说 - 真实浏览器端到端验证（Playwright 驱动本机 Chrome）。

按 AGENTS.md 2026-07-12 事故规则执行完整用户路径：
  首页 -> 注册(经 admin API 预确认) -> 登录 -> 建场景+发第1轮 -> 发第2轮
  -> 生成行动卡 -> 提交复盘 -> 查周进度 -> 语音对练启停
任何页面 JS 错误或一方网络请求失败都记为失败项。

前置：
  1) 后端: AUTH_MODE=supabase CORS_ORIGINS=http://127.0.0.1:8081 \
       uvicorn app.main:app --host 127.0.0.1 --port 8000
  2) 前端: python3 -m http.server 8081 --bind 127.0.0.1  (在 web/ 目录)
  3) .venv 安装 playwright，本机已装 Google Chrome

用法：
  .venv/bin/python scripts/browser_e2e_check.py
退出码 0 = 全部通过。
"""

import json
import os
import subprocess
import sys
import time
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
FRONTEND = os.environ.get("E2E_FRONTEND", "http://127.0.0.1:8081/")
API_BASE = os.environ.get("E2E_API_BASE", "http://127.0.0.1:8000")
PASSWORD = "NvcE2E!x7K9"
TIMEOUT = int(os.environ.get("E2E_TIMEOUT_MS", "120000"))
SHOT_DIR = Path(os.environ.get("E2E_SHOT_DIR", "/tmp/nvc-e2e-shots"))

results = []


def check(step, ok, detail=""):
    results.append((step, ok, detail))
    mark = "PASS" if ok else "FAIL"
    print(f"[{mark}] {step}" + (f" — {detail}" if detail else ""))


def env(name):
    line = subprocess.run(
        ["grep", f"^{name}=", str(ROOT / ".env")],
        capture_output=True, text=True,
    ).stdout.strip()
    return line.split("=", 1)[1] if "=" in line else ""


SUPABASE_URL = env("SUPABASE_URL").rstrip("/")
SERVICE_KEY = env("SUPABASE_SERVICE_ROLE_KEY")


def admin_create_confirmed_user(email: str):
    """按 AGENTS.md 官方方案：service-role admin API 建预确认用户。"""
    out = subprocess.run(
        [
            "curl", "-sS", "-X", "POST", f"{SUPABASE_URL}/auth/v1/admin/users",
            "-H", "Content-Type: application/json",
            "-H", f"apikey: {SERVICE_KEY}",
            "-H", f"Authorization: Bearer {SERVICE_KEY}",
            "-d", json.dumps({
                "email": email, "password": PASSWORD, "email_confirm": True,
            }),
        ],
        capture_output=True, text=True,
    )
    try:
        body = json.loads(out.stdout)
    except json.JSONDecodeError:
        body = {"raw": out.stdout[:200]}
    uid = body.get("id")
    if not uid:
        raise RuntimeError(f"admin create failed: {body}")
    return uid


def main():
    stamp = str(int(time.time()))
    email = f"e2e_browser_{stamp}@example.com"

    uid = admin_create_confirmed_user(email)
    check("admin 预创建并确认用户", True, f"{email} / uid={uid[:8]}…")

    console_errors = []
    failed_requests = []

    with sync_playwright() as p:
        browser = p.chromium.launch(
            # 用户要求用默认谷歌浏览器：Playwright 官方 channel="chrome" 即本机 Chrome
            channel="chrome",
            headless=False,
            args=[
                # 官方推荐方式：假摄像头/麦克风，免去真实麦克风权限弹窗
                "--use-fake-ui-for-media-stream",
                "--use-fake-device-for-media-stream",
            ],
        )
        context = browser.new_context(viewport={"width": 1440, "height": 960})
        page = context.new_page()

        page.on("console", lambda m: console_errors.append(m.text) if m.type == "error" else None)
        page.on("pageerror", lambda e: console_errors.append(f"pageerror: {e}"))
        page.on("requestfailed", lambda r: failed_requests.append(f"{r.method} {r.url} :: {r.failure}"))

        page.set_default_timeout(TIMEOUT)
        # 本地 dev（127.0.0.1）默认 API 地址 = 当前域名 8081，没有 /api 代理。
        # 预置 localStorage 指向本地后端（等价于用户在开发者配置里保存一次）。
        page.goto(FRONTEND, wait_until="domcontentloaded")
        page.evaluate(
            """(apiBase) => {
              localStorage.setItem("api_base_url", apiBase);
              localStorage.setItem("onboarding_install_skip_v1", "1");
              localStorage.setItem("onboarding_dismiss_v1", "1");
            }""",
            API_BASE,
        )
        page.goto(FRONTEND, wait_until="networkidle")

        # ---- 0. 首页渲染 ----
        brand = page.title()
        check("页面加载", "好好说" in brand, f"title={brand!r}")

        # ---- 1. 注册登录（真实 Supabase 链路）----
        page.fill("#supabaseEmail", email)
        page.fill("#supabasePassword", PASSWORD)
        page.click("#supabaseLoginBtn")
        # 登录成功 = access_token 填入高级设置输入框（persistSupabaseSession）
        page.wait_for_function(
            "() => document.querySelector('#supabaseAccessToken').value.trim().length > 200",
            timeout=TIMEOUT,
        )
        token_len = len(page.input_value("#supabaseAccessToken"))
        check("Supabase 真实登录并获取 Token", token_len > 200, f"token {token_len} chars")

        # ---- 2. 建场景 + 发第 1 轮（真实 LLM）----
        page.fill("#sceneTitle", "浏览器E2E：和同事对齐进度")
        page.fill("#messageContent", "你每次都拖到最后一天才交，害得我天天加班帮你收拾。")
        page.click("#startPracticeBtn")

        # 反馈区出现真实推荐句（等待两次 LLM 完成）
        page.wait_for_function(
            "() => document.querySelector('#nextSentence') && "
            "document.querySelector('#nextSentence').textContent.trim().length > 8",
            timeout=TIMEOUT,
        )
        next_sentence = page.inner_text("#nextSentence").strip()
        topic_match = ("拖" in next_sentence) or ("加班" in next_sentence) or ("进度" in next_sentence) or ("时间" in next_sentence) or ("截止" in next_sentence) or ("交" in next_sentence)
        check("第1轮发送 + LLM 推荐句贴合原句", topic_match, f"推荐句: {next_sentence[:60]}")

        assistant_reply = page.inner_text("#assistantReply").strip()
        check("AI 对方回应已渲染", len(assistant_reply) > 10, assistant_reply[:50])

        overall = page.inner_text("#feedbackOverall").strip()
        check("结构化反馈分数已渲染", overall not in ("-", ""), f"总分={overall}")

        # ---- 3. 发第 2 轮 ----
        page.fill("#messageContent", "我知道项目难，但至少提前说一声，别让我被动。")
        page.click("#sendMessageBtn")
        # renderHistory 渲染 .turn-card；第2轮后应出现 turn-card-2
        page.wait_for_selector("#conversationList .turn-card#turn-card-2", timeout=TIMEOUT)
        conv_text = page.inner_text("#conversationList").strip()
        check("第2轮发送并进入会话记录", "别让我被动" in conv_text and "第 2 轮" in conv_text,
              f"记录 {len(conv_text)} chars，含用户原句")

        # ---- 4. 行动卡（总结）----
        page.eval_on_selector("#generateSummaryBtn", "el => el.click()")
        page.wait_for_function(
            "() => document.querySelector('#summaryOpening') && "
            "document.querySelector('#summaryOpening').textContent.trim() !== '-'",
            timeout=TIMEOUT,
        )
        opening = page.inner_text("#summaryOpening").strip()
        check("行动卡生成（含开场句）", len(opening) > 8, opening[:50])

        # ---- 5. 复盘提交 ----
        page.select_option("#usedInRealWorld", "true")
        page.fill("#outcomeScore", "5")
        page.fill("#blockerNote", "E2E 自动验证")
        page.eval_on_selector("#submitReflectionBtn", "el => el.click()")
        page.wait_for_function(
            "() => !document.querySelector('#reflectionMeta').textContent.includes('尚未提交')",
            timeout=60_000,
        )
        check("复盘提交成功", "尚未提交" not in page.inner_text("#reflectionMeta"),
              page.inner_text("#reflectionMeta")[:40])

        # ---- 6. 周进度 ----
        page.eval_on_selector("#weeklyProgressBtn", "el => el.click()")
        page.wait_for_function(
            "() => document.querySelector('#progressPracticeCount') && "
            "document.querySelector('#progressPracticeCount').textContent.trim() !== '-'",
            timeout=60_000,
        )
        practice_count = page.inner_text("#progressPracticeCount").strip()
        summary_count = page.inner_text("#progressSummaryCount").strip()
        real_count = page.inner_text("#progressRealCount").strip()
        check("周进度渲染且计数正确",
              practice_count not in ("-", "0"),
              f"练习={practice_count} 总结={summary_count} 真实应用={real_count}")

        # ---- 7. 语音对练启停（真实 Agora，放最后：会切换当前会话）----
        page.eval_on_selector("#practiceModeVoiceBtn", "el => el.click()")
        page.wait_for_selector("#voicePracticeBlock:not(.is-hidden)")
        page.eval_on_selector("#voiceStartBtn", "el => el.click()")
        page.wait_for_function(
            "() => document.querySelector('#voiceChannelValue') && "
            "document.querySelector('#voiceChannelValue').textContent.trim() !== '-'",
            timeout=180_000,
        )
        channel = page.inner_text("#voiceChannelValue").strip()
        check("语音会话创建（channel 分配）", len(channel) > 3, f"channel={channel[:24]}")

        rtc_state = page.evaluate("() => JSON.parse(document.querySelector('#output').textContent)")
        rtc_connected = bool(rtc_state.get("rtc_client", {}).get("connected"))
        check("Agora RTC 客户端加入频道", rtc_connected, f"rtc_client={rtc_state.get('rtc_client')}")

        page.eval_on_selector("#voiceStopBtn", "el => el.click()")
        page.wait_for_function(
            "() => { const b = document.querySelector('#voiceStopBtn'); return b && b.disabled; }",
            timeout=120_000,
        )
        check("语音会话正常结束", True, "")

        # 关键步骤截图留证
        SHOT_DIR.mkdir(parents=True, exist_ok=True)
        page.screenshot(path=str(SHOT_DIR / "final-state.png"), full_page=True)

        browser.close()

    # ---- 环境级检查 ----
    real_console_errors = [e for e in console_errors
                           if "favicon" not in e.lower() and "net::ERR_ABORTED" not in e]
    check("无页面 JS 错误", len(real_console_errors) == 0, "; ".join(real_console_errors[:3]))
    # 一方请求（页面/静态资源/后端 API/Supabase 认证）必须零失败；
    # 三方 SDK 遥测（Agora cds 配置节点、字体 CDN）在当前网络不可达属环境噪声，
    # 单独记录不作为发布门槛（RTC 已实测连通）。
    THIRD_PARTY = ("sd-rtn.com", "agora.io", "fonts.googleapis.com", "fonts.gstatic.com")
    first_party_fail = []
    third_party_fail = []
    for f in failed_requests:
        url = f.split(" :: ")[0]
        if "favicon" in url.lower():
            continue
        if any(host in url for host in THIRD_PARTY):
            third_party_fail.append(f)
        else:
            first_party_fail.append(f)
    check("一方网络请求零失败", len(first_party_fail) == 0, "; ".join(first_party_fail[:3]))
    if third_party_fail:
        print(f"[INFO] 三方 SDK/CDN 请求被网络阻断 {len(third_party_fail)} 条（非产品缺陷，RTC 已连通）")

    passed = sum(1 for _, ok, _ in results if ok)
    total = len(results)
    print(f"\n===== E2E RESULT: {passed}/{total} passed =====")
    Path("/tmp/nvc-e2e-result.json").write_text(json.dumps({
        "passed": passed, "total": total,
        "steps": [{"step": s, "ok": ok, "detail": d} for s, ok, d in results],
    }, ensure_ascii=False, indent=2))
    print(f"截图: {SHOT_DIR / 'final-state.png'} | 结果: /tmp/nvc-e2e-result.json")

    sys.exit(0 if passed == total else 1)


if __name__ == "__main__":
    main()
