from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from .export_md import rows_to_markdown
from .io_utils import read_word_set, write_rows
from .lexicon import build_lexicon
from .meanings import get_meaning
from .preprocess import extract_from_text, extract_from_words
from .scorer import score_word
from .cefr import normalize_level

InputMode = Literal["auto", "text", "words"]


@dataclass
class AnalysisResult:
    all_rows: list[dict]
    likely_unknown: list[dict]
    borderline: list[dict]
    likely_known: list[dict]
    proper_nouns: list[dict]
    summary: dict
    likely_unknown_md: str
    borderline_md: str


def detect_input_mode(content: str) -> InputMode:
    lines = [line.strip() for line in content.splitlines() if line.strip()]
    if not lines:
        return "text"
    short_lines = 0
    for line in lines[:200]:
        parts = line.split()
        if 1 <= len(parts) <= 3 and all(any(ch.isalpha() for ch in p) for p in parts):
            short_lines += 1
    return "words" if short_lines / max(1, min(len(lines), 200)) >= 0.75 else "text"


def analyze_content(
    content: str,
    user_level: str = "B2",
    input_mode: InputMode = "auto",
    cefr_backend: str = "auto",
    cefr_csv: str | Path = "data/cefr_seed.csv",
    known_path: str | Path | None = "data/known_words.txt",
    unknown_path: str | Path | None = "data/unknown_words.txt",
    known_words_extra: set[str] | None = None,
    unknown_words_extra: set[str] | None = None,
) -> AnalysisResult:
    level = normalize_level(user_level) or "B2"
    mode = detect_input_mode(content) if input_mode == "auto" else input_mode

    items = extract_from_words(content) if mode == "words" else extract_from_text(content)
    lexicon = build_lexicon(cefr_backend, cefr_csv)

    known_words = read_word_set(known_path)
    unknown_words = read_word_set(unknown_path)
    if known_words_extra:
        known_words |= {w.lower().strip() for w in known_words_extra if w.strip()}
    if unknown_words_extra:
        unknown_words |= {w.lower().strip() for w in unknown_words_extra if w.strip()}

    rows: list[dict] = []
    proper_rows: list[dict] = []

    for item in items:
        if item.is_proper:
            proper_rows.append({
                "word": item.surface,
                "lemma": item.lemma,
                "pos": item.pos,
                "reason": "proper noun / named entity",
                "sentence": item.sentence,
            })
            continue

        cefr = lexicon.get(item.lemma, item.pos)
        meaning_zh = lexicon.get_meaning(item.lemma) or get_meaning(item.lemma)
        result = score_word(item.lemma, cefr, level, known_words, unknown_words)
        rows.append({
            "word": item.surface,
            "lemma": item.lemma,
            "pos": item.pos,
            "label": result.label,
            "score": result.score,
            "cefr": result.cefr or "",
            "meaning_zh": meaning_zh,
            "zipf": f"{result.zipf:.2f}",
            "reason": result.reason,
            "sentence": item.sentence,
        })

    rows_sorted = sorted(rows, key=lambda r: (-int(r["score"]), r["lemma"]))
    likely_unknown = [r for r in rows_sorted if r["label"] == "likely_unknown"]
    borderline = [r for r in rows_sorted if r["label"] == "borderline"]
    likely_known = [r for r in rows_sorted if r["label"] == "likely_known"]
    counts = Counter(r["label"] for r in rows)
    cefr_counts = Counter((r.get("cefr") or "unknown") for r in rows)

    summary = {
        "user_level": level,
        "input_mode": mode,
        "cefr_backend": lexicon.name,
        "input_items": len(items),
        "scored_words": len(rows),
        "proper_nouns": len(proper_rows),
        "likely_unknown": counts.get("likely_unknown", 0),
        "borderline": counts.get("borderline", 0),
        "likely_known": counts.get("likely_known", 0),
        "cefr_counts": dict(cefr_counts),
    }

    return AnalysisResult(
        all_rows=rows_sorted,
        likely_unknown=likely_unknown,
        borderline=borderline,
        likely_known=likely_known,
        proper_nouns=proper_rows,
        summary=summary,
        likely_unknown_md=rows_to_markdown(likely_unknown, "建议学习词汇"),
        borderline_md=rows_to_markdown(borderline, "待确认词汇"),
    )


def write_analysis_outputs(result: AnalysisResult, out_dir: str | Path) -> None:
    out = Path(out_dir)
    write_rows(out / "all_tokens.csv", result.all_rows)
    write_rows(out / "likely_unknown.csv", result.likely_unknown)
    write_rows(out / "borderline.csv", result.borderline)
    write_rows(out / "likely_known.csv", result.likely_known)
    write_rows(out / "proper_nouns.csv", result.proper_nouns)
    (out / "likely_unknown.md").write_text(result.likely_unknown_md, encoding="utf-8")
    (out / "borderline.md").write_text(result.borderline_md, encoding="utf-8")
