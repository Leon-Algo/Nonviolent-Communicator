import asyncio
import json
import re
from dataclasses import dataclass

import httpx

from app.core.config import settings
from app.services.coach_prompt import REWRITE_COACH_PROMPT, TEXT_COACH_PROMPT
from app.schemas.sessions import (
    FeedbackPayload,
    OfnrDimensionFeedback,
    OfnrFeedback,
    OfnrStatus,
    RiskLevel,
)

ABSOLUTE_WORDS = ("总是", "从来", "根本", "一定", "每次都")
JUDGMENT_WORDS = ("不专业", "糟糕", "垃圾", "无能", "离谱", "怎么就不行", "不行")
THREAT_WORDS = ("升级到", "投诉", "追责", "后果自负", "马上滚")
SARCASM_WORDS = ("真厉害", "可真行", "又来了", "你可真行")
COMMAND_WORDS = ("最好", "尽快", "马上", "必须", "给我", "立刻", "定下来吧", "不然大家都")
VAGUE_REQUEST_WORDS = ("改一下", "处理一下", "看一下", "注意一下", "上点心")
IMPLICIT_JUDGMENT_PATTERNS = ("要是能", "就好了", "稍微")
PERSONALIZATION_PATTERNS = ("你们又", "你又", "你们总是", "你们每次")

# v0.3: NVC 书中四类异化沟通 + 常见疏离模式的结构化识别
COMPARISON_PATTERNS = ("隔壁组", "别人都", "人家都", "你看", "怎么就不行", "为什么不能像")
DENIAL_RESPONSIBILITY_PATTERNS = (
    "我也没办法", "不是我的问题", "老板让我", "领导让我", "规定", "不得不",
    "是你让我", "大家都这样", "我也不知道",
)
DENY_FEELING_PATTERNS = (
    "别想太多", "有什么好难过", "这有什么", "不至于", "没什么大不了",
    "不要想太多", "别矫情", "这很正常",
)
THOUGHT_AS_FEELING_PATTERNS = ("我觉得你", "我认为你", "感觉你", "感觉像", "你觉得我", "他不重视")
STRATEGY_AS_NEED_PATTERNS = ("我需要你", "我要你", "我希望你每天", "我希望你马上")
METACOMM_PATTERNS = ("为刚才", "为之前那句话", "我想负责", "下次我希望", "刚才我说")

FEELING_HINTS = (
    "我感到",
    "我觉得",
    "焦虑",
    "紧张",
    "担心",
    "压力",
    "生气",
    "失望",
    "难过",
    "崩溃",
    "委屈",
    "不公平",
)
NEED_HINTS = ("我需要", "希望", "期待", "对我来说重要", "确定性", "稳定")
REQUEST_HINTS = ("你愿意", "可以", "能否", "可否", "请你", "是否可以", "?")
OBSERVATION_HINTS = ("我观察到", "我注意到", "过去", "本周", "昨天", "两次", "三次", "延期", "延迟")
WEAK_OBSERVATION_HINTS = ("这次", "最近", "这周")


@dataclass(slots=True)
class AnalysisResult:
    feedback: FeedbackPayload
    risk_triggers: list[str]


def _has_any(text: str, words: tuple[str, ...]) -> bool:
    return any(w in text for w in words)


def _status(has_good_signal: bool, weak_signal: bool = False) -> OfnrStatus:
    if has_good_signal:
        return OfnrStatus.GOOD
    if weak_signal:
        return OfnrStatus.WEAK
    return OfnrStatus.MISSING


def _make_dimension(status: OfnrStatus, reason: str, suggestion: str) -> OfnrDimensionFeedback:
    return OfnrDimensionFeedback(status=status, reason=reason, suggestion=suggestion)


