from __future__ import annotations
from functools import lru_cache

COMMON_ZIPF = {
    "house": 5.2, "book": 5.1, "student": 4.7, "word": 4.8, "need": 5.2,
    "new": 5.5, "release": 4.5, "article": 4.5, "learn": 5.0, "learning": 4.8,
    "important": 4.7, "simple": 4.4, "reason": 4.5, "process": 4.4,
    "context": 4.0, "confirm": 3.8, "filter": 3.7, "recognize": 3.8,
    "derive": 4.0, "hypothesis": 3.8, "reinforcement": 3.1,
    "optimization": 3.2, "trajectory": 3.4, "inference": 3.4,
    "dataset": 3.7, "policy": 4.3, "robotics": 3.6,
    "stumble": 3.3, "linger": 3.1, "intricate": 3.2,
    "ubiquitous": 3.0, "meticulous": 2.8, "serendipitous": 2.4,
    "defenestration": 1.8, "efficient": 4.0, "complex": 4.2,
    "balance": 4.1, "exploration": 3.5, "attention": 4.3,
    "demo": 3.8, "argue": 4.0, "depend": 4.2, "extra": 4.2,
}

@lru_cache(maxsize=20000)
def zipf_frequency(word: str) -> float:
    word = word.lower().strip()
    try:
        from wordfreq import zipf_frequency as real_zipf_frequency  # type: ignore
        return float(real_zipf_frequency(word, "en"))
    except Exception:
        return fallback_zipf(word)

def fallback_zipf(word: str) -> float:
    if not word:
        return 0.0
    if word in COMMON_ZIPF:
        return COMMON_ZIPF[word]
    if len(word) <= 3:
        return 4.0
    if len(word) <= 6:
        return 3.6
    if len(word) <= 9:
        return 3.1
    return 2.7
