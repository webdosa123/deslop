# Pattern catalogue

The pattern descriptions below paraphrase, in part, the Wikipedia
**"Signs of AI writing"** editing guide, which is licensed **CC BY-SA 4.0**.
That guide is the reference for *what* the patterns are; deslop's detection and
rewriting logic is original. Reuse of this file's prose should preserve this
attribution (CC BY-SA 4.0).

Each entry: **id — name** · *why it reads as AI* · **fix**.
Korean ids are `P##`, English ids are `E##`. Only patterns the engine actually
detects are listed.

---

## Korean (P01–P14)

| id | 패턴 | 왜 AI처럼 읽히나 | 고치는 법 |
|----|------|------------------|-----------|
| P01 | 접속어 과다 | 논리 흐름을 "또한·따라서"로 일일이 표시 — 한국어는 어미·구조로 이어져 군더더기로 읽힘 | 접속어를 지우고 이어지면 그대로, 끊기면 앞 문장 구조 수정 |
| P03 | 강의체 프레이밍 | "~에 대해 살펴보겠습니다" 식 강의록 말투의 빈 도입·마무리 | 내용 없는 도입·마무리 삭제, 본론·논점으로 시작·종료 |
| P04 | 번역투·학술체 | 영어 직역체("본 연구", "이러한 맥락에서") | "본·상기·이러한 맥락" → "이·그"나 고유명사로 교체/삭제 |
| P05 | 중요성 과장 | "매우 중요한 핵심"처럼 근거 없는 강조어 누적 | 수식어 대신 구체 사실로 보여주기 |
| P06 | AI 특유 어휘 | "다양한·효율적으로" 등 구체성 회피어가 한 단락에 몰림 | 실제 숫자·이름을 붙이거나 단어 자체 삭제 |
| P08 | 수식어 중첩 | "보다 더욱 더"처럼 같은 강조 중첩 | 연속 수식어 중 하나만 남기기 |
| P09 | 오해 바로잡기 구조 | "흔히 X라 생각하지만 사실 Y"를 공식처럼 남발 | "단순히 ~이 아니라" 삭제, 하고 싶은 말 직접 주장 |
| P10 | 포괄적 일반화 | "많은 전문가들은·연구에 따르면" 식 익명 권위 | 출처 특정 또는 근거 표현 삭제 |
| P11 | 과제와 전망 공식 | "앞으로 더욱 발전할 것으로 기대됩니다" 빈 전망 | 실질 논점으로 끝내고, 전망은 근거와 연결 |
| P12 | 대화체 표현 | "도움이 되셨으면 합니다" 식 응대 말투 | 대화체 마무리 삭제, 실질 문장으로 종료 |
| P13 | 쉼표·구두점 패턴 | 영어식 접속어 뒤 쉼표(However,)를 한국어에 그대로 이식 | 접속어 뒤 쉼표·접속어 자체 삭제 |
| P14 | 통계적 균일성 | 모든 문장이 6~9어절로 균일 — 리듬 없이 단조로움 | 2~4어절 짧은 문장을 섞어 길이 변화 주기 |

## English (E01–E14)

| id | pattern | why it reads as AI | fix |
|----|---------|--------------------|-----|
| E01 | Connector overload | Sentences keep opening with Furthermore/Moreover/Therefore | Delete the connector; let order carry the logic |
| E02 | Academic/formal register | Default hedging like "it is imperative" — cold distance | Say it as you would to a smart colleague |
| E03 | Lecture framing | "In this article..." openers/closers frame text as a lesson | Cut the frame; open and close on content |
| E04 | Formulaic filler | "It is important to note that" delays the real claim | Delete the filler; state the claim |
| E05 | Hyperbolic modifiers | "revolutionary," "unprecedented" inflate without earning it | Replace with the specific that proves it |
| E06 | Inflated vocabulary | "leverage," "delve," "robust" cluster far denser than in plain text | Swap for the plain synonym |
| E08 | Modifier stacks | "highly important" — doubts the word lands alone | Drop the adverb; keep one modifier |
| E09 | Misconception structure | "Contrary to popular belief" sets up a straw man | Strip the opener; lead with your point |
| E10 | Sweeping generalization | "Research shows"/"experts say" fakes evidence | Name the source, or assert directly |
| E11 | Foresight framing | "Moving forward," "has the potential to" hedge without committing | Delete the phrase; state the conclusion |
| E12 | Conversational sign-offs | "I hope this helps" exposes a generated-answer origin | End on content |
| E13 | Punctuation patterns | Em dashes at ~10× rate + reflexive comma-after-connector | One em dash per paragraph; cut connector commas |
| E14 | Statistical uniformity | Uniform 15–25 word sentences make rhythm metronomic | Cut a key sentence under 8 words; let the next expand |

---

In **humanize**, the safest of these (clear lexical swaps, contentless openers/closers)
are applied automatically (Safe Auto); the rest are flagged with a suggestion so you
decide. In **coach**, every detected pattern is explained with its *why* and *fix*.
