<h1 align="center">deslop</h1>

<p align="center"><strong>Strip the AI slop. Keep your meaning.</strong></p>

<p align="center">
  <b>English</b> · <a href="README_KR.md">한국어</a>
</p>

<p align="center">
A Korean and English writing tool that finds AI-sounding prose, cleans it up, and tells you why it sounded that way. Runs locally. No API key.
</p>

<p align="center">
  <img alt="License: MIT" src="https://img.shields.io/badge/License-MIT-yellow.svg">
  <img alt="Python" src="https://img.shields.io/badge/python-3.10%2B-blue.svg">
  <img alt="Offline" src="https://img.shields.io/badge/offline-no%20API%20key-green.svg">
  <img alt="Deps" src="https://img.shields.io/badge/core%20deps-none-green.svg">
</p>

---

> deslop is for writing better and learning AI's tells. Paste a draft, see which habits make it read as machine-written, and fix them.
>
> It is not built to fool AI detectors or to pass AI text off as your own writing. That use is out of scope.

---

## What it does

deslop reads Korean or English prose and looks for the habits that give AI writing away. The ones that are always safe to change, it changes for you. The rest it flags, with a suggestion, so you decide. It also explains the reasoning, which is the part most tools skip.

Everything runs in plain Python on your machine. There is no network call, and the core library has nothing to install.

| | |
|---|---|
| ✍️ **humanize** | Replaces clear AI-isms automatically, and flags the judgment calls for review. |
| 🔍 **detect** | Scores text 0–100 for how dense the AI patterns are. Single, A/B, or revision-tracking. |
| 📚 **coach** | Goes pattern by pattern: what's off, why it reads as AI, and how you'd fix it. |

A score on its own doesn't teach you much. "This sentence stacks three buzzwords; swap them for the detail that proves your point" does.

## How good is the score, really?

The AI score measures the density of *known* AI-writing tics. It is not a forensic detector. Here is roughly what the bundled samples produce, which you can reproduce with `pytest`:

| | per-sample score | avg |
|---|---|---|
| 🇰🇷 Korean, AI-sounding | 85, 76 | 62.6 |
| 🇰🇷 Korean, human | 5, 0, 11 | 5.4 |
| 🇺🇸 English, AI-sounding | 55, 37 | 46.1 |
| 🇺🇸 English, human | 0, 4 | 1.9 |

Obvious AI text and obvious human text separate cleanly, by about 57 points in Korean and 44 in English.

What it misses: a draft that has already been edited, or written in a deliberately plain voice, can score low and slip past. English is also weaker than Korean right now, with a narrower gap, and that's on the list to improve. None of this is Turnitin or GPTZero. The number points you at rough spots. It does not certify anything.

## Install

```bash
git clone https://github.com/webdosa123/deslop.git
cd deslop
# The library and CLI need nothing but Python's standard library.
# Streamlit is only for the optional web demo:
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

It is rules and arithmetic, no machine learning and no model behind it.

Safe Auto handles the changes that can't really go wrong: swapping inflated words for plain ones (*leverage* to *use*, *혁신적인* to *새로운*), and deleting openers and closers that carry no content. Anything riskier, like hyperbole or vague appeals to authority, gets flagged instead of edited, so you stay in control. The score itself blends a few signals: how often patterns show up, how many sentences open with a connector, the punctuation rate, and how uniform the sentence lengths are. That last one, burstiness, matters more than people expect, because even sentence length is a giveaway.

Same input, same output, every time. See **[PATTERNS.md](PATTERNS.md)** for the full Korean (P01–P14) and English (E01–E14) catalogue.

## Intended use

Use it to improve your own drafts, to learn what AI writing tends to look like, or to review other people's drafts as an editor or teacher.

Don't use it to submit AI work as your own, to get around an academic policy, or anything in that direction.

## Credits

The pattern approach started from the English [stop-slop](https://github.com/hardikpandya/stop-slop) (MIT). The descriptions in PATTERNS.md draw on Wikipedia's "Signs of AI writing" guide (CC BY-SA 4.0). The case for Korean-specific signals comes from KatFishNet (ACL 2025, [arXiv:2503.00032](https://arxiv.org/abs/2503.00032)).

See [NOTICE](NOTICE) for the details. No third-party text is shipped in this repo.

## License

[MIT](LICENSE) © 2026 webdosa123