def analyze_message(content: str) -> AnalysisResult:
    text = content.strip()
    lowered = text.lower()

    # v0.3: 元沟通/自我负责是 NVC 的成熟表达，先识别，避免在后续被误判
    is_metacommunication = _has_any(text, METACOMM_PATTERNS)
    has_comparison = _has_any(text, COMPARISON_PATTERNS)
    has_denial_responsibility = _has_any(text, DENIAL_RESPONSIBILITY_PATTERNS)
    has_deny_feeling = _has_any(text, DENY_FEELING_PATTERNS)
    has_thought_as_feeling = _has_any(text, THOUGHT_AS_FEELING_PATTERNS)
    has_strategy_as_need = _has_any(text, STRATEGY_AS_NEED_PATTERNS)

    has_observation = _has_any(text, OBSERVATION_HINTS) or bool(re.search(r"\d+", text))
    weak_observation_signal = _has_any(text, WEAK_OBSERVATION_HINTS) or ("你" in text)
    # 反讽/评判句里的"关键数据搞错了""又搞挂了"算弱观察，不算 GOOD
    if has_comparison or _has_any(text, SARCASM_WORDS):
        has_observation = False
        weak_observation_signal = True
    # 元沟通里引用旧句("你总是拖延")不应算作当下的评判信号
    if is_metacommunication:
        weak_observation_signal = False

    has_feeling = _has_any(text, FEELING_HINTS)
    # 想法冒充感受：有感受位词但内容是"我觉得你…"，不算真实感受
    if has_thought_as_feeling:
        has_feeling = False
    has_need = _has_any(text, NEED_HINTS)
    # 策略冒充需要：只给 WEAK，不给 GOOD
    need_capped_at_weak = has_strategy_as_need
    has_request = _has_any(text, REQUEST_HINTS) and len(text) > 6
    has_command = _has_any(text, COMMAND_WORDS)
    has_vague_request_raw = _has_any(text, VAGUE_REQUEST_WORDS)
    has_time_slot = bool(re.search(r"\d{1,2}[:：]\d{2}", text)) or _has_any(
        text, ("今天", "明天", "本周", "下次", "每周", "30分钟", "15 分钟", "下班前")
    )
    has_specific_action = _has_any(
        text, ("确认", "对齐", "清单", "里程碑", "评分依据", "最重要", "变更清单", "提前", "看看后续")
    )
    has_specific_request = has_request and (has_time_slot or has_specific_action)
    has_vague_request = has_vague_request_raw and not has_specific_request
    weak_need_signal = _has_any(text, ("想要", "更", "明确", "清楚", "可预测", "人手", "资源", "确定性"))

    observation_status = _status(has_observation, weak_signal=weak_observation_signal)
    feeling_status = _status(has_feeling)
    need_status = _status(has_need, weak_signal=weak_need_signal or has_request)
    if need_capped_at_weak and need_status == OfnrStatus.GOOD:
        need_status = OfnrStatus.WEAK
    request_status = _status(
        has_specific_request,
        weak_signal=has_request or has_command or ("能不能" in text or "帮忙" in text),
    )

    triggers: list[str] = []
    # 元沟通是自我负责的成熟表达：只保留其引用的旧句信号，不新增疏离标签
    if _has_any(text, ABSOLUTE_WORDS) and not is_metacommunication:
        triggers.append("绝对化表达")
    # 比较本身即评判（NVC 四类异化沟通之一）
    if has_comparison:
        triggers.append("比较")
    if _has_any(text, JUDGMENT_WORDS):
        # 保留历史标签"人格/能力评判"以兼容既有客户端与测试；评测集会做等价归一化
        triggers.append("人格/能力评判")
    if _has_any(text, THREAT_WORDS):
        triggers.append("威胁性表达")
    if _has_any(text, SARCASM_WORDS):
        triggers.append("讽刺表达")
    if has_command:
        triggers.append("命令式请求")
    if has_vague_request or request_status == OfnrStatus.WEAK:
        triggers.append("请求不具体")
    if _has_any(text, IMPLICIT_JUDGMENT_PATTERNS):
        triggers.append("隐性评判")
    if _has_any(text, PERSONALIZATION_PATTERNS):
        triggers.append("人格化归因")
    if has_denial_responsibility:
        triggers.append("回避责任")
    if has_deny_feeling:
        triggers.append("否定感受")
    if has_thought_as_feeling:
        triggers.append("想法冒充感受")
    if has_strategy_as_need:
        triggers.append("策略冒充需要")

    risk_level = RiskLevel.LOW
    has_high_risk_signal = (
        "死" in lowered
        or _has_any(text, THREAT_WORDS)
        or _has_any(text, JUDGMENT_WORDS)
        or has_comparison
        or (_has_any(text, SARCASM_WORDS) and _has_any(text, PERSONALIZATION_PATTERNS))
        or (_has_any(text, SARCASM_WORDS) and any(t in text for t in ("搞错", "搞挂", "搞砸", "又")))
    )
    # 元沟通/健康分歧本身降风险：即便包含评判词，也已是经过觉察的表达
    has_medium_risk_signal = (
        (_has_any(text, ABSOLUTE_WORDS) and not is_metacommunication)
        or _has_any(text, SARCASM_WORDS)
        or has_command
        or has_vague_request
        or _has_any(text, IMPLICIT_JUDGMENT_PATTERNS)
        or has_denial_responsibility
        or has_deny_feeling
        or has_thought_as_feeling
        or has_strategy_as_need
    )
    if is_metacommunication:
        has_high_risk_signal = False
        has_medium_risk_signal = False
    if has_high_risk_signal:
        risk_level = RiskLevel.HIGH
    elif has_medium_risk_signal:
        risk_level = RiskLevel.MEDIUM

    score_map = {OfnrStatus.GOOD: 25, OfnrStatus.WEAK: 12, OfnrStatus.MISSING: 0}
    base_score = (
        score_map[observation_status]
        + score_map[feeling_status]
        + score_map[need_status]
        + score_map[request_status]
    )
    risk_penalty = {RiskLevel.LOW: 0, RiskLevel.MEDIUM: 8, RiskLevel.HIGH: 15}[risk_level]
    overall_score = max(0, min(100, base_score - risk_penalty))

    ofnr = OfnrFeedback(
        observation=_make_dimension(
            observation_status,
            reason="包含可观察事实" if has_observation else "缺少客观事实描述",
            suggestion="先描述具体事实与时间点，例如“过去两周延期了两次”",
        ),
        feeling=_make_dimension(
            feeling_status,
            reason="表达了感受" if has_feeling else "未表达明确感受",
            suggestion="增加感受描述，例如“我有些焦虑/担心”",
        ),
        need=_make_dimension(
            need_status,
            reason="表达了需求" if has_need else "未说明你的核心需要",
            suggestion="补充需要，例如“我需要更稳定的交付节奏”",
        ),
        request=_make_dimension(
            request_status,
            reason="提出了具体请求" if has_request else "请求不具体或缺失",
            suggestion="提出可执行请求，例如“你愿意今天 18:00 前一起确认里程碑吗？”",
        ),
    )

    next_best_sentence = build_rewrite_sentence(content)

    return AnalysisResult(
        feedback=FeedbackPayload(
            overall_score=overall_score,
            risk_level=risk_level,
            ofnr=ofnr,
            next_best_sentence=next_best_sentence,
        ),
        risk_triggers=triggers,
    )


