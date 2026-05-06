from vocab_filter.scorer import score_word
from vocab_filter.preprocess import simple_lemma
from vocab_filter.pipeline import analyze_content


def test_serendipitous_not_overstemmed():
    assert simple_lemma("serendipitous") == "serendipitous"


def test_common_edge_lemmas():
    assert simple_lemma("released") == "release"
    assert simple_lemma("robotics") == "robotics"


def test_known_overrides_level():
    assert score_word("meticulous", "C1", "B2", {"meticulous"}, set()).label == "likely_known"


def test_unknown_overrides_level():
    assert score_word("house", "A1", "B2", set(), {"house"}).label == "likely_unknown"


def test_c1_for_b2_is_unknown():
    assert score_word("intricate", "C1", "B2", set(), set()).label == "likely_unknown"


def test_pipeline_outputs_markdown():
    result = analyze_content(
        "The intricate mechanism was ubiquitous.",
        user_level="B2",
        input_mode="text",
        cefr_backend="csv",
        cefr_csv="data/cefr_seed.csv",
    )
    assert any(row["lemma"] == "intricate" for row in result.likely_unknown)
    assert "# 建议学习词汇" in result.likely_unknown_md
