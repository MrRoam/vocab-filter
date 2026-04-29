from __future__ import annotations
import argparse
from pathlib import Path
from collections import Counter
from .cefr import CEFRLexicon, normalize_level
from .preprocess import extract_from_text, extract_from_words
from .scorer import score_word
from .io_utils import read_word_set, write_rows

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Rule-based personal English unknown-word filter.")
    src = parser.add_mutually_exclusive_group(required=True)
    src.add_argument("--text", help="Path to an English article/text file.")
    src.add_argument("--words", help="Path to a plain word list file.")
    parser.add_argument("--level", default="B2", help="User CEFR level: A1/A2/B1/B2/C1/C2.")
    parser.add_argument("--cefr", default="data/cefr_seed.csv", help="Path to CEFR CSV.")
    parser.add_argument("--known", default="data/known_words.txt", help="Path to known words.")
    parser.add_argument("--unknown", default="data/unknown_words.txt", help="Path to unknown words.")
    parser.add_argument("--out", default="output", help="Output directory.")
    return parser

def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    user_level = normalize_level(args.level)
    if not user_level:
        raise SystemExit(f"Invalid --level {args.level!r}. Use A1/A2/B1/B2/C1/C2.")

    raw = Path(args.text or args.words).read_text(encoding="utf-8")
    items = extract_from_text(raw) if args.text else extract_from_words(raw)
    lexicon = CEFRLexicon.load(args.cefr)
    known_words = read_word_set(args.known)
    unknown_words = read_word_set(args.unknown)

    rows, proper_rows = [], []
    for item in items:
        if item.is_proper:
            proper_rows.append({"word": item.surface, "lemma": item.lemma, "reason": "proper noun / named entity", "sentence": item.sentence})
            continue
        cefr = lexicon.get(item.lemma)
        result = score_word(item.lemma, cefr, user_level, known_words, unknown_words)
        rows.append({
            "word": item.surface,
            "lemma": item.lemma,
            "label": result.label,
            "score": result.score,
            "cefr": result.cefr or "",
            "zipf": f"{result.zipf:.2f}",
            "reason": result.reason,
            "sentence": item.sentence,
        })

    rows_sorted = sorted(rows, key=lambda r: (-int(r["score"]), r["lemma"]))
    out = Path(args.out)
    write_rows(out / "all_tokens.csv", rows_sorted)
    write_rows(out / "likely_unknown.csv", [r for r in rows_sorted if r["label"] == "likely_unknown"])
    write_rows(out / "borderline.csv", [r for r in rows_sorted if r["label"] == "borderline"])
    write_rows(out / "likely_known.csv", [r for r in rows_sorted if r["label"] == "likely_known"])
    write_rows(out / "proper_nouns.csv", proper_rows)

    c = Counter(r["label"] for r in rows)
    print("vocab-filter done")
    print(f"user_level: {user_level}")
    print(f"input_items: {len(items)}")
    print(f"scored_words: {len(rows)}")
    print(f"proper_nouns: {len(proper_rows)}")
    print(f"likely_unknown: {c.get('likely_unknown', 0)}")
    print(f"borderline: {c.get('borderline', 0)}")
    print(f"likely_known: {c.get('likely_known', 0)}")
    print(f"output_dir: {out}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
