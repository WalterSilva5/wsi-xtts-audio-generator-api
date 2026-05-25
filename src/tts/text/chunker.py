"""Duration-aware text chunking for XTTS synthesis.

XTTS degrades on long inputs: prosody drifts, words get dropped/repeated and the
voice starts sounding robotic. The model behaves best when each inference covers
roughly **10-14 seconds** of speech.

This module splits arbitrary text into chunks that:

1. Stay under a configurable duration cap (estimated from character count).
2. Are cut at the *most natural* boundary available, in priority order:
   sentence end (``. ! ? …``) → clause (``, ; :``) → word → hard char cut.
3. **Keep their punctuation**, so the model still receives the prosodic cues it
   needs (a chunk ending in ``,`` is spoken as a continuation; one ending in
   ``.`` gets a proper falling, sentence-final intonation).
4. Are packed as *long as possible* under the cap — fewer, longer inferences
   preserve intonation far better than many tiny fragments.

The output carries a ``boundary`` type per chunk so the audio layer can insert a
pause whose length matches the punctuation (longer after a sentence, shorter
after a comma), instead of a uniform robotic gap.

Tuning (env vars, optional):
    XTTS_MAX_CHUNK_SECONDS   target max seconds per chunk (default 13)
    XTTS_CHARS_PER_SECOND    chars/second at speed 1.0 used for the estimate
                             (default 13 — intentionally conservative so the
                             estimate is an upper bound and real audio stays
                             under the cap)
"""
from __future__ import annotations

import os
import re
from dataclasses import dataclass
from typing import List

# --- configuration -----------------------------------------------------------

MAX_SECONDS: float = float(os.getenv("XTTS_MAX_CHUNK_SECONDS", "13"))
CHARS_PER_SECOND: float = float(os.getenv("XTTS_CHARS_PER_SECOND", "13"))

# Never exceed this many characters in a single chunk, regardless of the
# duration math — keeps us safely below the XTTS per-language character limit
# (~200-250) so the model never re-splits internally.
MAX_CHARS_HARD: int = 200
# Avoid pathologically tiny caps when speed is very low.
MIN_CHARS: int = 40

_SENTENCE_ENDINGS = ".!?…"
_CLAUSE_ENDINGS = ",;:"

# Split *after* a sentence terminator followed by whitespace (terminator stays
# attached to the left part). Optional closing quote/bracket is kept too.
_SENTENCE_RE = re.compile(r'(?<=[.!?…])["\')\]]?\s+')
# Split *after* a clause delimiter followed by whitespace.
_CLAUSE_RE = re.compile(r'(?<=[,;:])\s+')
_WS_RE = re.compile(r"\s+")


@dataclass
class TextChunk:
    """A single piece of text to synthesize in one inference call."""

    text: str
    boundary: str          # 'sentence' | 'clause' | 'word' — type of its ENDING
    est_seconds: float     # estimated spoken duration in seconds

    @property
    def ends_sentence(self) -> bool:
        return self.boundary == "sentence"


# --- public API --------------------------------------------------------------

def estimate_seconds(text: str, speed: float = 1.0,
                     cps: float = CHARS_PER_SECOND) -> float:
    """Estimate spoken duration of ``text`` (seconds).

    Character-based and deliberately conservative. ``speed`` follows XTTS
    semantics: <1.0 is slower (longer audio), >1.0 is faster (shorter audio).
    """
    n = len(text.strip())
    if n == 0:
        return 0.0
    return n / (max(cps, 1.0) * max(speed, 0.1))


def max_chars_for(speed: float, max_seconds: float = MAX_SECONDS,
                  cps: float = CHARS_PER_SECOND) -> int:
    """Maximum characters allowed in a chunk for the given speed/cap."""
    raw = int(max_seconds * cps * max(speed, 0.1))
    return max(MIN_CHARS, min(raw, MAX_CHARS_HARD))


def chunk_text(text: str, speed: float = 1.0,
               max_seconds: float = MAX_SECONDS,
               cps: float = CHARS_PER_SECOND) -> List[TextChunk]:
    """Split ``text`` into duration-capped, boundary-aware chunks.

    Returns an empty list for empty input.
    """
    text = _WS_RE.sub(" ", (text or "")).strip()
    if not text:
        return []

    max_chars = max_chars_for(speed, max_seconds, cps)
    atoms = _atomize(text, max_chars)
    return _pack(atoms, max_chars, speed, cps)


# --- internals ---------------------------------------------------------------

def _atomize(text: str, max_chars: int) -> List[str]:
    """Break text into the smallest natural units that each fit ``max_chars``.

    Sentences that already fit are kept whole; longer ones are broken at
    clauses, then words, then (last resort) hard character cuts.
    """
    atoms: List[str] = []
    for sentence in _split(text, _SENTENCE_RE):
        if len(sentence) <= max_chars:
            atoms.append(sentence)
            continue
        for clause in _split(sentence, _CLAUSE_RE):
            if len(clause) <= max_chars:
                atoms.append(clause)
            else:
                atoms.extend(_split_words(clause, max_chars))
    return atoms


def _pack(atoms: List[str], max_chars: int, speed: float,
          cps: float) -> List[TextChunk]:
    """Greedily merge consecutive atoms into chunks up to ``max_chars``."""
    chunks: List[TextChunk] = []
    current = ""
    for atom in atoms:
        candidate = f"{current} {atom}".strip() if current else atom
        if current and len(candidate) > max_chars:
            chunks.append(_make_chunk(current, speed, cps))
            current = atom
        else:
            current = candidate
    if current:
        chunks.append(_make_chunk(current, speed, cps))
    return chunks


def _make_chunk(text: str, speed: float, cps: float) -> TextChunk:
    text = text.strip()
    return TextChunk(
        text=text,
        boundary=_classify_boundary(text),
        est_seconds=round(estimate_seconds(text, speed, cps), 2),
    )


def _classify_boundary(text: str) -> str:
    stripped = text.rstrip("\"')]}")  # ignore trailing closing quotes/brackets
    if not stripped:
        return "word"
    last = stripped[-1]
    if last in _SENTENCE_ENDINGS:
        return "sentence"
    if last in _CLAUSE_ENDINGS:
        return "clause"
    return "word"


def _split(text: str, pattern: re.Pattern) -> List[str]:
    return [p.strip() for p in pattern.split(text) if p and p.strip()]


def _split_words(text: str, max_chars: int) -> List[str]:
    """Split an over-long, punctuation-poor span at whitespace (then chars)."""
    parts: List[str] = []
    current = ""
    for word in text.split():
        candidate = f"{current} {word}".strip() if current else word
        if current and len(candidate) > max_chars:
            parts.append(current)
            current = word
        else:
            current = candidate
        # A single word longer than the cap: hard-cut it.
        while len(current) > max_chars:
            parts.append(current[:max_chars])
            current = current[max_chars:]
    if current:
        parts.append(current)
    return parts
