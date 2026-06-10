"""
deslop — Python API

A deterministic, offline AI-writing cleaner / detector / coach for Korean and English.
No API key, no network, no third-party dependencies — pure rule-based transforms and scoring.

Usage:
    from deslop import humanize, detect, coach          # Korean
    from deslop import humanize_en, detect_en, coach_en  # English

    r = humanize("AI가 생성한 텍스트")
    print(r["transformed_text"])
    print(r["ai_score_before"], "->", r["ai_score_after"])

    d = detect("...")            # {ai_score, verdict, top_patterns, raw}
    c = coach("...")             # explains WHY each pattern reads as AI

Returned dicts:
    humanize* : raw, lang, text_type, transformed_text, safe_auto, flags,
                progress, ai_score_before, ai_score_after
    detect*   : raw, ai_score, verdict, top_patterns
    coach*    : raw, ai_score, safe_auto_summary, coach_details, takeaway
"""

import engine
from engine import format_result


# ─── engine adapters (deterministic, offline) ────────────────────────────────

def _engine_humanize_dict(res, lang: str) -> dict:
    """engine HumanizerResult -> humanize() dict."""
    en = (lang == "en")
    mb, ma = res.metrics_before, res.metrics_after
    before = int(round(mb.ai_score)) if mb else None
    after = int(round(ma.ai_score)) if ma else None

    text_type = (engine._classify_text_en if en else engine._classify_text_ko)(res.original_text)

    if res.safe_auto_changes:
        safe_auto = "\n".join(f"- {ch.pattern_id}: {ch.description}" for ch in res.safe_auto_changes)
    else:
        safe_auto = "- No Safe Auto changes" if en else "- Safe Auto 변경 없음"

    if res.flags:
        if en:
            flags = "\n".join(
                f'- Sentence {f.sentence_idx + 1}: {f.pattern_id} "{f.original}" → {f.suggestion}'
                for f in res.flags
            )
        else:
            flags = "\n".join(
                f'- {f.sentence_idx + 1}번 문장: {f.pattern_id} "{f.original}" → {f.suggestion}'
                for f in res.flags
            )
    else:
        flags = "- No flags" if en else "- Flag 없음"

    if en:
        progress = f"[Original {before} pts] → [After Safe Auto {after} pts] → [Target 10 pts or below]"
    else:
        progress = f"[원문 {before}점] → [Safe Auto 후 {after}점] → [목표 10점 이하]"

    return {
        "raw": format_result(res),
        "lang": lang,
        "text_type": text_type,
        "transformed_text": res.converted_text,
        "safe_auto": safe_auto,
        "flags": flags,
        "progress": progress,
        "ai_score_before": before,
        "ai_score_after": after,
    }


def _metrics_block(m, lang: str) -> str:
    if lang == "en":
        return (
            f"Pattern density: {m.pattern_density:.2f}\n"
            f"Connector freq: {m.connector_freq:.2f}\n"
            f"Punct/sentence: {m.punct_per_sentence:.2f}\n"
            f"Burstiness: {m.burstiness:.1f}\n"
            f"Sentences: {m.sentence_count}"
        )
    return (
        f"패턴 밀도: {m.pattern_density:.2f}\n"
        f"접속어 빈도: {m.connector_freq:.2f}\n"
        f"쉼표/문장: {m.punct_per_sentence:.2f}\n"
        f"Burstiness: {m.burstiness:.1f}\n"
        f"문장 수: {m.sentence_count}"
    )


def _engine_detect_dict(text, lang, compare_text=None, track_texts=None) -> dict:
    en = (lang == "en")
    detect_fn = engine.detect_en if en else engine.detect_ko
    label_fn = engine._score_label_en if en else engine._score_label_ko
    fmt = (lambda n: f"{n} pts") if en else (lambda n: f"{n}점")

    m = detect_fn(text)
    score = int(round(m.ai_score))
    verdict = label_fn(m.ai_score)
    top_patterns = _metrics_block(m, lang)

    lines = []
    if en:
        lines.append(f"[AI Score: {score} pts] — {verdict}")
    else:
        lines.append(f"[AI지수: {score}점] — {verdict}")
    lines.append("")
    lines.append(top_patterns)

    if compare_text:
        m2 = detect_fn(compare_text)
        s2 = int(round(m2.ai_score))
        lines.append("")
        lines.append("--- A/B comparison ---" if en else "--- A/B 비교 ---")
        lines.append(f"A: {fmt(score)} ({verdict})")
        lines.append(f"B: {fmt(s2)} ({label_fn(m2.ai_score)})")
        lines.append(("Δ: " if en else "차이: ") + f"{s2 - score:+d}" + ("" if en else "점") + (" pts" if en else ""))
    elif track_texts:
        lines.append("")
        lines.append("--- Revision tracking ---" if en else "--- 회차 추적 ---")
        orig_label = "Original" if en else "원문"
        lines.append(f"{orig_label}: {fmt(score)}")
        prev = score
        for i, t in enumerate(track_texts, 1):
            si = int(round(detect_fn(t).ai_score))
            rev_label = f"Revision {i}" if en else f"수정 {i}회차"
            lines.append(f"{rev_label}: {fmt(si)} ({si - prev:+d})")
            prev = si

    return {
        "raw": "\n".join(lines),
        "ai_score": score,
        "verdict": verdict,
        "top_patterns": top_patterns,
    }


