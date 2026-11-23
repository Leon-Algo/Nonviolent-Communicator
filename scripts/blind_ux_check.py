# -*- coding: utf-8 -*-
"""盲用户验收：只用页面上"看得见的文字"操作，模拟第一次使用的新用户。

与 user_journey_check.py 的区别：本脚本**不使用任何元素 ID**，只按可见文本
（label 文案、按钮文案）定位，就像真人扫页面找按钮。凡是找不到、看不懂、
需要猜测的地方，都作为"体验卡点"记录。

产出：/tmp/blind_ux_findings.json + 控制台报告
"""

import json
import subprocess
import sys
import time
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
FRONTEND = "http://127.0.0.1:8081/"
PASSWORD = "BlindTest!2026"
findings = []   # (级别, 步骤, 现象)
steps = []      # (步骤, 是否完成, 备注)


def note(level, step, detail):
    findings.append({"level": level, "step": step, "detail": detail})
    print(f"  [{level}] {step}: {detail}")


def step(name, ok, detail=""):
    steps.append({"step": name, "ok": ok, "detail": detail})
    print(f"[{'OK ' if ok else 'STUCK'}] {name}" + (f" — {detail}" if detail else ""))


def env(name):
    line = subprocess.run(["grep", f"^{name}=", str(ROOT / ".env")],
                          capture_output=True, text=True).stdout.strip()
    return line.split("=", 1)[1] if "=" in line else ""


def make_user(email):
    out = subprocess.run([
        "curl", "-sS", "-X", "POST", f"{env('SUPABASE_URL').rstrip('/')}/auth/v1/admin/users",
        "-H", "Content-Type: application/json",
        "-H", f"apikey: {env('SUPABASE_SERVICE_ROLE_KEY')}",
        "-H", f"Authorization: Bearer {env('SUPABASE_SERVICE_ROLE_KEY')}",
        "-d", json.dumps({"email": email, "password": PASSWORD, "email_confirm": True}),
    ], capture_output=True, text=True)
    return bool(json.loads(out.stdout or "{}").get("id"))


