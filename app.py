"""
deslop — web demo

Run:
    streamlit run app.py

No API key, no network — fully offline, deterministic.
"""

import streamlit as st
from deslop import humanize, detect, coach, humanize_en, detect_en, coach_en

st.set_page_config(
    page_title="deslop",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ─── 헤더 ────────────────────────────────────────────────────────────────────

st.title("deslop")
st.caption("결정론적 AI 글쓰기 정리·탐지·코치 · 한국어/영어 · AI지수 0–100 · 오프라인 (API 키 불필요)")
st.info(
    "✍️ 글쓰기 품질·AI 리터러시 도구입니다 — **왜 AI처럼 읽히는지** 이해하고 더 나은 글을 쓰기 위한 것입니다. "
    "AI 탐지 우회나 AI 글을 사람 글로 위장하는 용도가 **아닙니다**.  \n"
    "A writing-quality and AI-literacy tool to understand *why* text reads as AI — "
    "**not** for evading AI detectors or passing off AI text as human-written."
)

tab_humanize, tab_detect, tab_coach, tab_en = st.tabs(["✍️ 자연화 (KO)", "🔍 탐지", "📚 코치", "🇺🇸 English"])


# ─── 자연화 탭 ───────────────────────────────────────────────────────────────

with tab_humanize:
    col_in, col_out = st.columns([1, 1], gap="large")

    with col_in:
        st.subheader("원문")
        input_text = st.text_area(
            "원문",
            height=300,
            placeholder="AI가 생성한 한국어 텍스트를 붙여넣으세요.",
            label_visibility="collapsed",
        )
        with st.expander("내 스타일 샘플 입력 (선택)"):
            style_sample = st.text_area(
                "스타일 샘플",
                height=120,
                placeholder="평소 자신이 쓴 글 예시를 입력하면 스타일에 맞게 변환합니다.",
                label_visibility="collapsed",
            )
        run_btn = st.button(
            "자연화 실행",
            type="primary",
            use_container_width=True,
            disabled=not input_text.strip(),
        )

    with col_out:
        st.subheader("결과")

        if run_btn and input_text.strip():
            with st.spinner("분석 중..."):
                result = humanize(input_text, style_sample=style_sample or None)

            # AI지수 게이지
            score_before = result["ai_score_before"]
            score_after = result["ai_score_after"]

            if score_before is not None:
                m1, m2, m3 = st.columns(3)
                m1.metric("원문 AI지수", f"{score_before}점")
                if score_after is not None:
                    delta = score_after - score_before
                    m2.metric("Safe Auto 후", f"{score_after}점", delta=delta, delta_color="inverse")
                m3.metric("목표", "10점 이하")

                # 진행 바
                if score_before > 0:
                    after_val = score_after if score_after is not None else score_before
                    progress_pct = max(0.0, 1.0 - after_val / score_before)
                    st.progress(progress_pct, text=f"완료율 {int(progress_pct * 100)}%")

            # 진행 상태
            if result["progress"]:
                st.info(result["progress"])

            st.divider()

            # 변환 텍스트
            if result["transformed_text"]:
                st.subheader("변환된 텍스트")
                st.markdown(result["transformed_text"])
            else:
                # 섹션 파싱 실패 시 전체 출력 표시
                st.markdown(result["raw"])

            st.divider()

            # Safe Auto 내역 / Flag 목록
            detail_col1, detail_col2 = st.columns(2)
            with detail_col1:
                if result["safe_auto"]:
                    with st.expander("Safe Auto 처리 내역"):
                        st.markdown(result["safe_auto"])

            with detail_col2:
                if result["flags"]:
                    with st.expander("작가 검토 필요 — Flag", expanded=True):
                        st.markdown(result["flags"])

            # 전체 원본 출력
            with st.expander("전체 출력 (원본)"):
                st.text(result["raw"])


# ─── 탐지 탭 ─────────────────────────────────────────────────────────────────

with tab_detect:
    detect_mode = st.radio(
        "탐지 모드",
        ["단일 분석", "A/B 비교", "수정 회차 추적"],
        horizontal=True,
    )

    st.divider()

    if detect_mode == "단일 분석":
        detect_text = st.text_area(
            "분석할 텍스트",
            height=250,
            placeholder="AI 여부를 확인할 텍스트를 입력하세요.",
        )
        detect_btn = st.button(
            "탐지 실행",
            type="primary",
            disabled=not detect_text.strip(),
        )

        if detect_btn and detect_text.strip():
            with st.spinner("탐지 중..."):
                result = detect(detect_text)

            if result["ai_score"] is not None:
                score = result["ai_score"]
                if score >= 50:
                    st.error(f"AI지수 {score}점 — {result['verdict']}")
                elif score >= 20:
                    st.warning(f"AI지수 {score}점 — {result['verdict']}")
                else:
                    st.success(f"AI지수 {score}점 — {result['verdict']}")
                st.progress(min(score / 100, 1.0))
            elif result["verdict"]:
                st.markdown(f"**판정:** {result['verdict']}")

            st.divider()
            st.markdown(result["raw"])

    elif detect_mode == "A/B 비교":
        col_a, col_b = st.columns(2, gap="large")
        with col_a:
            text_a = st.text_area("텍스트 A", height=220, placeholder="원문 또는 첫 번째 텍스트")
        with col_b:
            text_b = st.text_area("텍스트 B", height=220, placeholder="수정본 또는 두 번째 텍스트")

        compare_btn = st.button(
            "비교 탐지",
            type="primary",
            disabled=not (text_a.strip() and text_b.strip()),
        )

        if compare_btn and text_a.strip() and text_b.strip():
            with st.spinner("비교 탐지 중..."):
                result = detect(text_a, compare_text=text_b)

            st.markdown(result["raw"])

    else:  # 수정 회차 추적
        st.caption("원문과 수정 회차별 텍스트를 입력하면 AI지수 변화를 추적합니다.")
        original_text = st.text_area("원문", height=150, placeholder="수정 전 원본 텍스트")
        rev1 = st.text_area("수정 1회차", height=150, placeholder="1차 수정 텍스트")
        rev2 = st.text_area("수정 2회차 (선택)", height=100, placeholder="2차 수정 텍스트 — 생략 가능")

        track_btn = st.button(
            "변화 추적",
            type="primary",
            disabled=not (original_text.strip() and rev1.strip()),
        )

        if track_btn and original_text.strip() and rev1.strip():
            track_list = [rev1]
            if rev2.strip():
                track_list.append(rev2)

            with st.spinner("추적 중..."):
                result = detect(original_text, track_texts=track_list)

            st.markdown(result["raw"])


# ─── 코치 탭 ─────────────────────────────────────────────────────────────────

with tab_coach:
    st.caption("패턴을 교체하는 게 아니라 **왜 AI처럼 읽히는지** 이해하는 모드입니다.")

    coach_text = st.text_area(
        "분석할 텍스트",
        height=250,
        placeholder="패턴 원인을 학습하고 싶은 텍스트를 입력하세요.",
    )
    coach_btn = st.button(
        "코치 리포트 생성",
        type="primary",
        disabled=not coach_text.strip(),
    )

    if coach_btn and coach_text.strip():
        with st.spinner("분석 중..."):
            result = coach(coach_text)

        if result["ai_score"] is not None:
            st.metric("AI지수", f"{result['ai_score']}점")

        # 핵심 takeaway — 가장 먼저 표시
        if result["takeaway"]:
            st.success(f"**오늘의 핵심 takeaway**\n\n{result['takeaway']}")

        st.divider()

        if result["safe_auto_summary"]:
            with st.expander("Safe Auto 요약 (구조적 패턴)"):
                st.markdown(result["safe_auto_summary"])

        if result["coach_details"]:
            st.subheader("패턴 코치 해설")
            st.markdown(result["coach_details"])
        else:
            st.markdown(result["raw"])

        with st.expander("전체 리포트 (원본)"):
            st.text(result["raw"])


# ─── English 탭 ──────────────────────────────────────────────────────────────

with tab_en:
    st.caption("English AI writing tools · 14 patterns (E01–E14) · AI Score 0–100")

    en_sub_humanize, en_sub_detect, en_sub_coach = st.tabs(
        ["✍️ Humanize", "🔍 Detect", "📚 Coach"]
    )

    # ── EN Humanize ──────────────────────────────────────────────────────────

    with en_sub_humanize:
        col_en_in, col_en_out = st.columns([1, 1], gap="large")

        with col_en_in:
            st.subheader("Input")
            en_input_text = st.text_area(
                "Input text",
                height=300,
                placeholder="Paste AI-generated English text here.",
                label_visibility="collapsed",
                key="en_input",
            )
            with st.expander("My style sample (optional)"):
                en_style_sample = st.text_area(
                    "Style sample",
                    height=120,
                    placeholder="Paste a sample of your own writing to match your voice.",
                    label_visibility="collapsed",
                    key="en_style",
                )
            en_run_btn = st.button(
                "Humanize",
                type="primary",
                use_container_width=True,
                disabled=not en_input_text.strip(),
                key="en_run",
            )

        with col_en_out:
            st.subheader("Result")

            if en_run_btn and en_input_text.strip():
                with st.spinner("Analyzing..."):
                    result = humanize_en(en_input_text, style_sample=en_style_sample or None)

                score_before = result.get("ai_score_before")
                score_after = result.get("ai_score_after")

                if score_before is not None:
                    m1, m2, m3 = st.columns(3)
                    m1.metric("Before", f"{score_before} pts")
                    if score_after is not None:
                        delta = score_after - score_before
                        m2.metric("After Safe Auto", f"{score_after} pts", delta=delta, delta_color="inverse")
                    m3.metric("Target", "< 10 pts")

                    if score_before > 0:
                        after_val = score_after if score_after is not None else score_before
                        progress_pct = max(0.0, 1.0 - after_val / score_before)
                        st.progress(progress_pct, text=f"{int(progress_pct * 100)}% complete")

                if result.get("progress"):
                    st.info(result["progress"])

                st.divider()

                if result.get("transformed_text"):
                    st.subheader("Converted Text")
                    st.markdown(result["transformed_text"])
                else:
                    st.markdown(result.get("raw", ""))

                st.divider()

                detail_col1, detail_col2 = st.columns(2)
                with detail_col1:
                    if result.get("safe_auto"):
                        with st.expander("Safe Auto changes"):
                            st.markdown(result["safe_auto"])

                with detail_col2:
                    if result.get("flags"):
                        with st.expander("Writer Review — Flag & Suggest", expanded=True):
                            st.markdown(result["flags"])

                with st.expander("Full output (raw)"):
                    st.text(result.get("raw", ""))

    # ── EN Detect ────────────────────────────────────────────────────────────

    with en_sub_detect:
        en_detect_mode = st.radio(
            "Detection mode",
            ["Single analysis", "A/B comparison", "Revision tracking"],
            horizontal=True,
            key="en_detect_mode",
        )

        st.divider()

        if en_detect_mode == "Single analysis":
            en_detect_text = st.text_area(
                "Text to analyze",
                height=250,
                placeholder="Paste text to check for AI patterns.",
                key="en_detect_single",
            )
            en_detect_btn = st.button(
                "Detect",
                type="primary",
                disabled=not en_detect_text.strip(),
                key="en_detect_run",
            )

            if en_detect_btn and en_detect_text.strip():
                with st.spinner("Detecting..."):
                    result = detect_en(en_detect_text)

                if result["ai_score"] is not None:
                    score = result["ai_score"]
                    if score >= 50:
                        st.error(f"AI Score {score} pts — {result['verdict']}")
                    elif score >= 20:
                        st.warning(f"AI Score {score} pts — {result['verdict']}")
                    else:
                        st.success(f"AI Score {score} pts — {result['verdict']}")
                    st.progress(min(score / 100, 1.0))
                elif result["verdict"]:
                    st.markdown(f"**Verdict:** {result['verdict']}")

                st.divider()
                st.markdown(result["raw"])

        elif en_detect_mode == "A/B comparison":
            col_a, col_b = st.columns(2, gap="large")
            with col_a:
                en_text_a = st.text_area("Text A", height=220, placeholder="Original or first text", key="en_text_a")
            with col_b:
                en_text_b = st.text_area("Text B", height=220, placeholder="Revised or second text", key="en_text_b")

            en_compare_btn = st.button(
                "Compare",
                type="primary",
                disabled=not (en_text_a.strip() and en_text_b.strip()),
                key="en_compare_run",
            )

            if en_compare_btn and en_text_a.strip() and en_text_b.strip():
                with st.spinner("Comparing..."):
                    result = detect_en(en_text_a, compare_text=en_text_b)

                st.markdown(result["raw"])

        else:  # Revision tracking
            st.caption("Enter the original and each revision to track AI Score change.")
            en_orig = st.text_area("Original", height=150, placeholder="Pre-revision text", key="en_track_orig")
            en_rev1 = st.text_area("Revision 1", height=150, placeholder="First revision", key="en_track_rev1")
            en_rev2 = st.text_area("Revision 2 (optional)", height=100, placeholder="Second revision", key="en_track_rev2")

            en_track_btn = st.button(
                "Track",
                type="primary",
                disabled=not (en_orig.strip() and en_rev1.strip()),
                key="en_track_run",
            )

            if en_track_btn and en_orig.strip() and en_rev1.strip():
                track_list = [en_rev1]
                if en_rev2.strip():
                    track_list.append(en_rev2)

                with st.spinner("Tracking..."):
                    result = detect_en(en_orig, track_texts=track_list)

                st.markdown(result["raw"])

    # ── EN Coach ─────────────────────────────────────────────────────────────

    with en_sub_coach:
        st.caption("Learn **why** your text reads as AI-generated — not just what to change.")

        en_coach_text = st.text_area(
            "Text to analyze",
            height=250,
            placeholder="Paste text to get pattern coaching.",
            key="en_coach_input",
        )
        en_coach_btn = st.button(
            "Generate Coach Report",
            type="primary",
            disabled=not en_coach_text.strip(),
            key="en_coach_run",
        )

        if en_coach_btn and en_coach_text.strip():
            with st.spinner("Analyzing..."):
                result = coach_en(en_coach_text)

            if result["ai_score"] is not None:
                st.metric("AI Score", f"{result['ai_score']} pts")

            if result["takeaway"]:
                st.success(f"**Today's Key Takeaway**\n\n{result['takeaway']}")

            st.divider()

            if result["safe_auto_summary"]:
                with st.expander("Safe Auto Summary (structural patterns)"):
                    st.markdown(result["safe_auto_summary"])

            if result["coach_details"]:
                st.subheader("Pattern Coaching")
                st.markdown(result["coach_details"])
            else:
                st.markdown(result["raw"])

            with st.expander("Full report (raw)"):
                st.text(result["raw"])


# ─── 사이드바 ────────────────────────────────────────────────────────────────

with st.sidebar:
    st.header("deslop")
    st.markdown("""
**한국어 — 3종:**
- **자연화 (KO)** — Safe Auto + Flag & Suggest
- **탐지** — AI지수 + 패턴 분포
- **코치** — 왜 AI 같은지 해설

**영어 — 3종:**
- **Humanize** — Safe Auto + Flag & Suggest
- **Detect** — AI Score + pattern distribution
- **Coach** — why it reads as AI

**KO 패턴:** P01–P14
**EN 패턴:** E01–E14

**AI지수 해석:**
- 50+ : AI 패턴 다수
- 20–49 : 일부 패턴 (회색지대)
- 0–19 : 자연스러운 글

AI지수는 *알려진 AI 표면 패턴의 밀도* 신호입니다 —
판별기(forensic detector)가 아닙니다.

100% 오프라인 · API 키 불필요 · 결정론적

[GitHub](https://github.com/webdosa123/deslop)
""")
