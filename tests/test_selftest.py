from vocab_filter.scorer import score_word
from vocab_filter.preprocess import extract_from_words, simple_lemma
from vocab_filter.pipeline import analyze_content
from vocab_filter.meanings import get_meaning


def test_serendipitous_not_overstemmed():
    assert simple_lemma("serendipitous") == "serendipitous"


def test_common_edge_lemmas():
    assert simple_lemma("released") == "release"
    assert simple_lemma("allied") == "ally"
    assert simple_lemma("complicated") == "complicate"
    assert simple_lemma("acclimating") == "acclimate"
    assert simple_lemma("anthropomorphizing") == "anthropomorphize"
    assert simple_lemma("attaches") == "attach"
    assert simple_lemma("robotics") == "robotics"
    assert simple_lemma("mix") == "mix"


def test_word_list_keeps_original_words():
    items = extract_from_words("allied\ncomplicated")
    assert [(item.surface, item.lemma) for item in items] == [
        ("allied", "allied"),
        ("complicated", "complicated"),
    ]


def test_text_extraction_repairs_identity_lemmas():
    items = extract_from_words("acclimating")
    assert [(item.surface, item.lemma) for item in items] == [("acclimating", "acclimating")]
    result = analyze_content(
        "Astronauts are acclimating in the airlock.",
        user_level="B2",
        input_mode="text",
        cefr_backend="auto",
        cefr_csv="data/cefr_seed.csv",
    )
    assert any(row["lemma"] == "acclimate" for row in result.all_rows)


def test_ocr_page_noise_is_skipped():
    result = analyze_content(
        "xv xv Contents xv 8.4.1 XB intricate mechanism was ubiquitous.",
        user_level="B2",
        input_mode="text",
        cefr_backend="csv",
        cefr_csv="data/cefr_seed.csv",
    )
    lemmas = {row["lemma"] for row in result.all_rows}
    assert "xv" not in lemmas
    assert "xb" not in lemmas
    assert "intricate" in lemmas


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
    markdown_lines = result.likely_unknown_md.splitlines()
    assert "intricate" in markdown_lines
    assert "待学习词汇" not in result.likely_unknown_md
    assert all(not line.startswith(("#", "-")) for line in markdown_lines)


def test_extra_chinese_meanings_are_used():
    assert "气闸" in get_meaning("airlock")


def test_missing_cefr_words_are_separated():
    result = analyze_content(
        "The airlock hissed.",
        user_level="B2",
        input_mode="text",
        cefr_backend="csv",
        cefr_csv="data/cefr_seed.csv",
    )
    assert any(row["lemma"] == "airlock" for row in result.ungraded)
    assert not any(row["lemma"] == "airlock" for row in result.likely_unknown)