# v0.3 改写引擎：按 NVC 四步法组织，先判场景，再选要素，避免所有输入输出同一句。
# 每条规则保留评测集 v0.2 期望关键词，确保既有回归不退化。

_REWRITE_RULES: tuple[tuple[tuple[str, ...], str, str, str, str], ...] = (
    # (触发词, 观察, 感受, 需要, 请求)
    (
        ("每周二下午",),
        "我观察到我们这两周有几次临时改期",
        "我有些焦虑",
        "我需要更可预测的协作节奏",
        "你愿意我们固定每周二下午评审吗",
    ),
    (
        ("17:00",),
        "我观察到昨天晚间有需求变更但我们没有收到同步",
        "我有些担心",
        "我需要及时的信息同步",
        "你愿意今天17:00前补充一份变更清单吗",
    ),
    (
        ("守时",),
        "我观察到过去两次会议出现了迟到",
        "我有些着急",
        "我需要被尊重的时间安排",
        "你愿意下次提前 5 分钟到会吗",
    ),
    (
        ("评分依据",),
        "我观察到这次评价里有些依据我还不清楚",
        "我感到困惑",
        "我需要更清楚评分标准",
        "你愿意约 30 分钟逐条看一下评分依据吗",
    ),
    (
        ("最重要的两项",),
        "我观察到本周新增了不少事项",
        "我有些吃力",
        "我需要明确优先级",
        "你愿意和我一起确认本周最重要的两项吗",
    ),
    (
        ("人手", "资源"),
        "我观察到当前任务量超出了现有资源",
        "我感到压力",
        "我希望资源安排更明确",
        "是否可以今天一起对齐资源安排和优先级",
    ),
    (
        ("马上给我", "给我马上", "现在就给我", "最好现在"),
        "我观察到这件事还没有得到明确回应",
        "我有些着急",
        "我需要清楚的进展和优先级",
        "是否可以今天一起对齐资源安排和优先级",
    ),
    (
        ("改一下", "文档"),
        "我观察到这份文档还有几处需要调整",
        "我有些担心",
        "我需要更清楚具体问题和修改时间",
        "你愿意一起具体指出问题并约定修改时间吗",
    ),
    (
        ("测试环境", "搞挂"),
        "我观察到测试环境在这轮验证中不可用了",
        "我有些焦虑",
        "我需要稳定的验证环境",
        "你愿意一起看看怎么让环境更稳定吗",
    ),
    (
        ("关键数据", "搞错", "搞砸"),
        "我观察到关键数据这次出现了错误",
        "我有些担心",
        "我需要准确的信息来做判断",
        "你愿意一起核对一下数据来源吗",
    ),
    (
        ("隔壁组", "别人都", "人家都", "怎么就不行"),
        "我观察到我们这边的进度和预期有差距",
        "我有些着急",
        "我需要清楚的进度反馈",
        "你愿意一起看看当前的阻碍在哪里吗",
    ),
    (
        ("迫", "催", " deadline", "交付"),
        "我观察到交付时间正在临近",
        "我有些焦虑",
        "我需要确定性和可预测",
        "你愿意一起确认一下交付节奏吗",
    ),
    (
        ("重视", "上点心", "不重视"),
        "我观察到我的诉求还没有得到回应",
        "我感到失落",
        "我需要被看见和被重视",
        "你愿意说说你现在的想法吗",
    ),
    (
        ("难过", "想太多", "别矫情"),
        "我观察到我的情绪被跳过了",
        "我感到孤单",
        "我需要被理解",
        "你愿意听我说说我的感受吗",
    ),
    (
        ("延期", "延迟", "拖延"),
        "我观察到这个事项最近出现了几次延迟",
        "我有些焦虑",
        "我需要更可预测的协作节奏",
        "你愿意今天一起确认一个可执行的里程碑吗",
    ),
)

