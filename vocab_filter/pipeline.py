from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal
from collections import Counter

from .cefr import CEFRLexicon, normalize_level
from .io_utils import read_word_set
from .preprocess import WordItem, extract_from_text, extract_from_words
from .scorer import score_word

InputMode = Literal["auto", "text", "words"]

LEVEL_PRESETS = {
    "四级 425-500": "B1",
    "四级 500+": "B2",
    "六级 425-500": "B2",
    "六级 500+": "B2",
    "IELTS 5.5": "B1",
    "IELTS 6.0": "B2",
    "IELTS 6.5": "B2",
    "IELTS 7.0": "C1",
    "高中英语": "B1",
    "直接选择 A1": "A1",
    "直接选择 A2": "A2",
    "直接选择 B1": "B1",
    "直接选择 B2": "B2",
    "直接选择 C1": "C1",
    "直接选择 C2": "C2",
}


@dataclass
class AnalysisResult:
    rows: list[dict]
    proper_rows: list[dict]
    user_level: str

    @property
    def likely_unknown(self) -> list[dict]:
        return [r for r in self.rows if r["label"] == "likely_unknown"]

    @property
    def borderline(self) -> list[dict]:
        return [r for r in self.rows if r["label"] == "borderline"]

    @property
    def likely_known(self) -> list[dict]:
        return [r for r in self.rows if r["label"] == "likely_known"]

    @property
    def summary(self) -> dict[str, int | str]:
        c = Counter(r["label"] for r in self.rows)
        return {
            "user_level": self.user_level,
            "scored_words": len(self.rows),
            "proper_nouns": len(self.proper_rows),
            "likely_unknown": c.get("likely_unknown", 0),
            "borderline": c.get("borderline", 0),
            "likely_known": c.get("likely_known", 0),
        }


def resolve_user_level(value: str) -> str:
    if value in LEVEL_PRESETS:
        return LEVEL_PRESETS[value]
    level = normalize_level(value)
    if level:
        return level
    return "B2"


def guess_input_mode(raw: str) -> Literal["text", "words"]:
    lines = [line.strip() for line in raw.splitlines() if line.strip()]
    if not lines:
        return "text"
    short_lines = sum(1 for line in lines if len(line.split()) <= 3)
    return "words" if short_lines / len(lines) >= 0.75 else "text"


def analyze_content(
    raw: str,
    user_level: str = "B2",
    mode: InputMode = "auto",
    cefr_path: str | Path | None = None,
    known_path: str | Path | None = None,
    unknown_path: str | Path | None = None,
    known_words: set[str] | None = None,
    unknown_words: set[str] | None = None,
) -> AnalysisResult:
    level = resolve_user_level(user_level)
    actual_mode = guess_input_mode(raw) if mode == "auto" else mode

    items = extract_from_words(raw) if actual_mode == "words" else extract_from_text(raw)

    lexicon = CEFRLexicon.load(cefr_path or "") if cefr_path else CEFRLexicon.load("data/cefr_seed.csv")
    known = set(known_words or set()) | read_word_set(known_path)
    unknown = set(unknown_words or set()) | read_word_set(unknown_path)

    rows: list[dict] = []
    proper_rows: list[dict] = []

    for item in items:
        if item.is_proper:
            proper_rows.append(
                {
                    "word": item.surface,
                    "lemma": item.lemma,
                    "reason": "proper noun / named entity",
                    "sentence": item.sentence,
                }
            )
            continue

        cefr = lexicon.get(item.lemma)
        result = score_word(item.lemma, cefr, level, known, unknown)
        rows.append(
            {
                "word": item.surface,
                "lemma": item.lemma,
                "label": result.label,
                "score": result.score,
                "cefr": result.cefr or "",
                "zipf": f"{result.zipf:.2f}",
                "reason": result.reason,
                "sentence": item.sentence,
            }
        )

    rows_sorted = sorted(rows, key=lambda r: (-int(r["score"]), r["lemma"]))
    return AnalysisResult(rows=rows_sorted, proper_rows=proper_rows, user_level=level)
