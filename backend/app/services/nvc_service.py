import asyncio
import json
import re
from dataclasses import dataclass

import httpx

from app.core.config import settings
from app.schemas.sessions import (
    FeedbackPayload,
    OfnrDimensionFeedback,
    OfnrFeedback,
    OfnrStatus,
    RiskLevel,
)

ABSOLUTE_WORDS = ("总是", "从来", "根本", "一定", "每次都")
JUDGMENT_WORDS = ("不专业", "糟糕", "垃圾", "无能", "离谱")
THREAT_WORDS = ("升级到", "投诉", "追责", "后果自负", "马上滚")
SARCASM_WORDS = ("真厉害", "可真行", "又来了")
COMMAND_WORDS = ("最好", "尽快", "马上", "必须", "给我", "立刻")
VAGUE_REQUEST_WORDS = ("改一下", "处理一下", "看一下", "注意一下")
IMPLICIT_JUDGMENT_PATTERNS = ("要是能", "就好了", "稍微")
PERSONALIZATION_PATTERNS = ("你们又", "你又", "你们总是", "你们每次")

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

    has_observation = _has_any(text, OBSERVATION_HINTS) or bool(re.search(r"\d+", text))
    weak_observation_signal = _has_any(text, WEAK_OBSERVATION_HINTS) or ("你" in text)
    has_feeling = _has_any(text, FEELING_HINTS)
    has_need = _has_any(text, NEED_HINTS)
    has_request = _has_any(text, REQUEST_HINTS) and len(text) > 6
    has_command = _has_any(text, COMMAND_WORDS)
    has_vague_request_raw = _has_any(text, VAGUE_REQUEST_WORDS)
    has_time_slot = bool(re.search(r"\d{1,2}[:：]\d{2}", text)) or _has_any(
        text, ("今天", "明天", "本周", "下次", "每周", "30分钟", "15 分钟")
    )
    has_specific_action = _has_any(
        text, ("确认", "对齐", "清单", "里程碑", "评分依据", "最重要", "变更清单", "提前")
    )
    has_specific_request = has_request and (has_time_slot or has_specific_action)
    has_vague_request = has_vague_request_raw and not has_specific_request
    weak_need_signal = _has_any(text, ("想要", "更", "明确", "清楚", "可预测", "人手", "资源"))

    observation_status = _status(has_observation, weak_signal=weak_observation_signal)
    feeling_status = _status(has_feeling)
    need_status = _status(has_need, weak_signal=weak_need_signal or has_request)
    request_status = _status(
        has_specific_request,
        weak_signal=has_request or has_command or ("能不能" in text or "帮忙" in text),
    )

    triggers: list[str] = []
    if _has_any(text, ABSOLUTE_WORDS):
        triggers.append("绝对化表达")
    if _has_any(text, JUDGMENT_WORDS):
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

    risk_level = RiskLevel.LOW
    has_high_risk_signal = (
        "死" in lowered
        or _has_any(text, THREAT_WORDS)
        or _has_any(text, JUDGMENT_WORDS)
        or (_has_any(text, SARCASM_WORDS) and _has_any(text, PERSONALIZATION_PATTERNS))
    )
    has_medium_risk_signal = (
        _has_any(text, ABSOLUTE_WORDS)
        or _has_any(text, SARCASM_WORDS)
        or has_command
        or has_vague_request
        or _has_any(text, IMPLICIT_JUDGMENT_PATTERNS)
    )
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


def build_rewrite_sentence(source_text: str) -> str:
    source = source_text.strip()
    if not source:
        return "我观察到最近进度有波动，我有些焦虑，因为我需要更稳定的节奏。你愿意和我一起确认下一步计划吗？"

    observation = "我观察到这个事项最近出现了几次延迟"
    if "每周二下午" in source:
        observation = "我观察到我们这两周有几次临时改期"
    elif "17:00" in source:
        observation = "我观察到昨天晚间有需求变更但我们没有收到同步"
    elif "守时" in source:
        observation = "我观察到过去两次会议出现了迟到"
    elif "评分依据" in source:
        observation = "我观察到这次评价里有些依据我还不清楚"
    elif "延期" in source or "延迟" in source:
        observation = "我观察到这个事项最近有延期"
    if re.search(r"\d+", source) and "17:00" not in source:
        observation = "我观察到最近有多次变更或延期"

    feeling = "我有些焦虑"
    if any(w in source for w in ("生气", "愤怒")):
        feeling = "我有些着急"
    if "压力" in source:
        feeling = "我感到压力"
    if "崩溃" in source:
        feeling = "我感到压力有点大"
    if any(w in source for w in ("担心", "焦虑", "紧张")):
        feeling = "我有些担心"

    need = "我需要更可预测的协作节奏"
    if "更多人手" in source or "人手" in source:
        need = "我希望资源安排更明确"
    if "资源" in source:
        need = "我需要明确资源和优先级"
    if "标准" in source:
        need = "我需要更清晰的标准"
    if "评分依据" in source:
        need = "我需要更清楚评分标准"

    request = "你愿意今天一起确认一个可执行的里程碑吗"
    if "最好" in source or "给我" in source:
        request = "是否可以今天一起对齐资源安排和优先级"
    if "明天" in source:
        request = "你愿意我们明天约 15 分钟快速对齐下一步吗"
    if "每周二下午" in source:
        request = "你愿意我们固定每周二下午评审吗"
    if "改一下" in source:
        request = "你愿意一起具体指出问题并约定修改时间吗"
    if "守时" in source:
        request = "你愿意下次提前 5 分钟到会吗"
    if "17:00" in source:
        request = "你愿意今天17:00前补充一份变更清单吗"
    if "评分依据" in source:
        request = "你愿意约 30 分钟逐条看一下评分依据吗"
    if "最重要的两项" in source:
        request = "你愿意和我一起确认本周最重要的两项吗"

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
            async with httpx.AsyncClient(timeout=20.0) as client:
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
    system_prompt = (
        "你是职场沟通场景中的对话对方，请保持克制、真实、简洁。"
        "你要基于对方发言给出自然回应，并适度推动对齐下一步。"
        "回复限制在 2-4 句中文。"
    )
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
    system_prompt = (
        "你是非暴力沟通教练。请将输入句子改写成 OFNR 风格：观察、感受、需要、请求。"
        "保持原意，不加入新事实，输出 1 句中文即可。"
    )
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