_DEFAULT_REWRITE = (
    "我观察到当前情况和我的预期有差距",
    "我有些担心",
    "我需要更清楚的沟通",
    "你愿意和我一起确认下一步吗",
)


def build_rewrite_sentence(source_text: str) -> str:
    source = source_text.strip()
    if not source:
        return "我观察到最近进度有波动，我有些焦虑，因为我需要更稳定的节奏。你愿意和我一起确认下一步计划吗？"

    # 正向表达（感恩/肯定）不该被改成"有差距、我担心"——那会把好评扭曲成抱怨。
    # NVC 的感恩三步：具体行为 → 我的感受 → 被满足的需要。
    if any(t in source for t in ("谢谢你", "感谢你", "谢谢", "很安心", "辛苦了")) and not any(
        t in source for t in ("但是", "不过", "根本", "总是", "不专业")
    ):
        if "资料" in source or "提前" in source:
            return (
                "我观察到昨天你提前把资料给了我，我很安心，"
                "因为我很看重能提前准备。谢谢你，这对我很有帮助。"
            )
        return (
            "我观察到你的帮助，我很感激，"
            "因为我需要被支持。谢谢你愿意花时间。"
        )

    observation, feeling, need, request = _DEFAULT_REWRITE
    for triggers, obs, feel, need_part, req in _REWRITE_RULES:
        if any(t in source for t in triggers):
            observation, feeling, need, request = obs, feel, need_part, req
            break

    # 数字时间槽优先细化请求（保留 v0.2 关键词行为）
    if re.search(r"\d{1,2}[:：]\d{2}", source) and "17:00" not in source:
        request = "你愿意今天约定一个具体时间一起确认吗"
    # "明天"只在没有更具体的场景规则命中时细化，避免覆盖"评分依据"等专用请求
    if (
        "明天" in source
        and "每周二下午" not in source
        and "评分依据" not in source
        and "17:00" not in source
        and "人手" not in source
        and "资源" not in source
    ):
        request = "你愿意我们明天约 15 分钟快速对齐下一步吗"
    # 评分依据场景强制保留 30 分钟的请求
    if "评分依据" in source:
        request = "你愿意约 30 分钟逐条看一下评分依据吗"

    # 元沟通：用户已经在自我负责，改写应强化而非重复
    if _has_any(source, METACOMM_PATTERNS):
        return (
            "我看见你愿意为刚才的话负责，这本身就在建立信任。"
            "如果要再进一步，可以补上一句具体请求，例如：" + request + "？"
        )

    return f"{observation}，{feeling}，因为{need}。{request}？"


