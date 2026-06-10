"""
humanizer_engine.py — Rule-based AI writing pattern detector and humanizer.
Implements English (E01–E14) and Korean (P01–P14) patterns from humanizer-en.md / humanizer-ko.md.
No LLM/API required. Pure Python regex + statistics.
"""

from __future__ import annotations

import argparse
import json
import math
import re
import sys
from dataclasses import dataclass, field, asdict
from typing import Optional


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class Change:
    pattern_id: str
    description: str


@dataclass
class Flag:
    pattern_id: str
    original: str
    suggestion: str
    sentence_idx: int


@dataclass
class Metrics:
    sentence_count: int
    pattern_density: float
    connector_freq: float
    punct_per_sentence: float
    burstiness: float
    ai_score: float


@dataclass
class HumanizerResult:
    lang: str
    original_text: str
    converted_text: str
    safe_auto_changes: list[Change] = field(default_factory=list)
    flags: list[Flag] = field(default_factory=list)
    metrics_before: Optional[Metrics] = None
    metrics_after: Optional[Metrics] = None


# ---------------------------------------------------------------------------
# Sentence splitters
# ---------------------------------------------------------------------------

_EN_ABBREVS = re.compile(
    r"\b(Mr|Mrs|Ms|Dr|Prof|Sr|Jr|vs|etc|Inc|Ltd|Corp|Fig|approx|dept|est|"
    r"govt|approx|misc|Mon|Tue|Wed|Thu|Fri|Sat|Sun|Jan|Feb|Mar|Apr|Jun|Jul|"
    r"Aug|Sep|Oct|Nov|Dec)\.",
    re.IGNORECASE,
)

def split_sentences_en(text: str) -> list[str]:
    # Temporarily replace abbreviation periods to protect them
    protected = _EN_ABBREVS.sub(lambda m: m.group(0).replace(".", "\x00"), text)
    # Split on sentence-ending punctuation followed by whitespace + capital or end
    parts = re.split(r'(?<=[.!?])\s+(?=[A-Z\"\'\(])', protected)
    # Restore protected periods
    sentences = [p.replace("\x00", ".").strip() for p in parts if p.strip()]
    return sentences


def split_sentences_ko(text: str) -> list[str]:
    """Split Korean text into sentences, preserving sentence-ending punctuation."""
    # Strategy: find split points — whitespace after Korean sentence endings
    # Korean endings: 다, 요, 죠, 음, 겠, 지 followed by optional [.!?] then whitespace
    # Use a split-on-whitespace-after-ending approach, keeping the ending in the left part
    result = []
    # First split on explicit punctuation boundaries
    parts = re.split(r'(?<=[.!?])\s+', text)
    for part in parts:
        # Within each part, split on Korean-specific endings followed by space
        sub_parts = re.split(r'(?<=[다요죠음겠지])\s+(?=[가-힣])', part)
        result.extend(sub_parts)
    return [s.strip() for s in result if s.strip()]


# ---------------------------------------------------------------------------
# Metrics calculation
# ---------------------------------------------------------------------------

def _word_count(sentence: str) -> int:
    return len(sentence.split())


def _burstiness(sentences: list[str]) -> float:
    counts = [_word_count(s) for s in sentences if s.strip()]
    if len(counts) < 2:
        return 0.0
    mean = sum(counts) / len(counts)
    if mean == 0:
        return 0.0
    variance = sum((c - mean) ** 2 for c in counts) / len(counts)
    std = math.sqrt(variance)
    return (std / mean) * 100


def _ai_score(pattern_density: float, connector_freq: float,
               punct_per_sentence: float, burstiness: float,
               sentence_count: int = 10) -> float:
    # Burstiness penalty is unreliable for < 3 sentences — scale it down
    burst_scale = min(1.0, sentence_count / 3.0)
    score = (
        min(50.0, pattern_density * 25)
        + min(20.0, connector_freq * 40)
        + min(15.0, punct_per_sentence * 15)
        + max(0.0, (40 - burstiness) * 0.75) * burst_scale
    )
    return round(score, 2)


def _strip_review_markers(text: str) -> str:
    """Remove [[Review:...]] and [[검토:...]] inline markers for punctuation counting."""
    return re.sub(r'\[\[(?:Review|검토):[^\]]*\]\]', '', text)


def compute_metrics_en(text: str, pattern_count: int, connector_count: int) -> Metrics:
    clean = _strip_review_markers(text)
    sentences = split_sentences_en(clean)
    sc = max(1, len(sentences))
    pd = pattern_count / sc
    cf = connector_count / sc
    em_dashes = clean.count("—")
    pps = em_dashes / sc
    burst = _burstiness(sentences)
    return Metrics(
        sentence_count=sc,
        pattern_density=round(pd, 2),
        connector_freq=round(cf, 2),
        punct_per_sentence=round(pps, 2),
        burstiness=round(burst, 2),
        ai_score=_ai_score(pd, cf, pps, burst, sc),
    )


def compute_metrics_ko(text: str, pattern_count: int, connector_count: int) -> Metrics:
    clean = _strip_review_markers(text)
    sentences = split_sentences_ko(clean)
    sc = max(1, len(sentences))
    pd = pattern_count / sc
    cf = connector_count / sc
    commas = clean.count(",") + clean.count("，")
    pps = commas / sc
    burst = _burstiness(sentences)
    return Metrics(
        sentence_count=sc,
        pattern_density=round(pd, 2),
        connector_freq=round(cf, 2),
        punct_per_sentence=round(pps, 2),
        burstiness=round(burst, 2),
        ai_score=_ai_score(pd, cf, pps, burst, sc),
    )


# ---------------------------------------------------------------------------
# English Safe Auto patterns
# ---------------------------------------------------------------------------

_EN_CONNECTORS = [
    "Furthermore", "Moreover", "Additionally", "In addition",
    "Therefore", "Thus", "Consequently", "As a result", "Hence",
    "Firstly", "Secondly", "Thirdly", "Finally",
    "In terms of", "With regard to", "Regarding",
]

_EN_CONNECTOR_PATTERN = re.compile(
    r'^(' + '|'.join(re.escape(c) for c in _EN_CONNECTORS) + r')[,\s]+',
    re.IGNORECASE | re.MULTILINE,
)

_EN_OPENER_RE = re.compile(
    r"(?:in this article[,\s]+we(?:'ll|'ll| will)\s+explore|"
    r"let(?:'s|'s)\s+dive\s+into|"
    r"today[,\s]+we(?:'re|'re| are)\s+going\s+to|"
    r"in this guide[,\s]+we(?:'ll|'ll| will)\s+cover)",
    re.IGNORECASE,
)

_EN_CLOSER_RE = re.compile(
    r"(?:in conclusion[,\s]|to summarize[,\s]|"
    r"i hope this (?:helps|article|was)|feel free to ask|"
    r"that(?:'s|'s| is) everything you need to know)",
    re.IGNORECASE,
)

_EN_FORMULAIC = [
    (re.compile(r'\bIt is important to note that\s+', re.IGNORECASE), ""),
    (re.compile(r'\bIt is worth noting that\s+', re.IGNORECASE), ""),
    (re.compile(r'\bIt should be noted that\s+', re.IGNORECASE), ""),
    (re.compile(r'\bIt is worth mentioning that\s+', re.IGNORECASE), ""),
    (re.compile(r'\bIt goes without saying that\s+', re.IGNORECASE), ""),
    (re.compile(r'\bAs mentioned above[,\s]*', re.IGNORECASE), ""),
    (re.compile(r'\bThe aforementioned\b', re.IGNORECASE), "the"),
    (re.compile(r'\bAs previously stated[,\s]*', re.IGNORECASE), ""),
    (re.compile(r'\bFrom a \w+ perspective[,\s]*', re.IGNORECASE), ""),
    (re.compile(r'\bIn the context of\s+', re.IGNORECASE), ""),
    (re.compile(r'\bThis is particularly true when\s+', re.IGNORECASE), ""),
]

_EN_MODIFIER_STACKS = re.compile(
    r'\b(highly|very|extremely|absolutely|truly|deeply|incredibly)\s+'
    r'(important|crucial|essential|remarkable|innovative|powerful|exceptional|fundamental|impactful)\b',
    re.IGNORECASE,
)

_EN_MOST_REDUNDANT = re.compile(r'\b(most\s+optimal|most\s+unique)\b', re.IGNORECASE)

_EN_CHATBOT_RE = re.compile(
    r'(?:I hope this helps|I hope you found this (?:helpful|useful)|'
    r'Feel free to ask if (?:you have any|you need)|'
    r'Let me know if you need any|'
    r'As an AI (?:language model|,)|'
    r'Please note that this is not professional advice)',
    re.IGNORECASE,
)

_EN_COMMA_AFTER_CONNECTOR = re.compile(
    r'\b(' + '|'.join(re.escape(c) for c in _EN_CONNECTORS) + r'),\s+',
    re.IGNORECASE,
)

_EN_EMDASH_CLAUSE = re.compile(r'\s*—\s*([A-Z])')

