"""
deslop test suite — synthetic samples only (no third-party / copyrighted text).

Run from anywhere:
    pytest -q
"""

import os
import sys

# Make the repo root importable regardless of where pytest is invoked.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import engine  # noqa: E402
import deslop  # noqa: E402


# --- synthetic corpora (all written for this repo; safe to publish) ----------

KO_AI = [
    "이 제품은 혁신적인 솔루션을 통해 사용자 경험을 극대화하고, 지속적으로 가치를 "
    "제공함으로써 패러다임을 전환합니다. 결론적으로, 이는 시사하는 바가 큽니다.",
    "본 연구는 다양한 요인을 종합적으로 분석하여 효율적인 프레임워크를 제시하고자 "
    "합니다. 또한, 이러한 접근은 향후 발전 가능성을 시사합니다.",
]

KO_HUMAN = [
    "어제 동네 책방 갔다가 표지 예뻐서 산 책인데 첫 장부터 좀 졸렸다. 그래도 끝까진 봐야지.",
    "비 와서 우산 챙겼는데 깜빡하고 지하철에 두고 내렸다. 새로 산 건데. 아 진짜.",
    "엄마가 김치 보냈다. 박스 여니까 국물 좀 샜더라. 그래도 맛은 똑같다.",
]

EN_AI = [
    "This innovative solution leverages cutting-edge technology to seamlessly transform "
    "productivity and empower teams. Ultimately, it represents a groundbreaking paradigm shift.",
]

EN_HUMAN = [
    "I grabbed this book because the cover looked nice, but the first chapter dragged. "
    "Still, I keep carrying it around.",
    "Left my umbrella on the train again. Brand new one too. Of course it started "
    "raining the second I got out.",
]


def _avg(xs):
    return sum(xs) / len(xs)


# --- detection separates clear AI from clear human ---------------------------

def test_ko_clear_ai_scores_high():
    for t in KO_AI:
        assert engine.detect_ko(t).ai_score > 40

def test_ko_human_scores_low():
    for t in KO_HUMAN:
        assert engine.detect_ko(t).ai_score < 20

def test_en_human_scores_low():
    for t in EN_HUMAN:
        assert engine.detect_en(t).ai_score < 20

def test_ko_separation_is_meaningful():
    ai = _avg([engine.detect_ko(t).ai_score for t in KO_AI])
    hu = _avg([engine.detect_ko(t).ai_score for t in KO_HUMAN])
    assert ai - hu > 30

def test_en_separation_is_meaningful():
    ai = _avg([engine.detect_en(t).ai_score for t in EN_AI])
    hu = _avg([engine.detect_en(t).ai_score for t in EN_HUMAN])
    assert ai - hu > 25


# --- humanize never raises the score; human text is left ~untouched ----------

def test_humanize_does_not_raise_score():
    for t in KO_AI + KO_HUMAN:
        r = engine.humanize_ko(t)
        assert r.metrics_after.ai_score <= r.metrics_before.ai_score
    for t in EN_AI + EN_HUMAN:
        r = engine.humanize_en(t)
        assert r.metrics_after.ai_score <= r.metrics_before.ai_score

def test_safe_auto_no_false_positive_on_human():
    # Deterministic auto-replace should not edit clean human prose.
    for t in KO_HUMAN:
        r = engine.humanize_ko(t)
        assert len(r.safe_auto_changes) == 0


# --- public API contract (deslop.py, offline) --------------------------------

def test_humanize_dict_keys():
    r = deslop.humanize(KO_AI[0])
    for k in ("raw", "lang", "text_type", "transformed_text", "safe_auto",
              "flags", "progress", "ai_score_before", "ai_score_after"):
        assert k in r
    assert isinstance(r["ai_score_before"], int)
    assert r["ai_score_after"] <= r["ai_score_before"]

def test_detect_dict_keys():
    r = deslop.detect(KO_AI[0])
    for k in ("raw", "ai_score", "verdict", "top_patterns"):
        assert k in r
    assert isinstance(r["ai_score"], int)

def test_coach_explains_patterns():
    r = deslop.coach(KO_AI[0])
    for k in ("raw", "ai_score", "safe_auto_summary", "coach_details", "takeaway"):
        assert k in r
    # At least one pattern explanation should be present for clearly-AI text.
    assert "###" in r["coach_details"]

def test_en_api_runs():
    assert deslop.humanize_en(EN_AI[0])["ai_score_after"] <= deslop.humanize_en(EN_AI[0])["ai_score_before"]
    assert "ai_score" in deslop.detect_en(EN_AI[0])
    assert "takeaway" in deslop.coach_en(EN_AI[0])

def test_auto_language_routing():
    assert deslop.humanize_auto(KO_AI[0])["lang"] == "ko"
    assert deslop.humanize_auto(EN_AI[0])["lang"] == "en"


# --- the tool needs no network / no API key ----------------------------------

def test_no_anthropic_dependency():
    import importlib
    assert importlib.util.find_spec("deslop") is not None
    # deslop + engine must import without anthropic installed or any API key.
    assert "anthropic" not in sys.modules
