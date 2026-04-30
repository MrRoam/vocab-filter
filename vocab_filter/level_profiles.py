from __future__ import annotations

from dataclasses import dataclass

from .cefr import LEVELS


@dataclass(frozen=True)
class LevelProfile:
    label: str
    cefr_level: str
    description: str


PROFILE_OPTIONS: list[LevelProfile] = [
    LevelProfile("高中 / 高考基础", "B1", "大多数 A1-A2 跳过，B1 作为边界，B2+ 优先输出。"),
    LevelProfile("四级 425-500", "B1", "适合刚过四级或四级中等水平。"),
    LevelProfile("四级 500+", "B2", "适合四级较高分、准备六级。"),
    LevelProfile("六级 425-500", "B2", "适合刚过六级或六级中等水平。"),
    LevelProfile("六级 500+", "B2", "仍建议按 B2 过滤，C1/C2 会更突出。"),
    LevelProfile("IELTS 5.5", "B1", "偏 B1-B2，保守起见按 B1。"),
    LevelProfile("IELTS 6.0", "B2", "常用作 B2 近似。"),
    LevelProfile("IELTS 6.5", "B2", "偏 B2-C1，默认按 B2。"),
    LevelProfile("IELTS 7.0+", "C1", "适合较强阅读词汇水平。"),
]


PROFILE_LABELS = [p.label for p in PROFILE_OPTIONS]


def profile_to_cefr(label: str) -> str:
    for profile in PROFILE_OPTIONS:
        if profile.label == label:
            return profile.cefr_level
    if label in LEVELS:
        return label
    return "B2"


def estimate_level_from_quiz(level_scores: dict[str, float]) -> str:
    """Return the highest CEFR level with recognition rate >= 0.70."""
    estimated = "A1"
    for level in LEVELS:
        if level_scores.get(level, 0.0) >= 0.70:
            estimated = level
    return estimated
