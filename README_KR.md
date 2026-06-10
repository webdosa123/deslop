<h1 align="center">deslop</h1>

<p align="center"><strong>AI 슬롭은 걷어내고, 의미는 남긴다.</strong></p>

<p align="center">
  <a href="README.md">English</a> · <b>한국어</b>
</p>

<p align="center">
결정론적 · 100% 오프라인 · API 키 불필요 — 한국어 &amp; 영어 AI 글쓰기 <b>정리 · 탐지 · 코치</b> 도구
</p>

<p align="center">
  <img alt="License: MIT" src="https://img.shields.io/badge/License-MIT-yellow.svg">
  <img alt="Python" src="https://img.shields.io/badge/python-3.10%2B-blue.svg">
  <img alt="Offline" src="https://img.shields.io/badge/offline-no%20API%20key-green.svg">
  <img alt="Deps" src="https://img.shields.io/badge/core%20deps-none-green.svg">
</p>

---

> ✍️ **deslop은 글쓰기 품질·AI 리터러시 도구입니다** — *왜* 글이 AI처럼 읽히는지 이해하고 더 나은 글을 쓰기 위한 것입니다.
> **AI 탐지기를 우회하거나 AI 글을 사람 글로 위장하는 용도가 아닙니다.** 탐지 우회는 명시적인 비목표(non-goal)입니다.

---

## 무엇을 하나

deslop은 글을 AI처럼 보이게 만드는 표면 패턴을 찾아, 안전한 것은 자동 교정하고 나머지는 이유와 함께 설명합니다 — **한국어와 영어**로, 완전히 **결정론적**이고 **오프라인**으로. API 키도, 네트워크도, 모델 호출도, 핵심부의 외부 의존성도 없습니다.

| | |
|---|---|
| ✍️ **humanize** | 명백한 AI 표현은 자동 교체(Safe Auto), 판단이 필요한 건 검토하도록 Flag 처리. |
| 🔍 **detect** | 텍스트를 0–100점으로 채점(AI 패턴 밀도). 단일 / A-B 비교 / 회차 추적 모드. |
| 📚 **coach** | 패턴 하나하나에 대해 *왜* AI처럼 읽히는지, *어떻게* 고치는지 설명. |

핵심은 **coach**입니다. 점수만으로는 알 수 있는 게 적지만, "이 문장은 버즈워드를 셋이나 쌓았다 — 주장을 증명하는 구체적 사실로 바꿔라"는 바로 실행할 수 있는 조언입니다.

## 점수에 대한 정직한 이야기

deslop의 AI지수는 **알려진 AI 글쓰기 패턴의 밀도 신호**이지, forensic 판별기가 아닙니다. 합성 샘플에서 실제로 나오는 값입니다 (`pytest`로 재현 가능):

| | 개별 AI지수 | 평균 |
|---|---|---|
| 🇰🇷 한국어 — AI 같은 글 | 85, 76 | **62.6** |
| 🇰🇷 한국어 — 사람 글 | 5, 0, 11 | **5.4** |
| 🇺🇸 영어 — AI 같은 글 | 55, 37 | 46.1 |
| 🇺🇸 영어 — 사람 글 | 0, 4 | 1.9 |

**판별격차: 한국어 약 57점, 영어 약 44점.** 명백한 AI 글과 사람 글은 잘 갈립니다 — 특히 한국어에서.

**한계 — 분명히 밝힙니다:**
- *알려진 표면 패턴*을 탐지합니다. 이미 다듬어졌거나 일부러 평범하게 쓴 AI 글은 낮게 나와 빠져나갈 수 있습니다.
- **현재 영어는 한국어보다 약합니다** (판별격차가 작음, 개선 중).
- ML 분류기가 **아니며** Turnitin·GPTZero급도 **아닙니다.** 점수는 판정이 아니라 글쓰기 신호로 보세요.

## 설치

```bash
git clone https://github.com/webdosa123/deslop.git
cd deslop
# 핵심 라이브러리 + CLI는 설치할 게 없습니다 — 순수 파이썬 표준 라이브러리.
# 선택적 웹 데모만 Streamlit이 필요합니다:
pip install -r requirements.txt
```

## 사용법

**CLI**
```bash
python deslop.py "이 제품은 혁신적인 솔루션을 통해 가치를 극대화합니다."
python deslop.py "텍스트" --detect          # 점수만
python deslop.py "텍스트" --coach            # 패턴 해설
python deslop.py "your English text" --en    # 영어
python deslop.py 파일경로.txt --coach        # 파일에서 읽기
```

**라이브러리**
```python
from deslop import humanize, detect, coach          # 한국어
from deslop import humanize_en, detect_en, coach_en  # 영어

r = humanize("이 제품은 혁신적인 솔루션을 통해 패러다임을 전환합니다.")
print(r["ai_score_before"], "->", r["ai_score_after"])   # 93 -> 36
print(r["transformed_text"])

print(detect("...")["verdict"])
print(coach("...")["coach_details"])   # 패턴별 이유 + 교정
```

**웹 데모**
```bash
streamlit run app.py
```

## 작동 원리

순수 규칙 기반 변환과 통계 — 머신러닝도, LLM도 없습니다:

- **Safe Auto** — 신뢰도 높고 어조에 안전한 치환(예: *leverage → use*, *혁신적인 → 새로운*)과 내용 없는 도입·마무리 삭제.
- **Flag & Suggest** — 신뢰도가 낮은 판단(과장, 모호한 권위, 전망 filler)은 자동 교정하지 않고 제안과 함께 표시 — 결정권은 당신에게.
- **AI지수** — 패턴 밀도, 접속어 빈도, 구두점 비율, 문장 길이 **burstiness**(균일한 리듬은 강한 기계 신호)를 결합.

결정론적이라 같은 입력은 항상 같은 출력을 냅니다 — 즉시, 오프라인, 무료로.

전체 한국어(P01–P14)·영어(E01–E14) 패턴 카탈로그는 **[PATTERNS.md](PATTERNS.md)** 참고.

## 의도된 용도 / 아닌 용도

**의도된 용도:** 자기 글 개선, 흔한 AI 글쓰기 패턴 학습, 초고에 대한 편집·교육 검토.
**아닌 용도:** AI 생성물을 사람 글로 제출, 학문적 부정행위, 기관의 AI 정책 우회.

## 출처

- 패턴 접근법은 영어 **[stop-slop](https://github.com/hardikpandya/stop-slop)** (MIT)에서 영감.
- 패턴 설명은 Wikipedia **"Signs of AI writing"** 편집 가이드(CC BY-SA 4.0)를 참고.
- 한국어 신호 근거는 **KatFishNet** (ACL 2025, [arXiv:2503.00032](https://arxiv.org/abs/2503.00032)).

자세한 내용은 [NOTICE](NOTICE) 참고. 이 저장소에 제3자 텍스트는 재배포되지 않습니다.

## 라이선스

[MIT](LICENSE) © 2026 webdosa123