# E06 T1 — mechanical synonym substitutions (Safe Auto, no judgment needed)
_EN_E06_AUTO = [
    (re.compile(r'\butilize\b', re.IGNORECASE),       "use"),
    (re.compile(r'\butilized\b', re.IGNORECASE),      "used"),
    (re.compile(r'\butilizing\b', re.IGNORECASE),     "using"),
    (re.compile(r'\butilization\b', re.IGNORECASE),   "use"),
    (re.compile(r'\bleverage\b(?!\s+(?:ratio|point|buyout))', re.IGNORECASE), "use"),
    (re.compile(r'\bleveraged\b', re.IGNORECASE),     "used"),
    (re.compile(r'\bleveraging\b', re.IGNORECASE),    "using"),
    (re.compile(r'\bfoster\b', re.IGNORECASE),        "build"),
    (re.compile(r'\bfostering\b', re.IGNORECASE),     "building"),
    (re.compile(r'\bunderscore\b', re.IGNORECASE),    "highlight"),
    (re.compile(r'\bunderscored\b', re.IGNORECASE),   "highlighted"),
    (re.compile(r'\bunderscoring\b', re.IGNORECASE),  "highlighting"),
    (re.compile(r'\bdelve into\b', re.IGNORECASE),    "look into"),
    (re.compile(r'\bdelve\b', re.IGNORECASE),         "examine"),
    (re.compile(r'\bdelved\b', re.IGNORECASE),        "examined"),
    (re.compile(r'\bdelving\b', re.IGNORECASE),       "examining"),
    (re.compile(r'\bthe realm of\b', re.IGNORECASE),  "the field of"),
    (re.compile(r'\brealm\b', re.IGNORECASE),         "area"),
    (re.compile(r'\bnavigate\b', re.IGNORECASE),      "handle"),
    (re.compile(r'\bnavigating\b', re.IGNORECASE),    "handling"),
    (re.compile(r'\bnavigated\b', re.IGNORECASE),     "handled"),
    (re.compile(r'\bthe \w+ landscape\b', re.IGNORECASE), lambda m: m.group(0).replace("landscape", "environment")),
    (re.compile(r'\blandscape\b', re.IGNORECASE),     "environment"),
    (re.compile(r'\bharness\b', re.IGNORECASE),       "use"),
    (re.compile(r'\bharnessing\b', re.IGNORECASE),    "using"),
    (re.compile(r'\bcurate\b', re.IGNORECASE),        "select"),
    (re.compile(r'\bcurated\b', re.IGNORECASE),       "selected"),
    (re.compile(r'\bunpack\b', re.IGNORECASE),        "explain"),
    (re.compile(r'\belevate\b', re.IGNORECASE),       "improve"),
    (re.compile(r'\belevating\b', re.IGNORECASE),     "improving"),
    # T2 — additional AI buzzwords with unambiguous, register-safe replacements
    (re.compile(r'\brobust\b', re.IGNORECASE),          "strong"),
    (re.compile(r'\bcomprehensive\b', re.IGNORECASE),   "thorough"),
    (re.compile(r'\bcomprehensively\b', re.IGNORECASE), "thoroughly"),
    (re.compile(r'\bholistic\b', re.IGNORECASE),        "overall"),
    (re.compile(r'\bholistically\b', re.IGNORECASE),    "overall"),
    (re.compile(r'\bintricate\b', re.IGNORECASE),       "complex"),
    (re.compile(r'\bnuanced\b', re.IGNORECASE),         "detailed"),
    (re.compile(r'\bmultifaceted\b', re.IGNORECASE),    "complex"),
    (re.compile(r'\bimpactful\b', re.IGNORECASE),      "effective"),
    (re.compile(r'\bactionable\b', re.IGNORECASE),     "practical"),
    (re.compile(r'\bseamless\b', re.IGNORECASE),       "smooth"),
    (re.compile(r'\bseamlessly\b', re.IGNORECASE),     "smoothly"),
    (re.compile(r'\bstreamline\b', re.IGNORECASE),     "simplify"),
    (re.compile(r'\bstreamlined\b', re.IGNORECASE),    "simplified"),
    (re.compile(r'\bstreamlining\b', re.IGNORECASE),   "simplifying"),
    (re.compile(r'\bempower\b', re.IGNORECASE),        "enable"),
    (re.compile(r'\bempowering\b', re.IGNORECASE),     "enabling"),
    (re.compile(r'\bempowered\b', re.IGNORECASE),      "enabled"),
    (re.compile(r'\bfacilitate\b', re.IGNORECASE),     "help"),
    (re.compile(r'\bfacilitating\b', re.IGNORECASE),   "helping"),
    (re.compile(r'\bfacilitated\b', re.IGNORECASE),    "helped"),
    (re.compile(r'\bendeavor\b', re.IGNORECASE),       "effort"),
    (re.compile(r'\bendeavors\b', re.IGNORECASE),      "efforts"),
    (re.compile(r'\bsynergy\b', re.IGNORECASE),        "combination"),
    (re.compile(r'\bsynergies\b', re.IGNORECASE),      "combinations"),
]

# E09 — misconception opener stripping (sentence start → strip prefix)
_EN_E09_OPENER_STRIP = re.compile(
    r'^(Contrary\s+to\s+popular\s+belief|Despite\s+what\s+you\s+may\s+have\s+heard)[,\s]+',
    re.IGNORECASE
)

# E11 — foresight opener stripping (sentence start → strip prefix)
_EN_E11_OPENER_STRIP = re.compile(
    r'^(Moving\s+forward|Looking\s+ahead|As\s+we\s+look\s+to\s+the\s+future|'
    r'As\s+technology\s+continues\s+to\s+evolve|'
    r'In\s+an\s+ever[-\s]changing\s+world)[,\s]+',
    re.IGNORECASE
)

# E11 — "has the potential to" → "can"
_EN_HAS_POTENTIAL_RE = re.compile(r'\bhas\s+the\s+potential\s+to\b', re.IGNORECASE)

# E05 — mechanical removal of strongest AI adjectives (Safe Auto)
_EN_E05_AUTO = [
    (re.compile(r'\bgroundbreaking\b', re.IGNORECASE),    "new"),
    (re.compile(r'\brevolutionary\b', re.IGNORECASE),     "new"),
    (re.compile(r'\btransformative\b', re.IGNORECASE),    "significant"),
    (re.compile(r'\bunprecedented\b', re.IGNORECASE),     "new"),
    (re.compile(r'\bextraordinary\b', re.IGNORECASE),     "strong"),
    (re.compile(r'\bparadigm.?shift\b', re.IGNORECASE),   "major change"),
    (re.compile(r'\bcutting.?edge\b', re.IGNORECASE),     "modern"),
    (re.compile(r'\bparamount\b', re.IGNORECASE),         "key"),
    (re.compile(r'\bpivotal\b', re.IGNORECASE),           "key"),
    (re.compile(r'\bremarkable\b', re.IGNORECASE),        "notable"),
    (re.compile(r'\bexceptional\b', re.IGNORECASE),       "strong"),
    (re.compile(r'\bgame-changing\b', re.IGNORECASE),     "major"),
    (re.compile(r'\bdisruptive\b', re.IGNORECASE),        "significant"),
    (re.compile(r'\brevolutionized\b', re.IGNORECASE),    "changed"),
    (re.compile(r'\brevolutionize\b', re.IGNORECASE),     "change"),
    (re.compile(r'\brevolutionizing\b', re.IGNORECASE),   "changing"),
]


