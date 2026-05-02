from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from .cefr import CEFRLexicon, normalize_level


class BaseLexicon:
    name: str = "base"

    def get(self, word: str, pos: str = "") -> Optional[str]:
        raise NotImplementedError

    def available(self) -> bool:
        return True


@dataclass
class CSVLexicon(BaseLexicon):
    csv_path: str | Path
    name: str = "csv"

    def __post_init__(self) -> None:
        self.lexicon = CEFRLexicon.load(self.csv_path)

    def get(self, word: str, pos: str = "") -> Optional[str]:
        return self.lexicon.get(word)

    def available(self) -> bool:
        return bool(self.lexicon.mapping)


class CefrPyLexicon(BaseLexicon):
    """Adapter around Maximax67/cefrpy.

    cefrpy wraps the Words-CEFR-Dataset and can return CEFR levels for A1-C2.
    The dependency is optional so the project still runs with a local CSV fallback.
    """

    name = "cefrpy"

    def __init__(self) -> None:
        try:
            from cefrpy import CEFRAnalyzer  # type: ignore
        except Exception as exc:
            raise ImportError("Install cefrpy with: pip install cefrpy") from exc
        self.analyzer = CEFRAnalyzer()

    def get(self, word: str, pos: str = "") -> Optional[str]:
        word = word.lower().strip()
        if not word:
            return None

        # Prefer POS-specific lookup when spaCy provided a Penn Treebank tag.
        if pos:
            try:
                level = self.analyzer.get_word_pos_level_CEFR(word, pos)
                level = _coerce_cefr(level)
                if level:
                    return level
            except Exception:
                pass

        # Fallback to average word level.
        try:
            level = self.analyzer.get_average_word_level_CEFR(word)
            return _coerce_cefr(level)
        except Exception:
            return None


def _coerce_cefr(value: object) -> Optional[str]:
    if value is None:
        return None
    text = str(value).strip().upper()
    # cefrpy CEFRLevel values generally stringify as A1/B2/etc.
    for level in ["A1", "A2", "B1", "B2", "C1", "C2"]:
        if level in text:
            return level
    return normalize_level(text)


class CompositeLexicon(BaseLexicon):
    """Try multiple CEFR backends in order."""

    def __init__(self, backends: list[BaseLexicon]) -> None:
        self.backends = backends
        self.name = "+".join([b.name for b in backends]) if backends else "none"

    def get(self, word: str, pos: str = "") -> Optional[str]:
        for backend in self.backends:
            level = backend.get(word, pos)
            if level:
                return level
        return None

    def available(self) -> bool:
        return any(b.available() for b in self.backends)


def build_lexicon(
    backend: str = "auto",
    cefr_csv: str | Path = "data/cefr_seed.csv",
) -> BaseLexicon:
    """Build the requested CEFR lexicon.

    backend:
      - auto: cefrpy first, CSV fallback
      - cefrpy: cefrpy only, CSV fallback if cefrpy import fails
      - csv: CSV only
    """
    backend = (backend or "auto").lower()
    csv_backend = CSVLexicon(cefr_csv)

    if backend == "csv":
        return csv_backend

    try:
        cefrpy_backend = CefrPyLexicon()
    except ImportError:
        return csv_backend

    if backend == "cefrpy":
        return CompositeLexicon([cefrpy_backend, csv_backend])

    return CompositeLexicon([cefrpy_backend, csv_backend])
