from __future__ import annotations

from functools import lru_cache
from pathlib import Path
import csv


@lru_cache(maxsize=8)
def load_meanings(path: str | Path = "data/word_meanings_zh.csv") -> dict[str, str]:
    p = Path(path)
    if not p.exists():
        return {}

    meanings: dict[str, str] = {}
    with p.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        fields = {name.lower(): name for name in (reader.fieldnames or [])}
        word_col = next((fields[x] for x in ["word", "lemma", "term", "headword"] if x in fields), None)
        meaning_col = next(
            (fields[x] for x in ["meaning_zh", "zh", "chinese", "translation", "definition_zh"] if x in fields),
            None,
        )
        if not word_col or not meaning_col:
            return meanings
        for row in reader:
            word = (row.get(word_col) or "").strip().lower()
            meaning = (row.get(meaning_col) or "").strip()
            if word and meaning:
                meanings[word] = meaning
    return meanings


def get_meaning(word: str, path: str | Path = "data/word_meanings_zh.csv") -> str:
    return load_meanings(path).get(word.lower().strip(), "")
