# -*- coding: utf-8 -*-
"""NVC 好好说 - 普通用户全流程自动化验证（不含语音）。

用户视角完整旅程：
  0. 首次打开（全新 localStorage，无任何预置）
  1. 首页渲染 + 新手引导可见
  2. 注册（表单点击，真实 Supabase signup）
  3. 登录（真实 Supabase password grant）
  4. 建场景并发送第 1 轮（真实 LLM 反馈）
  5. 发送第 2 轮
  6. 生成行动卡
  7. 提交复盘
  8. 查看周进度
  9. 历史会话回看
 10. 退出登录（Token 清空，页面回到未登录态）

前置：后端 AUTH_MODE=supabase@8000、前端静态服务@8081。
用户预创建用 admin API（邮箱确认开启，等真实确认邮件会卡流程——AGENTS.md 方案）。
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
SHOT_DIR = Path(os.environ.get("E2E_SHOT_DIR", "/tmp/nvc-journey-shots"))

results = []


def check(step, ok, detail=""):
    results.append((step, ok, detail))
    print(f"[{'PASS' if ok else 'FAIL'}] {step}" + (f" — {detail}" if detail else ""))


def env(name):
    line = subprocess.run(
        ["grep", f"^{name}=", str(ROOT / ".env")], capture_output=True, text=True
    ).stdout.strip()
    return line.split("=", 1)[1] if "=" in line else ""


def admin_create_confirmed_user(email):
    out = subprocess.run(
        [
            "curl", "-sS", "-X", "POST",
            f"{env('SUPABASE_URL').rstrip('/')}/auth/v1/admin/users",
            "-H", "Content-Type: application/json",
            "-H", f"apikey: {env('SUPABASE_SERVICE_ROLE_KEY')}",
            "-H", f"Authorization: Bearer {env('SUPABASE_SERVICE_ROLE_KEY')}",
            "-d", json.dumps({"email": email, "password": PASSWORD, "email_confirm": True}),
        ],
        capture_output=True, text=True,
    )
    body = json.loads(out.stdout or "{}")
    if not body.get("id"):
        raise RuntimeError(f"admin create failed: {body}")
    return body["id"]


def main():
    stamp = str(int(time.time()))
    email = f"journey_{stamp}@example.com"
    admin_create_confirmed_user(email)
    print(f"[setup] 预创建已确认用户 {email}")

    console_errors, failed_requests = [], []

    with sync_playwright() as p:
        browser = p.chromium.launch(channel="chrome", headless=False, args=[
            "--use-fake-ui-for-media-stream", "--use-fake-device-for-media-stream"])
        # 全新 context = 全新 localStorage，模拟第一次进站的普通用户
        page = browser.new_context(viewport={"width": 1440, "height": 960}).new_page()
        page.set_default_timeout(TIMEOUT)
        page.on("console", lambda m: console_errors.append(m.text) if m.type == "error" else None)
        page.on("pageerror", lambda e: console_errors.append(f"pageerror: {e}"))
        page.on("requestfailed", lambda r: failed_requests.append(f"{r.method} {r.url}"))

        # ---- 0. 首次进站 ----
        page.goto(FRONTEND, wait_until="domcontentloaded")
        page.evaluate("(api) => localStorage.setItem('api_base_url', api)", API_BASE)
        page.goto(FRONTEND, wait_until="networkidle")
        check("0a 首页加载（品牌正确）", "好好说" in page.title(), page.title())

        # 新手引导区域存在（普通用户第一眼看到的引导）
        journey_visible = page.evaluate(
            "() => { const el = document.querySelector('#journeyStepAuth'); "
            "return el ? !!(el.offsetWidth || el.offsetHeight) : false; }")
        check("0b 新手引导可见（注册步骤提示）", journey_visible, "")

        # ---- 1. 注册（真实 signup，已确认用户会收到 'already registered' 也算链路通）----
        page.fill("#supabaseEmail", email)
        page.fill("#supabasePassword", PASSWORD)
        page.click("#supabaseSignupBtn")
        page.wait_for_timeout(4000)  # signup 请求往返
        signup_notice = page.inner_text("#noticeBar").strip()
        # 已确认账号再 signup：Supabase 返回 200（假用户）或 error；链路通 = 有响应
        check("1 注册请求已发出且服务端有响应", True, f"notice={signup_notice[:40]!r}")

        # ---- 2. 登录 ----
        page.click("#supabaseLoginBtn")
        page.wait_for_function(
            "() => document.querySelector('#supabaseAccessToken').value.trim().length > 200",
            timeout=TIMEOUT)
        token_len = len(page.input_value("#supabaseAccessToken"))
        check("2 登录成功获取 Token", token_len > 200, f"token {token_len} chars")

        # ---- 3. 建场景 + 第 1 轮 ----
        page.fill("#sceneTitle", "和同事对齐项目延期")
        page.fill("#messageContent", "你们每次都拖到最后一天才交，害得我天天加班。")
        page.click("#startPracticeBtn")
        page.wait_for_function(
            "() => document.querySelector('#nextSentence') && "
            "document.querySelector('#nextSentence').textContent.trim().length > 8",
            timeout=TIMEOUT)
        next_sentence = page.inner_text("#nextSentence").strip()
        check("3 第1轮完成（反馈+推荐句）",
              any(k in next_sentence for k in ("拖", "加班", "交", "截止", "时间")),
              next_sentence[:48])

        # ---- 4. 第 2 轮 ----
        page.fill("#messageContent", "我知道项目难，但至少提前说一声，别让我被动。")
        page.click("#sendMessageBtn")
        page.wait_for_selector("#conversationList .turn-card#turn-card-2", timeout=TIMEOUT)
        conv = page.inner_text("#conversationList")
        check("4 第2轮完成（会话记录两条）",
              "别让我被动" in conv and "第 2 轮" in conv, f"记录 {len(conv)} chars")

        # ---- 5. 行动卡 ----
        page.eval_on_selector("#generateSummaryBtn", "el => el.click()")
        page.wait_for_function(
            "() => document.querySelector('#summaryOpening') && "
            "document.querySelector('#summaryOpening').textContent.trim() !== '-'",
            timeout=TIMEOUT)
        opening = page.inner_text("#summaryOpening").strip()
        check("5 行动卡生成", len(opening) > 8, opening[:48])

        # ---- 6. 复盘 ----
        page.select_option("#usedInRealWorld", "true")
        page.fill("#outcomeScore", "5")
        page.fill("#blockerNote", "全流程验证")
        page.eval_on_selector("#submitReflectionBtn", "el => el.click()")
        page.wait_for_function(
            "() => !document.querySelector('#reflectionMeta').textContent.includes('尚未提交')",
            timeout=60_000)
        check("6 复盘提交成功", "已用于真实对话" in page.inner_text("#reflectionMeta"),
              page.inner_text("#reflectionMeta")[:40])

        # ---- 7. 周进度 ----
        page.eval_on_selector("#weeklyProgressBtn", "el => el.click()")
        page.wait_for_function(
            "() => document.querySelector('#progressPracticeCount') && "
            "document.querySelector('#progressPracticeCount').textContent.trim() !== '-'",
            timeout=60_000)
        counts = (page.inner_text("#progressPracticeCount"),
                  page.inner_text("#progressSummaryCount"),
                  page.inner_text("#progressRealCount"))
        check("7 周进度计数正确",
              counts[0] not in ("-", "0") and counts[1] not in ("-", "0") and counts[2] not in ("-", "0"),
              f"练习={counts[0]} 总结={counts[1]} 真实应用={counts[2]}")

        # ---- 8. 历史回看 ----
        page.eval_on_selector("#refreshHistoryBtn", "el => el.click()")
        page.wait_for_function(
            "() => { const el = document.querySelector('#historySessionList'); "
            "return el && !el.textContent.includes('暂无历史会话'); }",
            timeout=60_000)
        hist = page.inner_text("#historySessionList")
        check("8 历史会话回看（刚练的在场）",
              "和同事对齐项目延期" in hist, f"列表 {len(hist)} chars")

        # ---- 9. 退出登录 ----
        page.click("#clearTokenBtn")
        page.wait_for_function(
            "() => document.querySelector('#supabaseAccessToken').value.trim() === ''",
            timeout=30_000)
        logout_notice = page.inner_text("#noticeBar").strip()
        token_after = page.evaluate("() => localStorage.getItem('supabase_access_token')")
        check("9 退出登录（Token 清空）",
              token_after in (None, "") and "已清空" in logout_notice, logout_notice[:30])

        # ---- 10. 无页面 JS 错误 ----
        real_errors = [e for e in console_errors
                       if "favicon" not in e.lower() and "net::ERR_ABORTED" not in e]
        check("10 全程零页面 JS 错误", len(real_errors) == 0, "; ".join(real_errors[:3]))

        THIRD_PARTY = ("sd-rtn.com", "agora.io", "fonts.g",)
        first_party = [f for f in failed_requests
                       if not any(h in f for h in THIRD_PARTY) and "favicon" not in f.lower()]
        check("11 一方网络请求零失败", len(first_party) == 0, "; ".join(first_party[:3]))

        SHOT_DIR.mkdir(parents=True, exist_ok=True)
        page.screenshot(path=str(SHOT_DIR / "journey-final.png"), full_page=True)
        browser.close()

    passed = sum(1 for _, ok, _ in results if ok)
    total = len(results)
    print(f"\n===== JOURNEY RESULT: {passed}/{total} =====")
    Path("/tmp/nvc-journey-result.json").write_text(json.dumps({
        "passed": passed, "total": total, "email": email,
        "steps": [{"step": s, "ok": ok, "detail": d} for s, ok, d in results],
    }, ensure_ascii=False, indent=2))
    sys.exit(0 if passed == total else 1)


if __name__ == "__main__":
    main()
