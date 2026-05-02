from __future__ import annotations

from .cefr import normalize_level

FRIENDLY_LEVELS: dict[str, str] = {
    "不确定：先按四级基础 / B1": "B1",
    "高中-四级入门：B1": "B1",
    "四级 425-500：B1": "B1",
    "四级 500+：B2": "B2",
    "六级 425-500：B2": "B2",
    "六级 500+：B2": "B2",
    "雅思 5.5：B1": "B1",
    "雅思 6.0：B2": "B2",
    "雅思 6.5：B2": "B2",
    "雅思 7.0：C1": "C1",
    "自定义 A1": "A1",
    "自定义 A2": "A2",
    "自定义 B1": "B1",
    "自定义 B2": "B2",
    "自定义 C1": "C1",
    "自定义 C2": "C2",
}


def to_cefr_level(label_or_level: str) -> str:
    if label_or_level in FRIENDLY_LEVELS:
        return FRIENDLY_LEVELS[label_or_level]
    level = normalize_level(label_or_level)
    return level or "B2"
