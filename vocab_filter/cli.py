from __future__ import annotations
import argparse
from pathlib import Path
from collections import Counter

from .cefr import normalize_level
from .pipeline import analyze_content, write_analysis_outputs


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Rule-based personal English unknown-word filter.")
    src = parser.add_mutually_exclusive_group(required=True)
    src.add_argument("--text", help="Path to an English article/text file.")
    src.add_argument("--words", help="Path to a plain word list file.")
    parser.add_argument("--level", default="B2", help="User CEFR level: A1/A2/B1/B2/C1/C2.")
    parser.add_argument("--cefr", default="data/cefr_seed.csv", help="CSV fallback path with columns word,level.")
    parser.add_argument("--backend", default="auto", choices=["auto", "cefrpy", "csv"], help="CEFR backend. auto/cefrpy use Maximax67 cefrpy when installed, CSV as fallback.")
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
    result = analyze_content(
        raw,
        user_level=user_level,
        input_mode="text" if args.text else "words",
        cefr_backend=args.backend,
        cefr_csv=args.cefr,
        known_path=args.known,
        unknown_path=args.unknown,
    )
    write_analysis_outputs(result, args.out)

    print("vocab-filter done")
    for key, value in result.summary.items():
        if key != "cefr_counts":
            print(f"{key}: {value}")
    print(f"output_dir: {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
