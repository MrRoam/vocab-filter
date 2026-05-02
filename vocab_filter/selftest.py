from __future__ import annotations
from .scorer import score_word
from .preprocess import simple_lemma

def main() -> int:
    assert simple_lemma("serendipitous") == "serendipitous"
    assert simple_lemma("released") == "release"
    assert simple_lemma("robotics") == "robotics"
    assert score_word("ubiquitous", "C1", "B2", {"ubiquitous"}, set()).label == "likely_known"
    assert score_word("linger", "B2", "B2", set(), {"linger"}).label == "likely_unknown"
    assert score_word("meticulous", "C1", "B2", set(), set()).label == "likely_unknown"
    assert score_word("house", "A1", "B2", set(), set()).label == "likely_known"
    print("selftest passed")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
