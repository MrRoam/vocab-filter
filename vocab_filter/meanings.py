from __future__ import annotations

from functools import lru_cache
from pathlib import Path
import csv


DEFAULT_MEANING_PATHS = (
    Path("data/ecdict.csv"),
    Path("data/word_meanings_extra_zh.csv"),
    Path("data/word_meanings_zh.csv"),
)


@lru_cache(maxsize=8)
def load_meanings(path: str | Path = "data/word_meanings_zh.csv") -> dict[str, str]:
    p = Path(path)
    if not p.exists():
        return {}

    meanings: dict[str, str] = {}
    with _open_text_csv(p) as f:
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


def _open_text_csv(path: Path):
    for encoding in ("utf-8-sig", "gb18030"):
        try:
            with path.open("r", encoding=encoding, newline="") as probe:
                probe.read(8192)
            return path.open("r", encoding=encoding, errors="replace", newline="")
        except UnicodeDecodeError:
            continue
    return path.open("r", encoding="utf-8-sig", errors="replace", newline="")


@lru_cache(maxsize=1)
def load_default_meanings() -> dict[str, str]:
    meanings: dict[str, str] = {}
    for path in reversed(DEFAULT_MEANING_PATHS):
        meanings.update(load_meanings(path))
    return meanings


def get_meaning(word: str, path: str | Path = "data/word_meanings_zh.csv") -> str:
    word = word.lower().strip()
    if str(path) == "data/word_meanings_zh.csv":
        return load_default_meanings().get(word, "")
    return load_meanings(path).get(word, "")