def _apply_en_safe_auto(text: str) -> tuple[str, list[Change], int, int]:
    changes: list[Change] = []
    connector_count = 0
    pattern_count = 0

    # Detect whether text has paragraph structure or is inline
    has_newlines = '\n' in text

    # E03/E12 — delete opener, closer, chatbot sentences by splitting first
    sentences = split_sentences_en(text)
    kept: list[str] = []
    opener_deleted = 0
    closer_deleted = 0
    chatbot_deleted = 0

    for i, sent in enumerate(sentences):
        s = sent.strip()
        if _EN_OPENER_RE.search(s):
            opener_deleted += 1
            pattern_count += 1
        elif _EN_CLOSER_RE.search(s):
            closer_deleted += 1
            pattern_count += 1
        elif _EN_CHATBOT_RE.search(s):
            chatbot_deleted += 1
            pattern_count += 1
        else:
            kept.append(sent)

    if opener_deleted:
        changes.append(Change("E03", f"Lecture opener(s) deleted ({opener_deleted})"))
    if closer_deleted:
        changes.append(Change("E03", f"Lecture/chatbot closer(s) deleted ({closer_deleted})"))
    if chatbot_deleted:
        changes.append(Change("E12", f"Chatbot expression(s) deleted ({chatbot_deleted})"))

    # Reconstruct text preserving paragraph breaks if original had them
    if has_newlines:
        text = '\n\n'.join(kept)
    else:
        text = ' '.join(kept)

    # E13 — remove comma after connectors
    comma_matches = _EN_COMMA_AFTER_CONNECTOR.findall(text)
    if comma_matches:
        text = _EN_COMMA_AFTER_CONNECTOR.sub(lambda m: m.group(1) + " ", text)
        changes.append(Change("E13", f"Comma after connector removed ({len(comma_matches)}x)"))

    # E13 — em-dash as sentence separator (before capital) → period
    # Skip if sentence already contains 2+ em-dashes (parenthetical pair — human style)
    def replace_emdash(m: re.Match) -> str:
        return ". " + m.group(1)
    em_clause_candidates = []
    for sent in split_sentences_en(text):
        if sent.count("—") == 1 and _EN_EMDASH_CLAUSE.search(sent):
            em_clause_candidates.append(sent)
    em_count = len(em_clause_candidates)
    if em_count:
        text = _EN_EMDASH_CLAUSE.sub(replace_emdash, text)
        text = re.sub(r'\s*—\s*', ', ', text)
        changes.append(Change("E13", f"Em-dash(es) replaced with period/comma ({em_count}x)"))

    # E01 — count connector starts before stripping
    found_connectors: dict[str, int] = {}
    for s in split_sentences_en(text):
        m = _EN_CONNECTOR_PATTERN.match(s.strip())
        if m:
            key = m.group(1).lower()
            found_connectors[key] = found_connectors.get(key, 0) + 1
    total_connector_starts = sum(found_connectors.values())
    connector_count = total_connector_starts
    if total_connector_starts >= 3:
        # Strip connector from sentence starts
        def strip_connector(sentence: str) -> str:
            return _EN_CONNECTOR_PATTERN.sub("", sentence).strip()
        rebuilt: list[str] = []
        for s in split_sentences_en(text):
            stripped = _EN_CONNECTOR_PATTERN.sub("", s.strip())
            # Capitalize first letter
            if stripped:
                stripped = stripped[0].upper() + stripped[1:]
            rebuilt.append(stripped)
        text = (' ' if not has_newlines else '\n\n').join(rebuilt)
        connector_names = ", ".join(
            f"{k.title()} x{v}" for k, v in found_connectors.items() if v >= 1
        )
        changes.append(Change("E01", f"Connectors stripped from sentence starts ({connector_names})"))
        pattern_count += total_connector_starts

    # E08 — collapse modifier stacks
    mod_matches = _EN_MODIFIER_STACKS.findall(text)
    if mod_matches:
        # Include article context to fix "an extremely important" -> "an important" (not "a important")
        def collapse_modifier(m: re.Match) -> str:
            return m.group(2)
        text = _EN_MODIFIER_STACKS.sub(collapse_modifier, text)
        # Fix article agreement: "a/an" before wrong vowel/consonant start
        def fix_article(m: re.Match) -> str:
            art = m.group(1)
            word = m.group(2)
            correct = "an" if word[0].lower() in "aeiou" else "a"
            return correct + " " + word
        text = re.sub(r'\b(a|an)\s+([a-zA-Z])', fix_article, text, flags=re.IGNORECASE)
        for pair in mod_matches:
            changes.append(Change("E08", f'"{pair[0]} {pair[1]}" -> "{pair[1]}"'))
        pattern_count += len(mod_matches)

    redundant_matches = _EN_MOST_REDUNDANT.findall(text)
    if redundant_matches:
        def fix_redundant(m: re.Match) -> str:
            return m.group(0).split()[-1]
        text = _EN_MOST_REDUNDANT.sub(fix_redundant, text)
        for r in redundant_matches:
            changes.append(Change("E08", f'"{r}" -> "{r.split()[-1]}"'))
        pattern_count += len(redundant_matches)

    # E04 — remove formulaic phrases
    for pat, replacement in _EN_FORMULAIC:
        matches = pat.findall(text)
        if matches:
            text = pat.sub(replacement, text)
            changes.append(Change("E04", f"Formulaic phrase removed ({len(matches)}x)"))
            pattern_count += len(matches)

    # E06 — T1 AI vocabulary: mechanical synonym substitution
    e06_replaced: list[str] = []
    for pat, repl in _EN_E06_AUTO:
        if callable(repl):
            hits = pat.findall(text)
            if hits:
                text = pat.sub(repl, text)
                e06_replaced.extend(hits)
        else:
            hits = pat.findall(text)
            if hits:
                text = pat.sub(repl, text)
                e06_replaced.extend(hits)
    if e06_replaced:
        changes.append(Change("E06", f"AI vocab replaced ({len(e06_replaced)}x: {', '.join(dict.fromkeys(h.lower() for h in e06_replaced))})"))
        pattern_count += len(e06_replaced)

    # E05 — strongest AI adjectives: mechanical replacement with neutral alternatives
    e05_replaced: list[str] = []
    for pat, repl in _EN_E05_AUTO:
        hits = pat.findall(text)
        if hits:
            text = pat.sub(repl, text)
            e05_replaced.extend(hits)
    if e05_replaced:
        changes.append(Change("E05", f"AI adjectives replaced ({len(e05_replaced)}x: {', '.join(dict.fromkeys(h.lower() for h in e05_replaced))})"))
        pattern_count += len(e05_replaced)

    # E09 — strip misconception opener phrases from sentence starts
    sentences = split_sentences_en(text)
    e09_stripped = 0
    rebuilt: list[str] = []
    for s in sentences:
        m = _EN_E09_OPENER_STRIP.match(s.strip())
        if m:
            rest = _EN_E09_OPENER_STRIP.sub('', s.strip()).strip()
            if rest:
                rest = rest[0].upper() + rest[1:]
                rebuilt.append(rest)
                e09_stripped += 1
        else:
            rebuilt.append(s)
    if e09_stripped:
        text = (' ' if not has_newlines else '\n\n').join(rebuilt)
        changes.append(Change("E09", f"Misconception opener stripped ({e09_stripped}x)"))
        pattern_count += e09_stripped

    # E11 — strip foresight opener phrases from sentence starts
    sentences = split_sentences_en(text)
    e11_stripped = 0
    rebuilt = []
    for s in sentences:
        m = _EN_E11_OPENER_STRIP.match(s.strip())
        if m:
            rest = _EN_E11_OPENER_STRIP.sub('', s.strip()).strip()
            if rest:
                rest = rest[0].upper() + rest[1:]
                rebuilt.append(rest)
                e11_stripped += 1
        else:
            rebuilt.append(s)
    if e11_stripped:
        text = (' ' if not has_newlines else '\n\n').join(rebuilt)
        changes.append(Change("E11", f"Foresight opener stripped ({e11_stripped}x)"))
        pattern_count += e11_stripped

    # E11 — "has the potential to" → "can"
    potential_hits = _EN_HAS_POTENTIAL_RE.findall(text)
    if potential_hits:
        text = _EN_HAS_POTENTIAL_RE.sub('can', text)
        changes.append(Change("E11", f"'has the potential to' → 'can' ({len(potential_hits)}x)"))
        pattern_count += len(potential_hits)

    # Capitalize sentence starts after connector removal
    text = re.sub(r'(?<=[.!?] )([a-z])', lambda m: m.group(1).upper(), text)
    text = re.sub(r'\n([a-z])', lambda m: '\n' + m.group(1).upper(), text)
    text = re.sub(r' {2,}', ' ', text)
    text = re.sub(r'\n{3,}', '\n\n', text).strip()

    # Recount connector starts in the final text (post-auto) for accurate metrics
    post_conn_count = sum(
        1 for s in split_sentences_en(text)
        if _EN_CONNECTOR_PATTERN.match(s.strip())
    )
    connector_count = post_conn_count

    return text, changes, pattern_count, connector_count


# ---------------------------------------------------------------------------
# English Flag patterns
# ---------------------------------------------------------------------------

_E05_WORDS = [
    "groundbreaking", "revolutionary", "transformative", "game-changing",
    "unprecedented", "remarkable", "extraordinary", "exceptional",
    "paradigm shift", "cutting-edge", "disruptive",
]
_E05_PATTERN = re.compile(
    r'\b(' + '|'.join(re.escape(w) for w in _E05_WORDS) + r')\b',
    re.IGNORECASE,
)

_E06_T1 = {
    "delve": "look at / examine / delete",
    "tapestry": "pattern / mix / delete",
    "nuanced": "detailed / specific / delete",
    "multifaceted": "complex / multi-part / delete",
    "leverage": "use / apply",
    "foster": "build / encourage / develop",
    "underscore": "highlight / show / emphasize",
    "realm": "area / field / domain",
    "navigate": "handle / manage / work through",
    "landscape": "field / environment / sector",
    # 추가 T1
    "unpack": "explain / examine / delete",
    "curate": "choose / select / delete",
    "harness": "use / apply",
    "catalyze": "trigger / start / drive",
    "synergize": "combine / work together",
    "elevate": "improve / raise / delete",
    "supercharge": "boost / improve",
    "groundbreaking": "new / important / delete",
}
_E06_T2 = [
    # T2 remaining — not in E05 Auto, context-dependent meaning
    "inaugural", "bespoke", "scalable", "innovative", "ecosystem",
]
_E06_T1_PATTERN = re.compile(
    r'\b(' + '|'.join(re.escape(w) for w in _E06_T1.keys()) + r')\b',
    re.IGNORECASE,
)
_E06_T2_PATTERN = re.compile(
    r'\b(' + '|'.join(re.escape(w) for w in _E06_T2) + r')\b',
    re.IGNORECASE,
)

_E09_PATTERNS = [
    re.compile(r'\bcontrary to popular belief\b', re.IGNORECASE),
    re.compile(r'\bmany people think .{1,60} but actually\b', re.IGNORECASE),
    re.compile(r'\bdespite what you may have heard\b', re.IGNORECASE),
    re.compile(r'(?:^|\. )the truth is\b', re.IGNORECASE),
]

