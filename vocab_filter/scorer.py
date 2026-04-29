from __future__ import annotations
from dataclasses import dataclass
from typing import Optional
from .cefr import LEVEL_ORDER, normalize_level
from .frequency import zipf_frequency

@dataclass
class ScoreResult:
    score: int
    label: str
    cefr: Optional[str]
    zipf: float
    reason: str

def score_word(lemma: str, cefr: Optional[str], user_level: str, known_words: set[str], unknown_words: set[str]) -> ScoreResult:
    lemma = lemma.lower()
    user_level = normalize_level(user_level) or "B2"
    freq = zipf_frequency(lemma)

    if lemma in known_words:
        return ScoreResult(0, "likely_known", cefr, freq, "in known_words")
    if lemma in unknown_words:
        return ScoreResult(100, "likely_unknown", cefr, freq, "in unknown_words")

    word_level_num = LEVEL_ORDER.get(cefr or "", LEVEL_ORDER["C1"])
    user_level_num = LEVEL_ORDER[user_level]
    score = 50 + (word_level_num - user_level_num) * 20
    reasons = []

    if cefr:
        if word_level_num > user_level_num:
            reasons.append(f"level {cefr} is above user level {user_level}")
        elif word_level_num == user_level_num:
            reasons.append(f"level {cefr} matches user level {user_level}")
        else:
            reasons.append(f"level {cefr} is below user level {user_level}")
    else:
        reasons.append("CEFR level missing; treated as advanced unless frequency is high")

    if freq >= 5.0:
        score -= 20
        reasons.append(f"very common word, zipf={freq:.2f}")
    elif freq >= 4.0:
        score -= 10
        reasons.append(f"common word, zipf={freq:.2f}")
    elif freq < 3.0:
        score += 15
        reasons.append(f"low-frequency word, zipf={freq:.2f}")
    else:
        reasons.append(f"medium/low frequency, zipf={freq:.2f}")

    score = max(0, min(100, round(score)))
    return ScoreResult(score, classify(score), cefr, freq, "; ".join(reasons))

def classify(score: int) -> str:
    if score >= 65:
        return "likely_unknown"
    if score >= 40:
        return "borderline"
    return "likely_known"
