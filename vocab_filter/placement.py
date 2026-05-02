from __future__ import annotations

from collections import defaultdict
from pathlib import Path
import csv
import random

LEVELS = ["A1", "A2", "B1", "B2", "C1", "C2"]


def load_test_words(path: str | Path = "data/placement_test_words.csv") -> dict[str, list[str]]:
    p = Path(path)
    data: dict[str, list[str]] = {level: [] for level in LEVELS}
    if not p.exists():
        return data
    with p.open("r", encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            level = (row.get("level") or "").strip().upper()
            word = (row.get("word") or "").strip().lower()
            if level in data and word:
                data[level].append(word)
    return data


def sample_test_words(per_level: int = 8, seed: int | None = None) -> list[dict]:
    rng = random.Random(seed)
    data = load_test_words()
    rows: list[dict] = []
    for level in LEVELS:
        words = list(data.get(level, []))
        rng.shuffle(words)
        for word in words[:per_level]:
            rows.append({"word": word, "level": level})
    rng.shuffle(rows)
    return rows


def estimate_level(responses: list[dict]) -> dict:
    # response: {word, level, answer}, answer in know/blur/unknown
    score_by_level: dict[str, list[float]] = defaultdict(list)
    value = {"认识": 1.0, "模糊": 0.5, "不认识": 0.0, "know": 1.0, "blur": 0.5, "unknown": 0.0}
    for row in responses:
        level = row.get("level")
        answer = row.get("answer")
        if level in LEVELS and answer in value:
            score_by_level[level].append(value[answer])

    rates = {}
    for level in LEVELS:
        vals = score_by_level.get(level, [])
        rates[level] = round(sum(vals) / len(vals), 2) if vals else 0.0

    suggested = "A1"
    for level in LEVELS:
        if rates[level] >= 0.7:
            suggested = level

    # If the next level is close, use it as the filtering level so output is less noisy.
    idx = LEVELS.index(suggested)
    if idx + 1 < len(LEVELS) and rates[LEVELS[idx + 1]] >= 0.55:
        suggested = LEVELS[idx + 1]

    return {"rates": rates, "suggested_level": suggested}