_E10_PATTERNS = [
    re.compile(r'\bmany experts (?:suggest|say|believe)\b', re.IGNORECASE),
    re.compile(r'\bstudies show\b', re.IGNORECASE),
    re.compile(r'\bresearch (?:indicates|shows)\b', re.IGNORECASE),
    re.compile(r'\bit is widely (?:accepted|known)\b', re.IGNORECASE),
    re.compile(r'\bexperts believe\b', re.IGNORECASE),
    re.compile(r'\bscience confirms\b', re.IGNORECASE),
]

_E11_PATTERNS = [
    re.compile(r'\bmoving forward\b', re.IGNORECASE),
    re.compile(r'\blooking ahead\b', re.IGNORECASE),
    re.compile(r'\bas we look to the future\b', re.IGNORECASE),
    re.compile(r'\bhas the potential to\b', re.IGNORECASE),
    re.compile(r'\bchallenges remain but\b', re.IGNORECASE),
    re.compile(r'\bas technology continues to evolve\b', re.IGNORECASE),
    re.compile(r'\bin an ever-changing world\b', re.IGNORECASE),
]

_E02_PATTERNS = [
    re.compile(r'\bit is imperative that\b', re.IGNORECASE),
    re.compile(r'\bone must\b', re.IGNORECASE),
    re.compile(r'\bit behooves\b', re.IGNORECASE),
]

# E03b — AI content-marketing / SEO-blog clichés. Multi-word phrases that are
# heavily over-represented in machine-written blog, marketing, and listicle copy
# and rare in genuine human prose (casual or literary). Detection-only signals.
_EN_CLICHE_PATTERNS = [
    re.compile(r"\bin this (?:comprehensive |ultimate |complete |detailed |step-by-step )?(?:guide|post|article|tutorial)\b", re.IGNORECASE),
    re.compile(r"\blet'?s dive (?:right )?in\b", re.IGNORECASE),
    re.compile(r"\bby the end of this (?:guide|post|article|tutorial|video)\b", re.IGNORECASE),
    re.compile(r"\bwe'?ll (?:walk|take) you through\b", re.IGNORECASE),
    re.compile(r"\beverything you need to know\b", re.IGNORECASE),
    re.compile(r"\bhave you ever (?:wanted|wondered|felt|struggled|thought)\b", re.IGNORECASE),
    re.compile(r"\bare you (?:looking|tired|ready|struggling)\b", re.IGNORECASE),
    re.compile(r"\byou'?re not alone\b", re.IGNORECASE),
    re.compile(r"\bhidden gems\b", re.IGNORECASE),
    re.compile(r"\boff the beaten path\b", re.IGNORECASE),
    re.compile(r"\b(?:take your breath away|breathtaking)\b", re.IGNORECASE),
    re.compile(r"\bunlock (?:the |your )?(?:power|potential|secret|full)\b", re.IGNORECASE),
    re.compile(r"\btake your \w+ to the next level\b", re.IGNORECASE),
    re.compile(r"\blook no further\b", re.IGNORECASE),
    re.compile(r"\bwhether you'?re an? \w+ or\b", re.IGNORECASE),
    re.compile(r"\bno longer optional\b", re.IGNORECASE),
    re.compile(r"\b(?:has|have) never been (?:more|easier|simpler)\b", re.IGNORECASE),
    re.compile(r"\bstate-of-the-art\b", re.IGNORECASE),
    re.compile(r"\bso grab your\b", re.IGNORECASE),
    re.compile(r"\blet'?s get started\b", re.IGNORECASE),
    re.compile(r"\bwe'?ve rounded up\b", re.IGNORECASE),
    re.compile(r"\bmust-(?:see|visit|try|have|read)\b", re.IGNORECASE),
    re.compile(r"\bin today'?s (?:fast-paced|rapidly evolving|ever-changing|ever-evolving|digital|modern|competitive|connected) \w+\b", re.IGNORECASE),
    re.compile(r"\bnow more than ever\b", re.IGNORECASE),
    re.compile(r"\bstay ahead of the (?:curve|competition|game)\b", re.IGNORECASE),
    re.compile(r"\bset (?:you|yourself|your \w+) apart\b", re.IGNORECASE),
]


def _apply_en_flags(text: str, sentences: list[str]) -> tuple[str, list[Flag], int]:
    flags: list[Flag] = []
    flag_pattern_count = 0

    # E05
    for i, sent in enumerate(sentences):
        for m in _E05_PATTERN.finditer(sent):
            word = m.group(1)
            marker = f'[[Review: E05 — "{word}" → delete or replace with specific claim showing why it\'s notable]]'
            text = text.replace(word, marker + word, 1)
            flags.append(Flag("E05", word, "delete or replace with specific claim", i))
            flag_pattern_count += 1

    # E06 Tier 1 — always flag
    for i, sent in enumerate(sentences):
        for m in _E06_T1_PATTERN.finditer(sent):
            word = m.group(1).lower()
            suggestion = _E06_T1.get(word, "simpler alternative")
            marker = f'[[Review: E06 — "{m.group(1)}" → {suggestion}]]'
            text = text.replace(m.group(1), marker + m.group(1), 1)
            flags.append(Flag("E06", m.group(1), suggestion, i))
            flag_pattern_count += 1

    # E06 Tier 2 — flag if 4+ in document
    t2_matches = _E06_T2_PATTERN.findall(text.lower())
    if len(t2_matches) >= 4:
        for i, sent in enumerate(sentences):
            for m in _E06_T2_PATTERN.finditer(sent):
                word = m.group(1)
                marker = f'[[Review: E06 — "{word}" → simpler word]]'
                text = text.replace(word, marker + word, 1)
                flags.append(Flag("E06", word, "simpler word", i))
                flag_pattern_count += 1

    # E09
    for i, sent in enumerate(sentences):
        for pat in _E09_PATTERNS:
            m = pat.search(sent)
            if m:
                phrase = m.group(0)
                marker = f'[[Review: E09 — "{phrase}" → state the actual point directly]]'
                text = text.replace(phrase, phrase + " " + marker, 1)
                flags.append(Flag("E09", phrase, "state the actual point directly", i))
                flag_pattern_count += 1

    # E10
    for i, sent in enumerate(sentences):
        for pat in _E10_PATTERNS:
            m = pat.search(sent)
            if m:
                phrase = m.group(0)
                marker = f'[[Review: E10 — "{phrase}" → cite specific source or delete]]'
                text = text.replace(phrase, marker + phrase, 1)
                flags.append(Flag("E10", phrase, "cite specific source or delete", i))
                flag_pattern_count += 1

    # E11
    for i, sent in enumerate(sentences):
        for pat in _E11_PATTERNS:
            m = pat.search(sent)
            if m:
                phrase = m.group(0)
                marker = f'[[Review: E11 — "{phrase}" → delete or connect to specific evidence]]'
                text = text.replace(phrase, phrase + " " + marker, 1)
                flags.append(Flag("E11", phrase, "delete or connect to specific evidence", i))
                flag_pattern_count += 1

    # E02
    for i, sent in enumerate(sentences):
        for pat in _E02_PATTERNS:
            m = pat.search(sent)
            if m:
                phrase = m.group(0)
                marker = f'[[Review: E02 — "{phrase}" → more direct phrasing]]'
                text = text.replace(phrase, marker + phrase, 1)
                flags.append(Flag("E02", phrase, "more direct phrasing", i))
                flag_pattern_count += 1

    return text, flags, flag_pattern_count


def _check_e14(sentences: list[str]) -> Optional[Flag]:
    counts = [_word_count(s) for s in sentences if s.strip()]
    if len(counts) < 3:
        return None
    if max(counts) - min(counts) < 10 and (sum(counts) / len(counts)) > 12:
        return Flag("E14", "uniform sentence length", "add short punchy sentence(s) and/or longer explanatory sentence(s)", 0)
    return None


# ---------------------------------------------------------------------------
# Korean Safe Auto patterns
# ---------------------------------------------------------------------------

_KO_CONNECTORS = [
    "또한", "더불어", "게다가", "더욱이", "뿐만 아니라", "아울러", "나아가",
    "따라서", "그러므로", "그래서", "결과적으로", "이에 따라",
    "우선", "첫째", "둘째", "셋째", "마지막으로", "결론적으로",
]

_KO_CONNECTOR_PATTERN = re.compile(
    r'^(' + '|'.join(re.escape(c) for c in _KO_CONNECTORS) + r')[,，\s]+',
    re.MULTILINE,
)

_KO_OPENER_RE = re.compile(
    r'(?:이번 글에서는|오늘은.{0,20}에 대해 살펴보겠|'
    r'이 글에서는.{0,20}알아보겠|에 대해 알아보겠습니다|'
    r'에 대해 살펴보겠습니다|를 중심으로 설명드리겠습니다)',
)

_KO_CLOSER_RE = re.compile(
    r'(?:이상으로.{0,30}(?:마치겠습니다|정리하였습니다|살펴보았습니다|정리해보았습니다|정리해보았다|알아보았습니다|알아보았다)|'
    r'지금까지.{0,30}(?:살펴보았습니다|살펴보았다|알아보았습니다|알아보았다|정리하였습니다)|'
    r'이 글이 도움이 되었으면 합니다|도움이 되셨으면 합니다|'
    r'도움이 되시길 바랍니다|궁금한 점은 댓글로 남겨주세요)',
)