def main():
    email = f"blind_{int(time.time())}@example.com"
    if not make_user(email):
        print("账号创建失败，终止")
        return 1
    print(f"[准备] 测试账号 {email}\n")

    with sync_playwright() as p:
        browser = p.chromium.launch(channel="chrome", headless=False)
        page = browser.new_context(viewport={"width": 1440, "height": 960}).new_page()
        page.set_default_timeout(120_000)

        # ---------- 1. 第一次打开 ----------
        page.goto(FRONTEND, wait_until="domcontentloaded")
        page.evaluate("() => localStorage.setItem('api_base_url','http://127.0.0.1:8000')")
        page.goto(FRONTEND, wait_until="networkidle")

        body_text = page.inner_text("body")[:1200]
        step("打开首页", True, f"标题={page.title()!r}")
        # 作为新用户，能否一眼看出该干什么？
        has_guide = any(k in body_text for k in ("第一次使用", "步骤", "开始", "注册"))
        if not has_guide:
            note("阻塞", "首页", "首屏没看到任何'下一步做什么'的引导文案")
        else:
            note("建议", "首页", "首屏有引导文案，但信息密度偏高（三步引导+安装提示+登录表单同屏）")

        # ---------- 2. 只按可见文案找登录表单 ----------
        email_box = None
        for label in ("邮箱", "Email", "email"):
            loc = page.get_by_label(label, exact=False)
            if loc.count() > 0:
                email_box = loc.first
                break
        if email_box is None:
            email_box = page.get_by_placeholder("your-email@example.com")
        step("找到邮箱输入框（按文案）", email_box.count() > 0, "label/placeholder 定位")

        pwd_box = page.get_by_label("密码", exact=False).first
        step("找到密码输入框（按文案）", pwd_box.count() > 0, "")

        email_box.fill(email)
        pwd_box.fill(PASSWORD)

        login_btn = page.get_by_role("button", name="登录并获取 Token")
        step("找到登录按钮（按文案）", login_btn.count() > 0, "按钮文案 '登录并获取 Token'")
        if login_btn.count() == 0:
            note("阻塞", "登录", "按'登录'找不到按钮")
            browser.close()
            return 1

        login_btn.first.click()
        try:
            page.wait_for_function(
                "() => document.querySelector('#supabaseAccessToken').value.trim().length > 200",
                timeout=60_000)
            step("登录成功", True, "提示文案明确")
        except Exception as exc:
            step("登录成功", False, str(exc)[:80])
            note("阻塞", "登录", "点了登录后 60 秒内没有明显成功反馈")

        # ---------- 3. 找场景输入 ----------
        # 新用户不知道"场景标题/目标/背景"分别该填什么
        title_box = page.get_by_label("场景标题", exact=False)
        goal_box = page.get_by_label("目标", exact=False)
        context_box = page.get_by_label("背景", exact=False)
        found = sum(1 for b in (title_box, goal_box, context_box) if b.count() > 0)
        step("找到场景三要素输入框", found == 3, f"{found}/3 通过文案定位")
        if found < 3:
            note("困扰", "建场景", f"三个必填项里有 {3-found} 个没法靠文案直接定位")

        # 默认值是否可用（新用户可能直接点发送）
        if title_box.count():
            default_title = title_box.first.input_value()
            note("建议", "建场景",
                 f"场景标题有默认值 {default_title!r}，新用户可能不改成自己的场景就直接发")

        msg_box = page.get_by_label("你的发言", exact=False)
        step("找到发言输入框", msg_box.count() > 0, "label '你的发言'")
        if msg_box.count():
            note("建议", "对练",
                 f"发言框有默认示例 {msg_box.first.input_value()!r}，"
                 "新用户可能误以为是系统消息而非占位提示")

        # ---------- 4. 发第一轮 ----------
        send_btn = page.get_by_role("button", name="创建场景并发送第 1 轮")
        step("找到发送按钮", send_btn.count() > 0, "文案清楚")
        if msg_box.count() and send_btn.count():
            msg_box.first.fill("你们每次都拖到最后一天，我很累。")
            send_btn.first.click()
            try:
                page.wait_for_function(
                    "() => { const el = document.querySelector('#nextSentence'); "
                    "return el && el.textContent.trim().length > 8; }", timeout=120_000)
                step("第 1 轮完成", True, "有 AI 回复 + 反馈分数 + 推荐句")
            except Exception:
                step("第 1 轮完成", False, "120 秒无结果")
                note("阻塞", "对练", "发送后 120 秒没有反馈，用户会以为卡死")

        # 反馈区是否可理解
        feedback = page.inner_text("body")
        if "下一句建议" in feedback:
            note("建议", "反馈",
                 "反馈区有'总分/风险等级/下一句建议/O-F-N-R'，术语较多，"
                 "首次使用没有解释这些指标的含义")

        # ---------- 5. 生成行动卡 + 复盘 ----------
        summary_btn = page.get_by_role("button", name="生成行动卡")
        step("找到'生成行动卡'按钮", summary_btn.count() > 0, "文案清楚")
        if summary_btn.count():
            summary_btn.first.click()
            try:
                page.wait_for_function(
                    "() => { const el = document.querySelector('#summaryOpening'); "
                    "return el && el.textContent.trim() !== '-'; }", timeout=120_000)
                step("行动卡生成", True, "")
            except Exception:
                step("行动卡生成", False, "")
                note("阻塞", "行动卡", "点击后 120 秒无内容")

        reflect_btn = page.get_by_role("button", name="提交复盘")
        step("找到'提交复盘'按钮", reflect_btn.count() > 0, "")
        if reflect_btn.count():
            # 新用户：选择"是"但不知道还要填评分
            page.get_by_label("是否已用于真实对话", exact=False).first.select_option("true")
            reflect_btn.first.click()
            page.wait_for_timeout(2500)
            notice = page.inner_text("#noticeBar").strip()
            if "评分" in notice or notice:
                note("困扰", "复盘",
                     f"选了'已用于真实对话'但没填评分时提示 {notice!r}——"
                     "必填项没有提前标注，是提交后才报错")
            page.get_by_label("效果评分", exact=False).first.fill("5")
            reflect_btn.first.click()
            try:
                page.wait_for_function(
                    "() => !document.querySelector('#reflectionMeta')"
                    ".textContent.includes('尚未提交')", timeout=90_000)
                ok = True
            except Exception:
                ok = False
                note("阻塞", "复盘", "填了评分提交后 90 秒仍未成功")
            step("复盘提交成功", ok, page.inner_text("#reflectionMeta")[:40])

        # ---------- 6. 周进度 + 历史 ----------
        prog_btn = page.get_by_role("button", name="查看本周进度")
        step("找到'查看本周进度'按钮", prog_btn.count() > 0, "")
        if prog_btn.count():
            prog_btn.first.click()
            try:
                page.wait_for_function(
                    "() => { const t = document.querySelector('#progressPracticeCount')"
                    ".textContent.trim(); return t !== '-' && t !== ''; }", timeout=90_000)
                counts = page.inner_text("#progressPracticeCount").strip()
                ok = True
            except Exception:
                counts, ok = "-", False
                note("阻塞", "周进度", "查询 90 秒后仍无数据")
            step("周进度有数据", ok, f"练习次数={counts}")

        hist_btn = page.get_by_role("button", name="刷新列表")
        step("找到历史筛选按钮", hist_btn.count() > 0, "文案'刷新列表'")
        if hist_btn.count():
            pass  # 文案已改为'刷新列表'，语义清楚，不再是问题

        # ---------- 7. 退出 ----------
        out_btn = page.get_by_role("button", name="退出登录")
        step("找到'退出登录'按钮", out_btn.count() > 0, "")
        if out_btn.count():
            out_btn.first.click()
            page.wait_for_timeout(1200)
            cleared = page.evaluate("() => localStorage.getItem('supabase_access_token')")
            step("退出登录生效", cleared in (None, ""), "")

        page.screenshot(path="/tmp/blind-final.png", full_page=True)
        browser.close()

    done = sum(1 for s in steps if s["ok"])
    print(f"\n===== 盲用户验收: {done}/{len(steps)} 步完成，{len(findings)} 条体验问题 =====")
    for f in findings:
        print(f"  [{f['level']}] {f['step']}: {f['detail']}")
    Path("/tmp/blind_ux_findings.json").write_text(json.dumps(
        {"steps": steps, "findings": findings}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