# Pattern coaching map — each id -> {label, why it reads as AI, how to fix}.
# Reimagined for deterministic use; pattern taxonomy inspired by the English
# "stop-slop" project (hardikpandya/stop-slop, MIT). See NOTICE.
_KO_COACH = {
    "P01": {"label": "접속어 과다", "why": 'AI는 논리 흐름을 "또한·따라서"로 일일이 표시하지만, 한국어는 어미와 문장 구조로 연결돼 이 신호가 군더더기로 읽힌다.', "fix": "접속어를 지우고 의미가 이어지면 그대로, 끊기면 앞 문장 구조를 고친다."},
    "P03": {"label": "강의체 프레이밍", "why": '"~에 대해 살펴보겠습니다" 같은 강의록·튜토리얼 말투를 학습해, 독자를 수업에 앉히는 빈 도입·마무리가 붙는다.', "fix": "내용 없는 도입·마무리를 지우고 본론 첫 문장과 마지막 논점으로 시작·종료한다."},
    "P04": {"label": "번역투·학술체", "why": '영어 학술문을 직역해 "본 연구"(this study), "이러한 맥락에서"(in this context)처럼 외국어 번역체로 읽힌다.', "fix": '"본·상기·이러한 맥락"은 "이·그"나 고유명사로 바꾸거나 지운다.'},
    "P05": {"label": "중요성 과장", "why": '주의를 끌려고 "매우 중요한 핵심"처럼 강조어를 겹쳐 쓰지만, 근거 없는 수식어가 쌓일수록 오히려 공허하게 들린다.', "fix": "수식어 대신 왜 중요한지 구체 사실로 보여주고, 못 쓰면 수식어를 뺀다."},
    "P06": {"label": "AI 특유 어휘", "why": '"다양한·효율적으로"는 구체적 목록이나 방법을 모를 때 쓰는 회피어라, 한 단락에 몰리면 기계적으로 읽힌다.', "fix": '"다양한"엔 실제 숫자·이름을 붙이고, 안 되면 단어 자체를 지운다.'},
    "P08": {"label": "수식어 중첩", "why": '"보다 더욱 더"처럼 같은 강조를 여러 겹 쌓아 서로 상쇄시키는 언어 낭비다.', "fix": "연달아 나온 수식어 둘 중 하나만 남기면 더 강하게 읽힌다."},
    "P09": {"label": "오해 바로잡기 구조", "why": '"흔히 X라 생각하지만 사실 Y다" 수사를 실제 독자 오해와 무관하게 공식처럼 남발해 허공에 주먹질하듯 들린다.', "fix": '"단순히 ~이 아니라"를 지우고 하고 싶은 말을 직접 주장한다.'},
    "P10": {"label": "포괄적 일반화", "why": '"많은 전문가들은·연구에 따르면"처럼 익명의 권위를 빌려 근거 없이 신뢰성을 꾸미려는 시도다.', "fix": "누구·어떤 연구인지 특정하거나, 못 하면 근거 표현을 빼고 주장만 남긴다."},
    "P11": {"label": "과제와 전망 공식", "why": '"앞으로 더욱 발전할 것으로 기대됩니다"는 내용 없이도 붙는 빈 껍데기라, 근거와 끊긴 전망이 공허하게 들린다.', "fix": "마지막 실질 논점으로 끝내고, 전망은 앞의 데이터·근거와 연결한다."},
    "P12": {"label": "공손한 대화체 표현", "why": '"도움이 되셨으면 합니다"는 대화형 응대 말투라, 내용을 전달하는 글에 남으면 생성형 답변이라는 인상을 준다.', "fix": "대화체 마무리를 지우고 마지막 실질 문장으로 글을 끝낸다."},
    "P13": {"label": "쉼표·구두점 패턴", "why": '영어식 접속어 뒤 쉼표(However,)와 절 경계 쉼표를 한국어에 그대로 옮겨, 원어민보다 쉼표가 과도해진다.', "fix": '접속어 뒤 쉼표("또한,"→"또한")부터 지우고 접속어 자체도 뺀다.'},
    "P14": {"label": "통계적 균일성", "why": "생성 텍스트는 일정한 정보 밀도를 유지해 모든 문장이 6~9어절로 비슷해져, 리듬 없이 단조롭게 읽힌다.", "fix": "강조할 문장은 2~4어절로 줄여 짧은 문장과 긴 문장을 섞는다."},
}