_KO_FORMULAIC = [
    (re.compile(r'본\s+(글|보고서|연구|문서)에서는'), lambda m: "이 " + m.group(1) + "에서"),
    (re.compile(r'이러한\s+맥락에서[,，\s]*'), lambda m: ""),
    (re.compile(r'위와\s+같이[,，\s]*'), lambda m: ""),
    (re.compile(r'상기'), lambda m: "앞서 언급한"),
    # 추가 번역투 패턴
    (re.compile(r'\b해당\s+(?=[가-힣])'), lambda m: "이 "),
    (re.compile(r'~관련하여[,，\s]*'), lambda m: "에 대해 "),
    (re.compile(r'~한\s+바[,\s]'), lambda m: ""),
    (re.compile(r'~인\s+바[,\s]'), lambda m: ""),
    (re.compile(r'이를\s+통해\s+알\s+수\s+있습니다'), lambda m: "확인됩니다"),
    (re.compile(r'것으로\s+나타났습니다'), lambda m: "입니다"),
    (re.compile(r'에\s+기인한\s+것으로\s+보입니다'), lambda m: "때문입니다"),
]

# P06 외래어 — 한국어 동의어로 직접 치환 (Safe Auto, 내용 판단 불필요)
_KO_P06_AUTO = [
    (re.compile(r'솔루션'), "해결책"),
    (re.compile(r'인사이트'), "시사점"),
    (re.compile(r'레버리지'), "활용"),
    (re.compile(r'프레임워크'), "기준"),
    (re.compile(r'가이드라인'), "지침"),
    (re.compile(r'이니셔티브'), "계획"),
    (re.compile(r'로드맵'), "계획"),
    (re.compile(r'퍼포먼스'), "성과"),
    (re.compile(r'모니터링'), "관리"),
    # 리더십, 커뮤니케이션, 플랫폼 — 한국어 일상어로 정착. 치환하지 않음.
    (re.compile(r'밸런스'), "균형"),
    (re.compile(r'시너지'), "상호 보완"),
    (re.compile(r'패러다임'), "방식"),
    (re.compile(r'프로세스'), "과정"),
    (re.compile(r'지속적으로'), "계속"),
    (re.compile(r'종합적으로'), "전체적으로"),
    (re.compile(r'종합적인'), "전반적인"),
]

# P05 — AI 과장 수식어 기계적 교체
_KO_P05_AUTO = [
    (re.compile(r'혁신적인\s+'), "새로운 "),
    (re.compile(r'획기적인\s+'), "새로운 "),
    (re.compile(r'필수\s*불가결'), "중요"),
    (re.compile(r'핵심적인\s+'), ""),           # 일반형 삭제 (역할·요소·방향 등 모든 명사 앞)
    (re.compile(r'필수적인\s+역할'), "역할"),
    (re.compile(r'필수적인\s+요소'), "요소"),
    (re.compile(r'주목할\s+만한\s+'), ""),
    (re.compile(r'간과해서는\s+안\s+됩니다'), "중요합니다"),
    (re.compile(r'중요한\s+역할을\s+하고\s+있습니다'), "영향을 줍니다"),
    (re.compile(r'중요한\s+역할을\s+합니다'), "영향을 줍니다"),
]

_KO_MODIFIER_STACKS = [
    (re.compile(r'매우\s+중요한\s+핵심'), "핵심"),
    (re.compile(r'매우\s+중요한'), "중요한"),
    (re.compile(r'더욱\s+더'), "더"),
    (re.compile(r'매우\s+다양한'), "다양한"),
    (re.compile(r'보다\s+더욱'), "더"),
    (re.compile(r'가장\s+최선의'), "최선의"),
    (re.compile(r'특히\s+특별히'), "특히"),
]

_KO_CHATBOT_RE = re.compile(
    r'(?:도움이 되셨으면 합니다|이 정보가 도움이 되기를 바랍니다|'
    r'추가적인 질문이 있으시면|궁금한 점이 있으시면|'
    r'제 지식의 한계로 인해|언제든지 질문해 주세요)',
)

# P11 — pure AI filler "expectation" sentences (Safe Auto deletion)
_KO_P11_FILLER_SENT = re.compile(
    r'(?:것으로\s+기대됩니다|것으로\s+전망됩니다|'
    r'것으로\s+전망합니다|것으로\s+기대합니다|'    # 능동형 추가
    r'것으로\s+예상됩니다|것으로\s+예상합니다|'
    r'하기를\s+바랍니다|기를\s+바랍니다|이기를\s+바랍니다|'
    r'더욱\s+발전할\s+것으로|더욱\s+성장할\s+것으로|'
    r'앞으로\s+더욱\s+발전|향후\s+발전이\s+기대)'
)

# Enumeration markers are normal in human writing — exclude from P13
_KO_P13_ENUM_MARKERS = {"첫째", "둘째", "셋째", "마지막으로"}
_KO_P13_CONNECTORS = [c for c in _KO_CONNECTORS if c not in _KO_P13_ENUM_MARKERS]
_KO_COMMA_AFTER_CONNECTOR = re.compile(
    r'(' + '|'.join(re.escape(c) for c in _KO_P13_CONNECTORS) + r')[,，]\s*',
)

# P01 connector stripping excludes enum markers (첫째/둘째/셋째 are legitimate in lists)
_KO_P01_CONNECTORS = [c for c in _KO_CONNECTORS if c not in _KO_P13_ENUM_MARKERS]
_KO_P01_CONNECTOR_PATTERN = re.compile(
    r'^(' + '|'.join(re.escape(c) for c in _KO_P01_CONNECTORS) + r')[,，\s]+',
    re.MULTILINE,
)

# Inline connectors — appear mid-sentence (not at start), strong AI signal when repeated
_KO_INLINE_CONN_WORDS = ["또한", "게다가", "더욱이", "아울러"]
_KO_INLINE_CONNECTOR_RE = re.compile(
    r'(?<=[가-힣])\s+(' + '|'.join(re.escape(c) for c in _KO_INLINE_CONN_WORDS) + r')\s+(?=[가-힣])'
)


def _apply_ko_safe_auto(text: str) -> tuple[str, list[Change], int, int]:
    changes: list[Change] = []
    connector_count = 0
    pattern_count = 0

    has_newlines = '\n' in text

    # P03/P12 — delete opener, closer, chatbot sentences by splitting first
    sentences = split_sentences_ko(text)
    kept: list[str] = []
    opener_deleted = 0
    closer_deleted = 0
    chatbot_deleted = 0
    p11_filler_deleted = 0

    for sent in sentences:
        s = sent.strip()
        if _KO_OPENER_RE.search(s):
            opener_deleted += 1
            pattern_count += 1
        elif _KO_CLOSER_RE.search(s):
            closer_deleted += 1
            pattern_count += 1
        elif _KO_CHATBOT_RE.search(s):
            chatbot_deleted += 1
            pattern_count += 1
        elif _KO_P11_FILLER_SENT.search(s):
            p11_filler_deleted += 1
            pattern_count += 1
        else:
            kept.append(sent)

    if opener_deleted:
        changes.append(Change("P03", f"강의체 도입 삭제 ({opener_deleted}개)"))
    if closer_deleted:
        changes.append(Change("P03", f"강의체 마무리 삭제 ({closer_deleted}개)"))
    if chatbot_deleted:
        changes.append(Change("P12", f"AI 챗봇 표현 삭제 ({chatbot_deleted}개)"))
    if p11_filler_deleted:
        changes.append(Change("P11", f"낙관적 기대 문장 삭제 ({p11_filler_deleted}개)"))

    if has_newlines:
        text = '\n\n'.join(kept)
    else:
        text = ' '.join(kept)

    # P13 — remove comma after connectors
    comma_matches = _KO_COMMA_AFTER_CONNECTOR.findall(text)
    if comma_matches:
        text = _KO_COMMA_AFTER_CONNECTOR.sub(lambda m: m.group(1) + " ", text)
        changes.append(Change("P13", f"접속어 뒤 쉼표 제거 ({len(comma_matches)}개)"))

    # P01 — count AI connectors at sentence starts (enum markers excluded)
    # Key fix: also count deleted sentences so P11 deletion doesn't suppress P01 trigger.
    found: dict[str, int] = {}
    for s in split_sentences_ko(text):
        m = _KO_P01_CONNECTOR_PATTERN.match(s.strip())
        if m:
            key = m.group(1)
            found[key] = found.get(key, 0) + 1
    for s in sentences:  # `sentences` = original split before any deletion
        if s not in kept:  # sentence was deleted — count its connector too
            m = _KO_P01_CONNECTOR_PATTERN.match(s.strip())
            if m:
                key = m.group(1)
                found[key] = found.get(key, 0) + 1
    total = sum(found.values())
    connector_count = total
    if total >= 2:  # 임계값 3→2: P11 삭제 후 접속어가 줄어도 탐지 유지
        rebuilt: list[str] = []
        for s in split_sentences_ko(text):
            stripped = _KO_P01_CONNECTOR_PATTERN.sub("", s.strip()).strip()
            rebuilt.append(stripped)
        text = (' ' if not has_newlines else '\n\n').join(rebuilt)
        connector_names = ", ".join(f"{k}x{v}" for k, v in found.items())
        changes.append(Change("P01", f"접속어 제거 ({connector_names})"))
        pattern_count += total

    # P01 — also remove inline connectors mid-sentence (3+ occurrences = clear AI pattern)
    inline_matches = _KO_INLINE_CONNECTOR_RE.findall(text)
    if len(inline_matches) >= 3:
        text = _KO_INLINE_CONNECTOR_RE.sub(' ', text)
        inline_names = ", ".join(inline_matches)
        changes.append(Change("P01", f"문장 내 접속어 제거 ({inline_names})"))
        pattern_count += len(inline_matches)

    # P08 — collapse modifier stacks
    for pat, replacement in _KO_MODIFIER_STACKS:
        matches = pat.findall(text)
        if matches:
            text = pat.sub(replacement, text)
            changes.append(Change("P08", f"수식어 중첩 제거: -> \"{replacement}\""))
            pattern_count += len(matches)

    # P04 — remove formulaic translation phrases
    for pat, repl_fn in _KO_FORMULAIC:
        matches = pat.findall(text)
        if matches:
            text = pat.sub(repl_fn, text)
            changes.append(Change("P04", f"번역투 표현 교체 ({len(matches)}개)"))
            pattern_count += len(matches)

    # P06 — AI 외래어 한국어 동의어 치환 (Safe Auto)
    p06_replaced: list[str] = []
    for pat, repl in _KO_P06_AUTO:
        hits = pat.findall(text)
        if hits:
            text = pat.sub(repl, text)
            p06_replaced.extend(hits)
    if p06_replaced:
        changes.append(Change("P06", f"AI 외래어 치환 ({len(p06_replaced)}개: {', '.join(dict.fromkeys(p06_replaced))})"))
        pattern_count += len(p06_replaced)

    # P05 — AI 과장 수식어 기계적 교체 (Safe Auto)
    p05_replaced: list[str] = []
    for pat, repl in _KO_P05_AUTO:
        hits = pat.findall(text)
        if hits:
            text = pat.sub(repl, text)
            p05_replaced.extend(hits)
    if p05_replaced:
        changes.append(Change("P05", f"과장 수식어 교체 ({len(p05_replaced)}개)"))
        pattern_count += len(p05_replaced)

    text = re.sub(r' {2,}', ' ', text)
    text = re.sub(r'\n{3,}', '\n\n', text).strip()

    # Recount connector starts in final text for accurate metrics
    post_conn_count = sum(
        1 for s in split_sentences_ko(text)
        if _KO_CONNECTOR_PATTERN.match(s.strip())
    )
    connector_count = post_conn_count

    return text, changes, pattern_count, connector_count


