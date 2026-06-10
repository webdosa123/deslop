<h1 align="center">deslop</h1>

<p align="center"><strong>AI 슬롭은 걷어내고, 의미는 남긴다.</strong></p>

<p align="center">
  <a href="README.md">English</a> · <b>한국어</b>
</p>

<p align="center">
AI 같은 글을 찾아 다듬고, 왜 그렇게 읽혔는지 알려주는 한국어·영어 글쓰기 도구. 내 컴퓨터에서 돌아가고, API 키가 필요 없다.
</p>

<p align="center">
  <img alt="License: MIT" src="https://img.shields.io/badge/License-MIT-yellow.svg">
  <img alt="Python" src="https://img.shields.io/badge/python-3.10%2B-blue.svg">
  <img alt="Offline" src="https://img.shields.io/badge/offline-no%20API%20key-green.svg">
  <img alt="Deps" src="https://img.shields.io/badge/core%20deps-none-green.svg">
</p>

---

> deslop은 글을 더 낫게 쓰고, AI 글의 버릇을 배우기 위한 도구다. 초고를 붙여넣으면 어떤 습관이 글을 AI처럼 보이게 하는지 짚어주고, 고치게 도와준다.
>
> AI 탐지기를 속이거나 AI 글을 내가 쓴 것처럼 위장하는 용도는 아니다. 그런 쓰임은 범위 밖이다.

---

## 무엇을 하나

deslop은 한국어나 영어 글을 읽고, AI 글의 티를 내는 습관을 찾는다. 언제 고쳐도 안전한 건 알아서 고치고, 애매한 건 제안만 달아 표시한다. 결정은 쓰는 사람 몫이다. 그리고 왜 그런지 설명까지 해준다. 보통 도구들이 건너뛰는 부분이다.

전부 파이썬으로 내 컴퓨터에서 돈다. 네트워크 호출이 없고, 핵심 라이브러리는 설치할 것도 없다.

| | |
|---|---|
| ✍️ **humanize** | 명백한 AI 표현은 자동 교체하고, 판단이 필요한 건 검토하도록 표시. |
| 🔍 **detect** | 텍스트의 AI 패턴 밀도를 0–100으로 채점. 단일, A/B, 회차 추적. |
| 📚 **coach** | 패턴마다 무엇이 어색한지, 왜 AI처럼 읽히는지, 어떻게 고칠지 설명. |

점수만으로는 배울 게 별로 없다. "이 문장은 버즈워드를 셋이나 쌓았다. 주장을 받쳐주는 구체적 사실로 바꿔라"가 훨씬 쓸모 있다.

## 점수, 얼마나 믿을 만한가

AI지수는 *알려진* AI 글쓰기 버릇이 얼마나 빽빽한지를 잰다. forensic 판별기가 아니다. 함께 들어 있는 샘플에서 대략 이런 값이 나온다. `pytest`로 직접 돌려볼 수 있다.

| | 개별 점수 | 평균 |
|---|---|---|
| 🇰🇷 한국어, AI 같은 글 | 85, 76 | 62.6 |
| 🇰🇷 한국어, 사람 글 | 5, 0, 11 | 5.4 |
| 🇺🇸 영어, AI 같은 글 | 55, 75 | 64.9 |
| 🇺🇸 영어, 사람 글 | 0, 4 | 1.9 |

일부러 까다롭게 만든 영어 35개 샘플(마케팅·블로그·에세이·이메일·일기·리뷰에 더해, 오탐을 노린 어휘 화려한 인간 글)로 넓게 재보면 AI 글 평균은 약 39, 사람 글은 약 9로 30점쯤 차이가 난다. 사람 글 중 "AI 패턴 다수" 구간에 들어간 건 하나도 없다.

못 잡는 것도 있다. 이미 손본 글이나 일부러 담백하게 쓴 AI 글은 점수가 낮게 나와 빠져나간다. 그런 글은 실제로 더 사람처럼 읽히니 의도된 동작이다. Turnitin이나 GPTZero 같은 게 아니다. 숫자는 손볼 데를 가리킬 뿐, 무언가를 증명해주지는 않는다.

## 설치

```bash
git clone https://github.com/webdosa123/deslop.git
cd deslop
# 라이브러리와 CLI는 파이썬 표준 라이브러리만 있으면 된다.
# Streamlit은 선택적 웹 데모에만 필요하다:
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

규칙과 산수로 돌아간다. 머신러닝도, 뒤에서 도는 모델도 없다.

Safe Auto는 잘못될 일이 거의 없는 교정을 맡는다. 부풀린 단어를 담백한 말로 바꾸고(leverage를 use로, 혁신적인을 새로운으로), 내용 없는 도입과 마무리를 지운다. 과장이나 모호한 권위 인용처럼 위험한 건 고치지 않고 표시만 한다. 결정권은 쓰는 사람에게 둔다. 점수는 몇 가지 신호를 섞어 낸다. 패턴이 얼마나 자주 나오는지, 접속어로 시작하는 문장이 몇 개인지, 쉼표가 얼마나 잦은지, 그리고 문장 길이가 얼마나 고른지다. 마지막 항목인 burstiness는 생각보다 중요하다. 문장 길이마저 티가 나기 때문이다.

같은 입력은 늘 같은 결과를 낸다. 전체 패턴 목록은 **[PATTERNS.md](PATTERNS.md)** 에 있다. 한국어는 P01–P14, 영어는 E01–E14다.

## 의도된 용도

내 초고를 다듬을 때, AI 글이 보통 어떤 모습인지 배울 때, 또는 편집자나 교사로서 남의 초고를 검토할 때 쓰면 된다.

AI 글을 내 것으로 제출하거나, 학교 정책을 피하거나, 그런 쪽으로는 쓰지 말자.

## 출처

패턴 접근법은 영어 [stop-slop](https://github.com/hardikpandya/stop-slop)(MIT)에서 출발했다. PATTERNS.md의 설명은 Wikipedia "Signs of AI writing" 가이드(CC BY-SA 4.0)를 참고했다. 한국어 고유 신호의 근거는 KatFishNet(ACL 2025, [arXiv:2503.00032](https://arxiv.org/abs/2503.00032))에서 가져왔다.

자세한 내용은 [NOTICE](NOTICE)에 있다. 이 저장소에 제3자 텍스트는 들어 있지 않다.

## 라이선스

[MIT](LICENSE) © 2026 webdosa123
