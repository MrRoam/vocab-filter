from vocab_filter.scorer import score_word
from vocab_filter.preprocess import simple_lemma

def test_serendipitous_not_overstemmed():
    assert simple_lemma("serendipitous") == "serendipitous"

def test_known_overrides_level():
    assert score_word("meticulous", "C1", "B2", {"meticulous"}, set()).label == "likely_known"

def test_unknown_overrides_level():
    assert score_word("house", "A1", "B2", set(), {"house"}).label == "likely_unknown"

def test_c1_for_b2_is_unknown():
    assert score_word("intricate", "C1", "B2", set(), set()).label == "likely_unknown"


def test_common_edge_lemmas():
    assert simple_lemma("released") == "release"
    assert simple_lemma("robotics") == "robotics"