# ---------------------------------------------------------------------------
# Korean Flag patterns
# ---------------------------------------------------------------------------

_P05_PHRASES = [
    "핵심적인 역할", "필수적인 요소", "혁신적인", "필수 불가결", "결정적인 역할",
    "매우 중요합니다", "매우 중요한", "주목할 만한", "간과해서는 안 됩니다",
    "중요한 시사점", "필수적인",
]
_P05_PATTERN = re.compile(
    '(' + '|'.join(re.escape(p) for p in sorted(_P05_PHRASES, key=len, reverse=True)) + ')',
)

_P06_WORDS = [
    "다양한", "효율적으로", "체계적으로", "효과적으로", "지속적으로", "포괄적으로",
    "통합적", "종합적", "최적화", "시너지", "패러다임", "솔루션", "인사이트",
    # 추가: 외래어 AI 어휘
    "레버리지", "프레임워크", "가이드라인", "이니셔티브", "퍼포먼스", "프로세스",
    "모니터링", "로드맵", "밸런스", "리더십", "커뮤니케이션", "플랫폼",
    # 추가: 한국어 AI 특화 형용어
    "혁신적인", "전략적으로", "구조적으로", "근본적으로", "심층적으로",
]
_P06_PATTERN = re.compile('(' + '|'.join(re.escape(w) for w in _P06_WORDS) + ')')

_P09_PATTERNS_KO = [
    re.compile(r'단순히[^\n]*이 아니라'),
    re.compile(r'흔히[^\n]*(?:착각|생각)하지만'),
    re.compile(r'많은 사람들이[^\n]*(?:오해|착각)'),
    re.compile(r'흔히 ~라고 생각하지만'),
]

_P10_PATTERNS_KO = [
    re.compile(r'많은 전문가들은'),   # more specific first to avoid sub-match collision
    re.compile(r'연구에 따르면'),
    re.compile(r'(?<!많은 )전문가들은'),  # only when not preceded by 많은
    re.compile(r'대부분의 사람들은'),
    re.compile(r'최근 들어[^\n]*추세입니다'),
]

_P11_PATTERNS_KO = [
    re.compile(r'미래에는'),
    re.compile(r'이 지속될 것으로 전망'),
    re.compile(r'한다면[^\n]*할 수 있을 것이다'),
]


def _apply_ko_flags(text: str, sentences: list[str]) -> tuple[str, list[Flag], int]:
    flags: list[Flag] = []
    flag_pattern_count = 0

    # P05
    for i, sent in enumerate(sentences):
        for m in _P05_PATTERN.finditer(sent):
            phrase = m.group(1)
            marker = f'[[검토: P05 — "{phrase}" → 삭제하거나 구체적 근거 제시]]'
            text = text.replace(phrase, marker + phrase, 1)
            flags.append(Flag("P05", phrase, "삭제하거나 구체적 근거 제시", i))
            flag_pattern_count += 1

    # P06 — if 3+ in document
    p06_total = len(_P06_PATTERN.findall(text))
    if p06_total >= 3:
        for i, sent in enumerate(sentences):
            for m in _P06_PATTERN.finditer(sent):
                word = m.group(1)
                marker = f'[[검토: P06 — "{word}" → 구체적으로]]'
                text = text.replace(word, marker + word, 1)
                flags.append(Flag("P06", word, "구체적으로", i))
                flag_pattern_count += 1

    # P09
    for i, sent in enumerate(sentences):
        for pat in _P09_PATTERNS_KO:
            m = pat.search(sent)
            if m:
                phrase = m.group(0)
                marker = f'[[검토: P09 — 오해 바로잡기 구조 → 요점 직접 서술]]'
                text = text.replace(phrase, phrase + " " + marker, 1)
                flags.append(Flag("P09", phrase, "요점 직접 서술", i))
                flag_pattern_count += 1

    # P10 — apply at most one marker per sentence to avoid nested markers
    for i, sent in enumerate(sentences):
        for pat in _P10_PATTERNS_KO:
            m = pat.search(sent)
            if m:
                phrase = m.group(0)
                marker = f'[[검토: P10 — "{phrase}" → 출처 명시 또는 삭제]]'
                text = text.replace(phrase, marker + phrase, 1)
                flags.append(Flag("P10", phrase, "출처 명시 또는 삭제", i))
                flag_pattern_count += 1
                break  # one P10 flag per sentence

    # P11
    for i, sent in enumerate(sentences):
        for pat in _P11_PATTERNS_KO:
            m = pat.search(sent)
            if m:
                phrase = m.group(0)
                marker = f'[[검토: P11 — "{phrase}" → 구체적 근거 연결 또는 삭제]]'
                text = text.replace(phrase, phrase + " " + marker, 1)
                flags.append(Flag("P11", phrase, "구체적 근거 연결 또는 삭제", i))
                flag_pattern_count += 1

    return text, flags, flag_pattern_count


def _check_p14(sentences: list[str]) -> Optional[Flag]:
    counts = [_word_count(s) for s in sentences if s.strip()]
    if len(counts) < 3:
        return None
    if max(counts) - min(counts) < 10 and (sum(counts) / len(counts)) > 5:
        return Flag("P14", "문장 길이 균일", "짧은 문장 1개 이상 + 긴 문장 1개 이상 확보", 0)
    return None


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def humanize_en(text: str) -> HumanizerResult:
    original = text

    # Count initial metrics (same counter as detect_en, so before-score == detect score)
    sentences_before = split_sentences_en(text)
    init_patterns, init_conn = _count_en_patterns(text, sentences_before)
    metrics_before = compute_metrics_en(text, init_patterns, init_conn)

    # Safe Auto
    converted, changes, auto_pattern_count, connector_count = _apply_en_safe_auto(text)

    # Flags
    sentences_after = split_sentences_en(converted)
    converted, flags, flag_count = _apply_en_flags(converted, sentences_after)

    # E14 document-level check
    e14 = _check_e14(sentences_after)
    if e14:
        flags.append(e14)
        converted += "\n\n[[Review: E14 — Uniform sentence length detected — add short (under 8 words) and long (over 25 words) sentences for natural variation]]"

    metrics_after = compute_metrics_en(
        converted, flag_count, connector_count
    )
    # Correct for sentence deletions: when Non-AI sentences are deleted, denominator
    # shrinks while flag count stays, inflating pattern_density. Recompute using orig count.
    orig_sc = max(1, len(sentences_before))
    new_sc = max(1, len(split_sentences_en(_strip_review_markers(converted))))
    if new_sc < orig_sc:
        clean_conv = _strip_review_markers(converted)
        corrected_pd = flag_count / orig_sc
        corrected_cf = connector_count / orig_sc
        corrected_pps = clean_conv.count("—") / orig_sc
        corrected_score = _ai_score(corrected_pd, corrected_cf, corrected_pps,
                                    metrics_after.burstiness, orig_sc)
        metrics_after = Metrics(
            orig_sc, round(corrected_pd, 2), round(corrected_cf, 2),
            round(corrected_pps, 2), metrics_after.burstiness, corrected_score
        )
    # Cap: Safe Auto should not raise the score
    if metrics_after.ai_score > metrics_before.ai_score:
        metrics_after = Metrics(
            metrics_after.sentence_count, metrics_after.pattern_density,
            metrics_after.connector_freq, metrics_after.punct_per_sentence,
            metrics_after.burstiness, metrics_before.ai_score,
        )

    return HumanizerResult(
        lang="en",
        original_text=original,
        converted_text=converted,
        safe_auto_changes=changes,
        flags=flags,
        metrics_before=metrics_before,
        metrics_after=metrics_after,
    )


