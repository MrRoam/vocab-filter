from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
from typing import Optional
import csv

LEVELS = ["A1", "A2", "B1", "B2", "C1", "C2"]
LEVEL_ORDER = {level: i + 1 for i, level in enumerate(LEVELS)}

def normalize_level(value: str | None) -> Optional[str]:
    if not value:
        return None
    v = value.strip().upper()
    return v if v in LEVEL_ORDER else None

@dataclass
class CEFRLexicon:
    mapping: dict[str, str]

    @classmethod
    def load(cls, path: str | Path) -> "CEFRLexicon":
        p = Path(path)
        if not p.exists():
            return cls({})
        mapping: dict[str, str] = {}
        with p.open("r", encoding="utf-8-sig", newline="") as f:
            reader = csv.DictReader(f)
            fields = {name.lower(): name for name in (reader.fieldnames or [])}
            word_col = next((fields[x] for x in ["word", "lemma", "term", "headword"] if x in fields), None)
            level_col = next((fields[x] for x in ["level", "cefr", "cefr_level"] if x in fields), None)
            if not word_col or not level_col:
                raise ValueError("CEFR CSV must contain word/lemma and level/cefr columns.")
            for row in reader:
                word = (row.get(word_col) or "").strip().lower()
                level = normalize_level(row.get(level_col))
                if word and level:
                    mapping[word] = level
        return cls(mapping)

    def get(self, word: str) -> Optional[str]:
        return self.mapping.get(word.lower().strip())