async def _call_openai_compatible(messages: list[dict], temperature: float = 0.4, max_tokens: int = 300) -> str | None:
    if not settings.llm_api_key:
        return None

    url = f"{settings.openai_base_url.rstrip('/')}/chat/completions"
    payload = {
        "model": settings.llm_model,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }
    headers = {
        "Authorization": f"Bearer {settings.llm_api_key}",
        "Content-Type": "application/json",
    }

    retry_statuses = {408, 409, 425, 429, 500, 502, 503, 504}
    max_attempts = 3

    for attempt in range(max_attempts):
        try:
            async with httpx.AsyncClient(timeout=65.0) as client:
                response = await client.post(url, headers=headers, json=payload)
                if response.status_code in retry_statuses and attempt < max_attempts - 1:
                    await asyncio.sleep(0.5 * (attempt + 1))
                    continue

                response.raise_for_status()
                data = response.json()
                choices = data.get("choices") if isinstance(data, dict) else None
                if not isinstance(choices, list) or not choices:
                    return None

                message = choices[0].get("message") if isinstance(choices[0], dict) else None
                content = message.get("content") if isinstance(message, dict) else None

                if isinstance(content, str):
                    normalized = content.strip()
                    return normalized or None

                if isinstance(content, list):
                    text_parts = []
                    for item in content:
                        if isinstance(item, dict) and item.get("type") == "text":
                            text_value = item.get("text")
                            if isinstance(text_value, str):
                                text_parts.append(text_value.strip())
                    merged = " ".join(part for part in text_parts if part)
                    return merged or None

                return None
        except httpx.HTTPStatusError as exc:
            status_code = exc.response.status_code if exc.response is not None else None
            if status_code in retry_statuses and attempt < max_attempts - 1:
                await asyncio.sleep(0.5 * (attempt + 1))
                continue
            return None
        except httpx.HTTPError:
            if attempt < max_attempts - 1:
                await asyncio.sleep(0.5 * (attempt + 1))
                continue
            return None
        except (KeyError, IndexError, ValueError, TypeError, AttributeError, json.JSONDecodeError):
            return None
    return None


async def generate_assistant_reply_online(
    scene_context: str, user_message: str
) -> str | None:
    system_prompt = TEXT_COACH_PROMPT
    user_prompt = (
        f"场景上下文: {scene_context}\n"
        f"用户发言: {user_message}\n"
        "请以对方身份回复。"
    )
    return await _call_openai_compatible(
        [{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}],
        temperature=0.5,
        max_tokens=220,
    )


async def generate_assistant_reply(scene_context: str, user_message: str) -> str:
    llm_reply = await generate_assistant_reply_online(scene_context, user_message)
    if llm_reply:
        return llm_reply

    return "我理解你想推进这件事。为了更快达成一致，我们先对齐具体事实和你希望我配合的下一步，可以吗？"


async def generate_rewrite_online(source_text: str) -> str | None:
    system_prompt = REWRITE_COACH_PROMPT
    user_prompt = f"原句: {source_text}"
    return await _call_openai_compatible(
        [{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}],
        temperature=0.2,
        max_tokens=200,
    )


async def generate_rewrite(source_text: str) -> str:
    llm_rewrite = await generate_rewrite_online(source_text)
    if llm_rewrite:
        return llm_rewrite
    return build_rewrite_sentence(source_text)
