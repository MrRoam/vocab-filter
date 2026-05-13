from __future__ import annotations
from dataclasses import dataclass
from typing import Iterable
import os
import re

TOKEN_RE = re.compile(r"[A-Za-z]+(?:[-'][A-Za-z]+)?")
ROMAN_NUMERAL_RE = re.compile(r"(?i)^(?=[mdclxvi]+$)m{0,4}(cm|cd|d?c{0,3})(xc|xl|l?x{0,3})(ix|iv|v?i{0,3})$")
ROMAN_WORD_EXCEPTIONS = {"mix"}

@dataclass
class WordItem:
    surface: str
    lemma: str
    sentence: str = ""
    is_proper: bool = False
    pos: str = ""


def extract_from_words(raw: str) -> list[WordItem]:
    return dedupe_keep_first(
        WordItem(m.group(0), normalize_word(m.group(0)), pos="")
        for m in TOKEN_RE.finditer(raw)
        if not should_skip_token(m.group(0), raw)
    )


def extract_from_text(text: str) -> list[WordItem]:
    if os.getenv("VOCAB_FILTER_NO_SPACY") == "1":
        return _regex_extract_from_text(text)
    try:
        import spacy  # type: ignore
        try:
            nlp = spacy.load("en_core_web_sm")
        except Exception:
            nlp = spacy.blank("en")
            nlp.add_pipe("sentencizer")
        doc = nlp(text)
        items: list[WordItem] = []
        for sent in doc.sents:
            sent_text = sent.text.strip()
            for token in sent:
                if not token.text or not TOKEN_RE.fullmatch(token.text):
                    continue
                if should_skip_token(token.text, sent_text):
                    continue
                if getattr(token, "is_stop", False):
                    continue
                lemma = token.lemma_.lower().strip() if token.lemma_ and token.lemma_ != "-PRON-" else simple_lemma(token.text)
                if lemma == token.text.lower().strip():
                    lemma = simple_lemma(token.text)
                if len(lemma) <= 1:
                    continue
                ent = getattr(token, "ent_type_", "")
                is_proper = ent in {"PERSON", "GPE", "ORG", "PRODUCT", "WORK_OF_ART", "NORP", "LOC", "LANGUAGE"}
                is_proper = is_proper or looks_like_proper(token.text, sent_text)
                pos = getattr(token, "tag_", "") or getattr(token, "pos_", "") or ""
                items.append(WordItem(token.text, lemma, sent_text, is_proper, pos))
        return dedupe_keep_first(items)
    except Exception:
        return _regex_extract_from_text(text)


def _regex_extract_from_text(text: str) -> list[WordItem]:
    sentences = re.split(r"(?<=[.!?])\s+", text)
    items: list[WordItem] = []
    for sent in sentences:
        for m in TOKEN_RE.finditer(sent):
            surface = m.group(0)
            if should_skip_token(surface, sent):
                continue
            lemma = simple_lemma(surface)
            if len(lemma) <= 1 or lemma in BASIC_STOPWORDS:
                continue
            items.append(WordItem(surface, lemma, sent.strip(), looks_like_proper(surface, sent), ""))
    return dedupe_keep_first(items)


def looks_like_proper(surface: str, sentence: str) -> bool:
    # ALLCAPS or camel-case terms such as NVIDIA / OpenAI are likely named entities,
    # even when they appear at the beginning of a sentence.
    if surface.isupper() and len(surface) > 1:
        return True
    if any(ch.isupper() for ch in surface[1:]):
        return True
    if surface[:1].isupper() and not sentence.lstrip().startswith(surface):
        return True
    return False


def should_skip_token(surface: str, context: str = "") -> bool:
    """Drop OCR/page-code fragments that are not useful vocabulary targets."""
    text = surface.strip()
    if len(text) <= 1:
        return True
    lowered = text.lower()
    if lowered not in ROMAN_WORD_EXCEPTIONS and ROMAN_NUMERAL_RE.fullmatch(lowered):
        return True
    if text.isupper() and len(text) <= 3:
        return True
    if lowered in {"contents", "chapter", "section", "page", "fig", "figure", "table"}:
        return True
    return False


def simple_lemma(word: str) -> str:
    w = word.lower().strip("'")
    irregular = {
        "was": "be", "were": "be", "is": "be", "are": "be", "am": "be",
        "been": "be", "being": "be", "has": "have", "had": "have",
        "does": "do", "did": "do", "went": "go", "gone": "go",
        "ran": "run", "written": "write", "wrote": "write",
    }
    if w in irregular:
        return irregular[w]
    if len(w) > 5 and w.endswith("ies"):
        return w[:-3] + "y"
    if len(w) > 5 and w.endswith("ing"):
        base = w[:-3]
        if len(base) > 2 and base[-1] == base[-2]:
            base = base[:-1]
        if base.endswith(("at", "iz")):
            return base + "e"
        return base
    if len(w) > 4 and w.endswith("ed"):
        base = w[:-2]
        if len(base) > 2 and base[-1] == base[-2]:
            base = base[:-1]
        if w.endswith("ied") and len(w) > 4:
            return w[:-3] + "y"
        if w.endswith("ated") and len(w) > 6:
            return base + "e"
        # Conservative repair for verbs like released -> release,
        # derived -> derive, argued -> argue, balanced -> balance.
        if base.endswith(("s", "v", "u", "c", "g")) and not base.endswith("ss"):
            return base + "e"
        return base
    if len(w) > 5 and w.endswith(("ches", "shes", "xes", "zes", "sses")):
        return w[:-2]
    if len(w) > 4 and w.endswith("s") and not w.endswith(("ss", "us", "ous", "is", "ics")):
        return w[:-1]
    return w


def normalize_word(word: str) -> str:
    return word.lower().strip("'")


def dedupe_keep_first(items: Iterable[WordItem]) -> list[WordItem]:
    seen = set()
    out: list[WordItem] = []
    for item in items:
        if len(item.lemma) <= 1 or should_skip_token(item.surface, item.sentence):
            continue
        key = item.lemma.lower()
        if key in seen:
            continue
        seen.add(key)
        out.append(item)
    return out


BASIC_STOPWORDS = {
    "the", "be", "and", "of", "to", "a", "in", "that", "have", "i", "it", "for",
    "not", "on", "with", "he", "as", "you", "do", "at", "this", "but", "his",
    "by", "from", "they", "we", "say", "her", "she", "or", "an", "will", "my",
    "one", "all", "would", "there", "their", "what", "so", "up", "out", "if",
    "about", "who", "get", "which", "go", "me", "when", "make", "can", "like",
    "for", "most", "may", "between", "however",
}
