from __future__ import annotations
from dataclasses import dataclass
from typing import Iterable
import os
import re

TOKEN_RE = re.compile(r"[A-Za-z]+(?:'[A-Za-z]+)?")

@dataclass
class WordItem:
    surface: str
    lemma: str
    sentence: str = ""
    is_proper: bool = False

def extract_from_words(raw: str) -> list[WordItem]:
    return dedupe_keep_first(
        WordItem(m.group(0), simple_lemma(m.group(0))) for m in TOKEN_RE.finditer(raw)
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
        items = []
        for sent in doc.sents:
            sent_text = sent.text.strip()
            for token in sent:
                if not token.text or not TOKEN_RE.fullmatch(token.text):
                    continue
                if getattr(token, "is_stop", False):
                    continue
                lemma = token.lemma_.lower().strip() if token.lemma_ and token.lemma_ != "-PRON-" else simple_lemma(token.text)
                if len(lemma) <= 1:
                    continue
                ent = getattr(token, "ent_type_", "")
                is_proper = ent in {"PERSON", "GPE", "ORG", "PRODUCT", "WORK_OF_ART", "NORP", "LOC"}
                is_proper = is_proper or looks_like_proper(token.text, sent_text)
                items.append(WordItem(token.text, lemma, sent_text, is_proper))
        return dedupe_keep_first(items)
    except Exception:
        return _regex_extract_from_text(text)

def _regex_extract_from_text(text: str) -> list[WordItem]:
    sentences = re.split(r"(?<=[.!?])\s+", text)
    items = []
    for sent in sentences:
        for m in TOKEN_RE.finditer(sent):
            surface = m.group(0)
            lemma = simple_lemma(surface)
            if len(lemma) <= 1 or lemma in BASIC_STOPWORDS:
                continue
            items.append(WordItem(surface, lemma, sent.strip(), looks_like_proper(surface, sent)))
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
        return base
    if len(w) > 4 and w.endswith("ed"):
        base = w[:-2]
        if len(base) > 2 and base[-1] == base[-2]:
            base = base[:-1]
        # Conservative repair for verbs like released -> release,
        # derived -> derive, argued -> argue, balanced -> balance.
        if base.endswith(("s", "v", "u", "c", "g")) and not base.endswith("ss"):
            return base + "e"
        return base
    if (
        len(w) > 4
        and w.endswith("s")
        and not w.endswith(("ss", "us", "ous", "is", "ics"))
    ):
        return w[:-1]
    return w

def dedupe_keep_first(items: Iterable[WordItem]) -> list[WordItem]:
    seen = set()
    out = []
    for item in items:
        if len(item.lemma) <= 1:
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
