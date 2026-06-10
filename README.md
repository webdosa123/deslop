<h1 align="center">deslop</h1>

<p align="center"><strong>Strip the AI slop. Keep your meaning.</strong></p>

<p align="center">
  <b>English</b> · <a href="README_KR.md">한국어</a>
</p>

<p align="center">
Deterministic · 100% offline · no API key — a Korean &amp; English AI-writing <b>cleaner, detector, and coach</b>.
</p>

<p align="center">
  <img alt="License: MIT" src="https://img.shields.io/badge/License-MIT-yellow.svg">
  <img alt="Python" src="https://img.shields.io/badge/python-3.10%2B-blue.svg">
  <img alt="Offline" src="https://img.shields.io/badge/offline-no%20API%20key-green.svg">
  <img alt="Deps" src="https://img.shields.io/badge/core%20deps-none-green.svg">
</p>

---

> ✍️ **deslop is a writing-quality and AI-literacy tool** — it helps you understand *why* prose reads as AI-generated and write better.
> It is **not** for evading AI detectors or passing AI text off as human-written. Detector evasion is an explicit non-goal.

---

## What it does

deslop finds the surface patterns that make prose read as machine-written, rewrites the safe ones, and explains the rest — in **Korean and English**, fully **deterministically** and **offline**. No API key, no network, no model calls, and no third-party dependencies in the core.

| | |
|---|---|
| ✍️ **humanize** | Auto-replaces unambiguous AI-isms (Safe Auto) and flags judgment calls for you to review. |
| 🔍 **detect** | Scores text 0–100 for AI-writing-pattern density. Single / A-B / revision-tracking modes. |
| 📚 **coach** | Explains, pattern by pattern, *why* the text reads as AI and *how* to fix it. |

The **coach** is the point: a score alone tells you little, but "this sentence stacks three buzzwords — replace them with the specific that proves your claim" is something you can act on.

## Be honest about the score

deslop's AI score is a **density signal for known AI-writing tics** — not a forensic detector. Here is what it actually produces on synthetic samples (reproduce with `pytest`):

| | per-sample AI score | avg |
|---|---|---|
| 🇰🇷 Korean — AI-sounding | 85, 76 | **62.6** |
| 🇰🇷 Korean — human | 5, 0, 11 | **5.4** |
| 🇺🇸 English — AI-sounding | 55, 37 | 46.1 |
| 🇺🇸 English — human | 0, 4 | 1.9 |

**Separation: ~57 pts (KO), ~44 pts (EN).** Clearly-AI vs clearly-human text is well separated, especially in Korean.

**Limitations — stated plainly:**
- It detects *known surface patterns*. Already-edited or deliberately-plain AI text can score low and slip through.
- **English is weaker than Korean** today (smaller separation; improving).
- It is **not** an ML classifier and **not** Turnitin/GPTZero-grade. Treat the score as a writing signal, not a verdict.

## Install

```bash
git clone https://github.com/webdosa123/deslop.git
cd deslop
# The core library + CLI need NOTHING — pure Python standard library.
# Only the optional web demo needs Streamlit:
pip install -r requirements.txt
```

## Use

**CLI**
```bash
python deslop.py "이 제품은 혁신적인 솔루션을 통해 가치를 극대화합니다."
python deslop.py "your text" --detect          # score only
python deslop.py "your text" --coach            # explain the patterns
python deslop.py "your English text" --en       # English
python deslop.py path/to/file.txt --coach       # read from a file
```

**Library**
```python
from deslop import humanize, detect, coach          # Korean
from deslop import humanize_en, detect_en, coach_en  # English

r = humanize("이 제품은 혁신적인 솔루션을 통해 패러다임을 전환합니다.")
print(r["ai_score_before"], "->", r["ai_score_after"])   # 93 -> 36
print(r["transformed_text"])

print(detect("...")["verdict"])
print(coach("...")["coach_details"])   # per-pattern why + fix
```

**Web demo**
```bash
streamlit run app.py
```

## How it works

Pure rule-based transforms and statistics — no machine learning, no LLM:

- **Safe Auto** — high-confidence, register-safe substitutions (e.g. *leverage → use*, *혁신적인 → 새로운*) and removal of contentless openers/closers.
- **Flag & Suggest** — lower-confidence calls (hyperbole, vague authority, foresight filler) are flagged with a suggestion instead of auto-edited, so you stay in control.
- **AI score** — combines pattern density, connector frequency, punctuation rate, and sentence-length **burstiness** (uniform rhythm is a strong machine signal).

Because it is deterministic, the same input always yields the same output — instantly, offline, and free.

See **[PATTERNS.md](PATTERNS.md)** for the full Korean (P01–P14) and English (E01–E14) pattern catalogue.

## Intended use / Not intended for

**Intended:** improving your own writing, learning common AI-writing patterns, and editorial or teaching review of drafts.
**Not intended:** submitting AI-generated work as human-authored, academic dishonesty, or circumventing any institution's AI policy.

## Credits

- Pattern approach inspired by the English **[stop-slop](https://github.com/hardikpandya/stop-slop)** (MIT).
- Pattern descriptions reference the Wikipedia **"Signs of AI writing"** editing guide (CC BY-SA 4.0).
- Korean-signal rationale draws on **KatFishNet** (ACL 2025, [arXiv:2503.00032](https://arxiv.org/abs/2503.00032)).

See [NOTICE](NOTICE) for details. No third-party text is redistributed in this repo.

## License

[MIT](LICENSE) © 2026 webdosa123
