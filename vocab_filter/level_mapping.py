from __future__ import annotations

from dataclasses import dataclass

from .cefr import normalize_level

CEFR_OPTIONS = ["A1", "A2", "B1", "B2", "C1", "C2"]


@dataclass(frozen=True)
class LevelEstimate:
    level: str
    note: str


def score_to_cefr(exam: str, score: float) -> LevelEstimate:
    """Approximate exam-score-to-CEFR mapping for filtering purposes.

    The result is intentionally coarse. It is used to set a default filtering level,
    not to certify the user's language proficiency.
    """
    exam = exam.strip()

    if exam == "CET-4 四级":
        if score < 425:
            return LevelEstimate("B1", "四级未过线，先按 B1 筛词。")
        if score < 550:
            return LevelEstimate("B1", "四级通过至中高分段，先按 B1 筛词。")
        return LevelEstimate("B2", "四级高分段，先按 B2 筛词。")

    if exam == "CET-6 六级":
        if score < 425:
            return LevelEstimate("B1", "六级未过线，先按 B1 筛词。")
        if score < 600:
            return LevelEstimate("B2", "六级通过至中高分段，先按 B2 筛词。")
        return LevelEstimate("C1", "六级高分段，先按 C1 筛词。")

    if exam == "IELTS 雅思":
        if score < 4.0:
            return LevelEstimate("A2", "雅思 4.0 以下，先按 A2 筛词。")
        if score < 5.5:
            return LevelEstimate("B1", "雅思 4.0-5.0，先按 B1 筛词。")
        if score < 7.0:
            return LevelEstimate("B2", "雅思 5.5-6.5，先按 B2 筛词。")
        if score < 8.5:
            return LevelEstimate("C1", "雅思 7.0-8.0，先按 C1 筛词。")
        return LevelEstimate("C2", "雅思 8.5-9.0，先按 C2 筛词。")

    if exam == "TOEFL iBT 托福":
        if score < 42:
            return LevelEstimate("A2", "托福 42 以下，先按 A2 筛词。")
        if score < 72:
            return LevelEstimate("B1", "托福 42-71，先按 B1 筛词。")
        if score < 95:
            return LevelEstimate("B2", "托福 72-94，先按 B2 筛词。")
        if score < 114:
            return LevelEstimate("C1", "托福 95-113，先按 C1 筛词。")
        return LevelEstimate("C2", "托福 114+，先按 C2 筛词。")

    if exam == "Duolingo English Test":
        if score < 80:
            return LevelEstimate("A2", "DET 80 以下，先按 A2 筛词。")
        if score < 110:
            return LevelEstimate("B1", "DET 80-105，先按 B1 筛词。")
        if score < 130:
            return LevelEstimate("B2", "DET 110-125，先按 B2 筛词。")
        if score < 150:
            return LevelEstimate("C1", "DET 130-145，先按 C1 筛词。")
        return LevelEstimate("C2", "DET 150+，先按 C2 筛词。")

    if exam == "高考英语":
        # Support both 150-point and 100-point style scores by using the raw score.
        if score <= 100:
            pct = score / 100
        else:
            pct = score / 150
        if pct < 0.60:
            return LevelEstimate("A2", "高考英语低于 60%，先按 A2 筛词。")
        if pct < 0.82:
            return LevelEstimate("B1", "高考英语 60%-82%，先按 B1 筛词。")
        return LevelEstimate("B2", "高考英语较高分段，先按 B2 筛词。")

    return LevelEstimate("B2", "未识别考试类型，默认按 B2 筛词。")


def to_cefr_level(label_or_level: str) -> str:
    level = normalize_level(label_or_level)
    return level or "B2"