def humanize_ko(text: str) -> HumanizerResult:
    original = text

    # Count initial metrics
    sentences_before = split_sentences_ko(text)
    init_conn = sum(
        1 for s in sentences_before
        if _KO_CONNECTOR_PATTERN.match(s.strip())
    )
    init_auto_count = (
        sum(1 for s in split_sentences_ko(text) if _KO_OPENER_RE.search(s))
        + sum(1 for s in split_sentences_ko(text) if _KO_CLOSER_RE.search(s))
        + sum(1 for s in split_sentences_ko(text) if _KO_CHATBOT_RE.search(s))
        + sum(1 for s in split_sentences_ko(text) if _KO_P11_FILLER_SENT.search(s))
        + sum(len(p.findall(text)) for p, _ in _KO_MODIFIER_STACKS)
    )
    p06_all = len(_P06_PATTERN.findall(text))
    init_flag_count = (
        len(_P05_PATTERN.findall(text))
        + (p06_all if p06_all >= 3 else 0)
        + sum(1 for p in _P09_PATTERNS_KO for _ in [p.search(text)] if _)
        + sum(1 for p in _P10_PATTERNS_KO for _ in [p.search(text)] if _)
        + sum(1 for p in _P11_PATTERNS_KO for _ in [p.search(text)] if _)
    )
    metrics_before = compute_metrics_ko(text, init_auto_count + init_flag_count, init_conn)

    # Safe Auto
    converted, changes, auto_pattern_count, connector_count = _apply_ko_safe_auto(text)

    # Flags
    sentences_after = split_sentences_ko(converted)
    converted, flags, flag_count = _apply_ko_flags(converted, sentences_after)

    # P14 document-level check
    p14 = _check_p14(sentences_after)
    if p14:
        flags.append(p14)
        converted += "\n\n[[검토: P14 — 문장 길이 균일 탐지 — 3~4어절 짧은 문장 1개 이상 + 10어절↑ 긴 문장 1개 이상 확보 필요]]"

    metrics_after = compute_metrics_ko(
        converted, flag_count, connector_count
    )
    # Correct for sentence deletions: when Non-AI sentences are deleted, denominator
    # shrinks while flag count stays, inflating pattern_density. Recompute using orig count.
    orig_sc = max(1, len(sentences_before))
    new_sc = max(1, len(split_sentences_ko(_strip_review_markers(converted))))
    if new_sc < orig_sc:
        clean_conv = _strip_review_markers(converted)
        corrected_pd = flag_count / orig_sc
        corrected_cf = connector_count / orig_sc
        commas_conv = clean_conv.count(",") + clean_conv.count("，")
        corrected_pps = commas_conv / orig_sc
        corrected_score = _ai_score(corrected_pd, corrected_cf, corrected_pps,
                                    metrics_after.burstiness, orig_sc)
        metrics_after = Metrics(
            orig_sc, round(corrected_pd, 2), round(corrected_cf, 2),
            round(corrected_pps, 2), metrics_after.burstiness, corrected_score
        )
    # Cap: Safe Auto should not raise the score
    if metrics_after.ai_score > metrics_before.ai_score:
        metrics_after = Metrics(
            metrics_after.sentence_count, metrics_after.pattern_density,
            metrics_after.connector_freq, metrics_after.punct_per_sentence,
            metrics_after.burstiness, metrics_before.ai_score,
        )

    return HumanizerResult(
        lang="ko",
        original_text=original,
        converted_text=converted,
        safe_auto_changes=changes,
        flags=flags,
        metrics_before=metrics_before,
        metrics_after=metrics_after,
    )


def _count_en_patterns(text: str, sentences: list[str]) -> tuple[int, int]:
    """Count AI-writing patterns + sentence-initial connectors.

    Shared by detect_en and humanize_en so the score is consistent. Counts the
    full set of detectable patterns (not just a subset), which is what makes the
    AI-density signal track reality on English text.
    """
    conn = sum(1 for s in sentences if _EN_CONNECTOR_PATTERN.match(s.strip()))
    patterns = (
        len(_E05_PATTERN.findall(text))                          # E05 hyperbole
        + len(_E06_T1_PATTERN.findall(text))                     # E06 inflated vocab (T1)
        + len(_E06_T2_PATTERN.findall(text))                     # E06 inflated vocab (T2)
        + sum(1 for s in sentences if _EN_OPENER_RE.search(s))   # E03 lecture openers
        + sum(1 for s in sentences if _EN_CLOSER_RE.search(s))   # E03 lecture closers
        + len(_EN_MODIFIER_STACKS.findall(text))                 # E08 modifier stacks
        + len(_EN_MOST_REDUNDANT.findall(text))                  # E08 most + absolute
        + sum(len(p.findall(text)) for p, _ in _EN_FORMULAIC)    # E04 formulaic filler
        + sum(1 for s in sentences if _EN_CHATBOT_RE.search(s))  # E12 chatbot sign-offs
        + sum(1 for p in _E02_PATTERNS if p.search(text))        # E02 academic register
        + sum(1 for p in _E09_PATTERNS if p.search(text))        # E09 misconception
        + sum(1 for p in _E10_PATTERNS if p.search(text))        # E10 sweeping generalization
        + sum(1 for p in _E11_PATTERNS if p.search(text))        # E11 foresight
        + len(_EN_COMMA_AFTER_CONNECTOR.findall(text))           # E13 comma-after-connector
        + sum(1 for p in _EN_CLICHE_PATTERNS if p.search(text))  # E03b content-marketing clichés
    )
    return patterns, conn


def detect_en(text: str) -> Metrics:
    sentences = split_sentences_en(text)
    patterns, conn = _count_en_patterns(text, sentences)
    return compute_metrics_en(text, patterns, conn)


def detect_ko(text: str) -> Metrics:
    sentences = split_sentences_ko(text)
    conn = sum(1 for s in sentences if _KO_CONNECTOR_PATTERN.match(s.strip()))
    patterns = (
        len(_P05_PATTERN.findall(text))
        + len(_P06_PATTERN.findall(text))
        + sum(1 for s in sentences if _KO_OPENER_RE.search(s))
        + sum(1 for s in sentences if _KO_CLOSER_RE.search(s))
        + sum(len(p.findall(text)) for p, _ in _KO_MODIFIER_STACKS)
    )
    return compute_metrics_ko(text, patterns, conn)


def _is_korean(text: str) -> bool:
    korean_chars = len(re.findall(r'[가-힣]', text))
    total_chars = len(re.sub(r'\s', '', text))
    return (korean_chars / max(1, total_chars)) > 0.30


def humanize_auto(text: str) -> HumanizerResult:
    if _is_korean(text):
        return humanize_ko(text)
    return humanize_en(text)


# ---------------------------------------------------------------------------
# Output formatting
# ---------------------------------------------------------------------------

def _classify_text_en(text: str) -> str:
    if re.search(r'\b(report|proposal|whitepaper|executive summary)\b', text, re.IGNORECASE):
        return "Formal document / passive voice"
    if re.search(r'\b(abstract|hypothesis|methodology|findings|conclusion)\b', text, re.IGNORECASE):
        return "Academic / hedged"
    if re.search(r'\b(you|your|we|let\'s|let us)\b', text[:200], re.IGNORECASE):
        return "Informational blog / active voice"
    if re.search(r'\b(buy|purchase|discover|transform|unlock)\b', text, re.IGNORECASE):
        return "Marketing / persuasive"
    if re.search(r'\bI\b', text[:200]):
        return "Personal / first-person"
    return "Informational / mixed"


def _classify_text_ko(text: str) -> str:
    if re.search(r'습니다|입니다', text):
        if re.search(r'보고서|제안서|공문', text):
            return "공식 문서 / ~습니다체"
        return "정보성 글 또는 공식 문서 / ~습니다체"
    if re.search(r'[다이]$', text.split('\n')[0] if text else ""):
        return "정보성 글 / ~다체"
    return "정보성 글 / 혼용체"


def _score_label_en(score: float) -> str:
    if score >= 80:
        return "Strong AI text"
    if score >= 50:
        return "Many AI patterns"
    if score >= 20:
        return "Safe Auto complete level"
    return "Natural English"