_EN_COACH = {
    "E01": {"label": "Connector Overload", "why": "Sentences keep opening with Furthermore/Moreover/Therefore, making every logical step explicit.", "fix": "Delete the connector; let sentence order carry the logic."},
    "E02": {"label": "Academic/Formal Register", "why": "Default academic hedging like 'it is imperative' creates cold distance.", "fix": "Say it as you would to a smart colleague."},
    "E03": {"label": "Lecture Framing", "why": "Tutorial-style openers/closers ('In this article...') frame text as a lesson, not writing.", "fix": "Cut the frame; open and close on real content."},
    "E04": {"label": "Formulaic Filler Phrases", "why": "Zero-content hedges like 'It is important to note that' delay the real claim.", "fix": "Delete the filler; state the claim directly."},
    "E05": {"label": "Hyperbolic Modifiers", "why": "Cost-free superlatives ('revolutionary,' 'unprecedented') inflate without earning emphasis.", "fix": "Replace the adjective with the specific that proves it."},
    "E06": {"label": "Inflated Vocabulary", "why": "Words like 'leverage,' 'delve,' 'robust' cluster far denser here than in plain human text.", "fix": "Swap each for its plain, direct synonym."},
    "E08": {"label": "Modifier Stacks", "why": "Stacked intensifiers ('highly important') signal the writer doubts the word lands alone.", "fix": "Drop the adverb; keep one confident modifier."},
    "E09": {"label": "Misconception Structure", "why": "'Contrary to popular belief' sets up a straw man nobody actually holds as an engagement hook.", "fix": "Strip the opener; lead with your actual point."},
    "E10": {"label": "Sweeping Generalization", "why": "'Research shows'/'experts say' fakes evidence with citation-shaped language and no source.", "fix": "Name the source, or assert the claim directly."},
    "E11": {"label": "Foresight Framing", "why": "'Moving forward' and 'has the potential to' announce structure and hedge without committing.", "fix": "Delete the phrase; state the conclusion outright."},
    "E12": {"label": "Conversational Sign-offs", "why": "'I hope this helps' is a chat-style sign-off that exposes a generated-answer origin.", "fix": "End on content; make any contact line specific."},
    "E13": {"label": "Punctuation Patterns", "why": "Em dashes at ~10x rate plus reflexive comma-after-connector form a recognizable signature.", "fix": "Limit em dashes to one per paragraph; cut connector commas."},
    "E14": {"label": "Statistical Uniformity", "why": "Uniform 15-25 word sentences make rhythm metronomic; human length varies for emphasis.", "fix": "Cut a key sentence under 8 words; let the next expand."},
}


def _engine_coach_dict(text, lang: str) -> dict:
    """Map detected patterns -> per-pattern coaching (deterministic)."""
    en = (lang == "en")
    coach_map = _EN_COACH if en else _KO_COACH
    humanize_fn = engine.humanize_en if en else engine.humanize_ko

    res = humanize_fn(text)
    m = res.metrics_before
    score = int(round(m.ai_score)) if m else None

    seen: list[str] = []
    for ch in res.safe_auto_changes:
        if ch.pattern_id not in seen:
            seen.append(ch.pattern_id)
    for f in res.flags:
        if f.pattern_id not in seen:
            seen.append(f.pattern_id)

    if res.safe_auto_changes:
        safe_auto_summary = "\n".join(f"- {ch.pattern_id}: {ch.description}" for ch in res.safe_auto_changes)
    else:
        safe_auto_summary = "- (no auto-processed structural patterns)" if en else "- (자동 처리된 구조 패턴 없음)"

    detail_blocks = []
    for pid in seen:
        info = coach_map.get(pid)
        if not info:
            continue
        if en:
            detail_blocks.append(
                f"### {pid} — {info['label']}\n"
                f"- Why it reads as AI: {info['why']}\n"
                f"- Fix: {info['fix']}"
            )
        else:
            detail_blocks.append(
                f"### {pid} — {info['label']}\n"
                f"- 왜 AI 같은가: {info['why']}\n"
                f"- 고치는 법: {info['fix']}"
            )
    if detail_blocks:
        coach_details = "\n\n".join(detail_blocks)
    else:
        coach_details = "No patterns detected — this reads naturally." if en else "감지된 패턴이 없습니다. 자연스러운 글입니다."

    if seen and coach_map.get(seen[0]):
        top = coach_map[seen[0]]
        takeaway = f"{top['label']}: {top['fix']}"
    else:
        takeaway = "Write with specifics and cut filler." if en else "구체적 사실로 쓰고 군더더기를 덜어내세요."

    if en:
        raw = (
            f"[AI Score: {score} pts]\n\n"
            f"[Safe Auto Summary]\n{safe_auto_summary}\n\n"
            f"[Pattern Coaching]\n{coach_details}\n\n"
            f"[Today's Key Takeaway]\n{takeaway}"
        )
    else:
        raw = (
            f"[AI지수: {score}점]\n\n"
            f"[Safe Auto 요약]\n{safe_auto_summary}\n\n"
            f"[패턴 코치 해설]\n{coach_details}\n\n"
            f"[오늘의 핵심 takeaway]\n{takeaway}"
        )

    return {
        "raw": raw,
        "ai_score": score,
        "safe_auto_summary": safe_auto_summary,
        "coach_details": coach_details,
        "takeaway": takeaway,
    }


