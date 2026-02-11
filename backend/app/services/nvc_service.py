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

FEELING_HINTS = ("我感到", "我觉得", "焦虑", "紧张", "担心", "压力", "生气", "失望", "难过")
NEED_HINTS = ("我需要", "希望", "期待", "对我来说重要", "确定性", "稳定")
REQUEST_HINTS = ("你愿意", "可以", "能否", "可否", "请你", "是否可以", "?")
OBSERVATION_HINTS = ("我观察到", "我注意到", "过去", "本周", "昨天", "两次", "三次", "延期", "延迟")


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
    has_feeling = _has_any(text, FEELING_HINTS)
    has_need = _has_any(text, NEED_HINTS)
    has_request = _has_any(text, REQUEST_HINTS) and len(text) > 6

    observation_status = _status(has_observation, weak_signal=("你们" in text or "你" in text))
    feeling_status = _status(has_feeling)
    need_status = _status(has_need, weak_signal=("希望" in text or "想要" in text))
    request_status = _status(has_request, weak_signal=("能不能" in text or "帮忙" in text))

    triggers: list[str] = []
    if _has_any(text, ABSOLUTE_WORDS):
        triggers.append("绝对化表达")
    if _has_any(text, JUDGMENT_WORDS):
        triggers.append("人格/能力评判")
    if _has_any(text, THREAT_WORDS):
        triggers.append("威胁性表达")
    if _has_any(text, SARCASM_WORDS):
        triggers.append("讽刺表达")

    risk_level = RiskLevel.LOW
    if "死" in lowered or _has_any(text, THREAT_WORDS) or _has_any(text, JUDGMENT_WORDS):
        risk_level = RiskLevel.HIGH
    elif _has_any(text, ABSOLUTE_WORDS) or _has_any(text, SARCASM_WORDS):
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
    if "延期" in source or "延迟" in source:
        observation = "我观察到这个事项最近有延期"
    if re.search(r"\d+", source):
        observation = "我观察到最近有多次变更或延期"

    feeling = "我有些焦虑"
    if any(w in source for w in ("生气", "愤怒")):
        feeling = "我有些着急"
    if any(w in source for w in ("担心", "焦虑", "紧张", "压力")):
        feeling = "我有些担心"

    need = "我需要更可预测的协作节奏"
    if "资源" in source:
        need = "我需要明确资源和优先级"
    if "标准" in source:
        need = "我需要更清晰的标准"

    request = "今天一起确认一个可执行的里程碑吗"
    if "明天" in source:
        request = "我们明天约 15 分钟快速对齐下一步吗"

    return f"{observation}，{feeling}，因为{need}。你愿意{request}？"


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

    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            response = await client.post(url, headers=headers, json=payload)
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
    except (httpx.HTTPError, KeyError, IndexError, ValueError, TypeError, AttributeError, json.JSONDecodeError):
        return None


async def generate_assistant_reply(scene_context: str, user_message: str) -> str:
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
    llm_reply = await _call_openai_compatible(
        [{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}],
        temperature=0.5,
        max_tokens=220,
    )
    if llm_reply:
        return llm_reply

    return "我理解你想推进这件事。为了更快达成一致，我们先对齐具体事实和你希望我配合的下一步，可以吗？"


async def generate_rewrite(source_text: str) -> str:
    system_prompt = (
        "你是非暴力沟通教练。请将输入句子改写成 OFNR 风格：观察、感受、需要、请求。"
        "保持原意，不加入新事实，输出 1 句中文即可。"
    )
    user_prompt = f"原句: {source_text}"
    llm_rewrite = await _call_openai_compatible(
        [{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}],
        temperature=0.2,
        max_tokens=200,
    )
    if llm_rewrite:
        return llm_rewrite
    return build_rewrite_sentence(source_text)