def _score_label_ko(score: float) -> str:
    if score >= 80:
        return "강한 AI 텍스트"
    if score >= 50:
        return "AI 패턴 다수"
    if score >= 20:
        return "Safe Auto 완료 수준"
    if score >= 10:
        return "Flag 검토 상당 부분 완료"
    return "자연스러운 한국어"


def format_result(result: HumanizerResult) -> str:
    m_b = result.metrics_before
    m_a = result.metrics_after
    lines: list[str] = []

    if result.lang == "en":
        text_type = _classify_text_en(result.original_text)
        lines.append(f"[Text Type]\n{text_type}\n")

        lines.append("[Safe Auto Complete]")
        if result.safe_auto_changes:
            for ch in result.safe_auto_changes:
                lines.append(f"- {ch.pattern_id}: {ch.description}")
        else:
            lines.append("- No Safe Auto changes applied")
        lines.append("")

        lines.append("[Writer Review — Flag & Suggest]")
        high_priority = [f for f in result.flags if f.pattern_id in ("E05", "E11")]
        other_flags = [f for f in result.flags if f.pattern_id not in ("E05", "E11")]
        all_flags = high_priority + other_flags

        if len(all_flags) > 10:
            lines.append(f"(Summary mode — {len(all_flags)} flags found)")
            for f in all_flags:
                lines.append(f'  - Sentence {f.sentence_idx + 1}: {f.pattern_id} "{f.original}" → {f.suggestion}')
        elif all_flags:
            for f in all_flags:
                lines.append(f'- Sentence {f.sentence_idx + 1}: {f.pattern_id} "{f.original}" → {f.suggestion}')
        else:
            lines.append("- No flags")
        lines.append("")

        lines.append("[Converted Text]")
        lines.append("(Safe Auto applied. Flag items remain with inline markers)")
        lines.append("")
        lines.append(result.converted_text)
        lines.append("")

        lines.append("[Metrics]")
        lines.append(f"{'':25s} {'Original':>10s}   {'After Auto':>10s}")
        lines.append(f"{'Pattern density:':<25s} {m_b.pattern_density:>10.2f}   {m_a.pattern_density:>10.2f}")
        lines.append(f"{'Connector freq:':<25s} {m_b.connector_freq:>10.2f}   {m_a.connector_freq:>10.2f}")
        lines.append(f"{'Punct/sentence (em-dash):':<25s} {m_b.punct_per_sentence:>10.2f}   {m_a.punct_per_sentence:>10.2f}")
        lines.append(f"{'Burstiness:':<25s} {m_b.burstiness:>10.1f}   {m_a.burstiness:>10.1f}")
        lines.append(f"{'AI Index:':<25s} {m_b.ai_score:>9.0f}pts   {m_a.ai_score:>9.0f}pts")
        lines.append("")

        remaining = [f for f in result.flags if f.pattern_id not in ("E14",)]
        remaining_summary = ", ".join(
            f"{pid}×{sum(1 for f in result.flags if f.pattern_id == pid)}"
            for pid in dict.fromkeys(f.pattern_id for f in remaining)
        )

        lines.append("[Progress]")
        lines.append(
            f"[Original {m_b.ai_score:.0f}pts] → [After Safe Auto {m_a.ai_score:.0f}pts] → [Target 10pts or below]"
        )
        if remaining_summary:
            lines.append(f"  ↑ Remaining: {remaining_summary} to review")
        lines.append("")

        lines.append("[Verification]")
        lines.append(f"Register: {text_type}")
        s_b = m_b.sentence_count
        s_a = m_a.sentence_count
        deleted = max(0, s_b - s_a)
        lines.append(f"Sentences: original {s_b} → output {s_a}" + (f" ({deleted} deleted)" if deleted else ""))
        lines.append("Content added: none")

    else:  # Korean
        text_type = _classify_text_ko(result.original_text)
        lines.append(f"[텍스트 유형]\n{text_type}\n")

        lines.append("[자동 교체 완료 — Safe Auto]")
        if result.safe_auto_changes:
            for ch in result.safe_auto_changes:
                lines.append(f"- {ch.pattern_id}: {ch.description}")
        else:
            lines.append("- Safe Auto 변경 없음")
        lines.append("")

        lines.append("[작가 검토 필요 — Flag & Suggest]")
        high_priority = [f for f in result.flags if f.pattern_id in ("P05", "P11")]
        other_flags = [f for f in result.flags if f.pattern_id not in ("P05", "P11")]
        all_flags = high_priority + other_flags

        if len(all_flags) > 10:
            lines.append(f"(요약 모드 — {len(all_flags)}개 Flag 탐지)")
            for f in all_flags:
                lines.append(f'  - {f.sentence_idx + 1}번 문장: {f.pattern_id} "{f.original}" → {f.suggestion}')
        elif all_flags:
            for f in all_flags:
                lines.append(f'- {f.sentence_idx + 1}번 문장: {f.pattern_id} "{f.original}" → {f.suggestion}')
        else:
            lines.append("- Flag 없음")
        lines.append("")

        lines.append("[변환된 텍스트]")
        lines.append("(Safe Auto 교체 적용. Flag 항목은 인라인 마커 포함 원문 유지)")
        lines.append("")
        lines.append(result.converted_text)
        lines.append("")

        lines.append("[측정 지표]")
        lines.append(f"{'':20s} {'원문':>8s}   {'변환 후(Auto)':>13s}")
        lines.append(f"{'패턴 밀도:':<20s} {m_b.pattern_density:>8.2f}   {m_a.pattern_density:>13.2f}")
        lines.append(f"{'접속어 빈도:':<20s} {m_b.connector_freq:>8.2f}   {m_a.connector_freq:>13.2f}")
        lines.append(f"{'쉼표/문장:':<20s} {m_b.punct_per_sentence:>8.2f}   {m_a.punct_per_sentence:>13.2f}")
        lines.append(f"{'Burstiness:':<20s} {m_b.burstiness:>8.1f}   {m_a.burstiness:>13.1f}")
        lines.append(f"{'AI지수:':<20s} {m_b.ai_score:>7.0f}점   {m_a.ai_score:>12.0f}점")
        lines.append("")

        remaining = [f for f in result.flags if f.pattern_id not in ("P14",)]
        remaining_summary = ", ".join(
            f"{pid}×{sum(1 for f in result.flags if f.pattern_id == pid)}"
            for pid in dict.fromkeys(f.pattern_id for f in remaining)
        )

        lines.append("[진행 상태]")
        lines.append(
            f"[원문 {m_b.ai_score:.0f}점] → [Safe Auto 후 {m_a.ai_score:.0f}점] → [Flag 검토 완료 목표 10점 이하]"
        )
        if remaining_summary:
            lines.append(f"  ↑ 남은 작업: {remaining_summary} 검토")
        lines.append("")

        lines.append("[검증]")
        lines.append(f"어조: {text_type}")
        s_b = m_b.sentence_count
        s_a = m_a.sentence_count
        deleted = max(0, s_b - s_a)
        lines.append(
            f"문장 수: 원문 {s_b}문장 → 출력 {s_a}문장"
            + (f" (강의체 {deleted}문장 삭제)" if deleted else "")
        )
        lines.append("내용 추가: 없음")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _load_input(source: str) -> str:
    if source.endswith(".txt") and len(source) < 260:
        try:
            with open(source, "r", encoding="utf-8") as fh:
                return fh.read()
        except FileNotFoundError:
            pass
    return source


def main() -> None:
    # Ensure UTF-8 output on all platforms (e.g. Windows cmd/PowerShell)
    import io
    if hasattr(sys.stdout, 'buffer'):
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

    parser = argparse.ArgumentParser(
        description="Rule-based AI writing pattern detector and humanizer (no LLM required).",
    )
    parser.add_argument("text", help='Text to analyze, or path to a .txt file')
    parser.add_argument("--lang", choices=["en", "ko", "auto"], default="auto",
                        help="Language (default: auto-detect)")
    parser.add_argument("--detect", action="store_true",
                        help="Metrics only — no conversion")
    parser.add_argument("--json", action="store_true",
                        help="Output raw JSON instead of formatted text")
    args = parser.parse_args()

    text = _load_input(args.text)

    if args.detect:
        if args.lang == "ko" or (args.lang == "auto" and _is_korean(text)):
            metrics = detect_ko(text)
        else:
            metrics = detect_en(text)
        if args.json:
            print(json.dumps(asdict(metrics), ensure_ascii=False, indent=2))
        else:
            print(f"Sentence count:     {metrics.sentence_count}")
            print(f"Pattern density:    {metrics.pattern_density:.2f}")
            print(f"Connector freq:     {metrics.connector_freq:.2f}")
            print(f"Punct/sentence:     {metrics.punct_per_sentence:.2f}")
            print(f"Burstiness:         {metrics.burstiness:.1f}")
            print(f"AI Score:           {metrics.ai_score:.0f}pts")
        return

    if args.lang == "ko":
        result = humanize_ko(text)
    elif args.lang == "en":
        result = humanize_en(text)
    else:
        result = humanize_auto(text)

    if args.json:
        print(json.dumps(asdict(result), ensure_ascii=False, indent=2))
    else:
        print(format_result(result))


if __name__ == "__main__":
    main()