# ─── public API (Korean) ──────────────────────────────────────────────────────

def humanize(text: str) -> dict:
    """Clean AI-writing patterns from Korean text (deterministic, offline)."""
    return _engine_humanize_dict(engine.humanize_ko(text), "ko")


def detect(text: str, compare_text: str = None, track_texts: list[str] = None) -> dict:
    """Score Korean text for AI patterns without modifying it.

    compare_text -> A/B mode; track_texts -> revision tracking (text = original).
    """
    return _engine_detect_dict(text, "ko", compare_text, track_texts)


def coach(text: str) -> dict:
    """Explain WHY Korean text reads as AI-written, pattern by pattern."""
    return _engine_coach_dict(text, "ko")


def batch_humanize(texts: list[str]) -> list[dict]:
    """humanize() over a list, preserving order."""
    return [humanize(t) for t in texts]


def batch_detect(texts: list[str]) -> list[dict]:
    """detect() over a list, preserving order."""
    return [detect(t) for t in texts]


# ─── public API (English) ─────────────────────────────────────────────────────

def humanize_en(text: str) -> dict:
    """Clean AI-writing patterns from English text (deterministic, offline)."""
    return _engine_humanize_dict(engine.humanize_en(text), "en")


def detect_en(text: str, compare_text: str = None, track_texts: list[str] = None) -> dict:
    """Score English text for AI patterns. compare_text -> A/B; track_texts -> tracking."""
    return _engine_detect_dict(text, "en", compare_text, track_texts)


def coach_en(text: str) -> dict:
    """Explain WHY English text reads as AI-written, pattern by pattern."""
    return _engine_coach_dict(text, "en")


# ─── language auto-detect (Korean / English) ─────────────────────────────────

def humanize_auto(text: str) -> dict:
    """Detect Korean vs English and humanize accordingly.

    Korean-char ratio > 30% -> Korean engine, else English engine.
    """
    if not text:
        raise ValueError("empty text")
    korean = sum(1 for c in text if "가" <= c <= "힣")
    if korean / len(text) > 0.3:
        return humanize(text)
    return humanize_en(text)


# ─── CLI ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import sys
    import io

    # Make Korean / em-dash output safe on legacy Windows consoles (cp949).
    if hasattr(sys.stdout, "buffer"):
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

    if len(sys.argv) < 2:
        print("usage: python deslop.py <text or file path> [--detect|--coach] [--en]")
        sys.exit(1)

    arg = sys.argv[1]
    flags = set(sys.argv[2:])
    from pathlib import Path

    p = Path(arg)
    input_text = p.read_text(encoding="utf-8") if p.exists() and p.is_file() else arg
    is_en = "--en" in flags

    if "--detect" in flags:
        result = (detect_en if is_en else detect)(input_text)
        print(f"AI score: {result['ai_score']}")
        print(f"verdict : {result['verdict']}")
        print("─" * 40)
        print(result["raw"])
    elif "--coach" in flags:
        result = (coach_en if is_en else coach)(input_text)
        print(f"AI score: {result['ai_score']}")
        print("─" * 40)
        print(result["raw"])
    else:
        result = (humanize_en if is_en else humanize)(input_text)
        print(f"AI score: {result['ai_score_before']} -> {result['ai_score_after']}")
        print("─" * 40)
        print(result["transformed_text"] or result["raw"])
