"""Unit tests for the duration-aware text chunker."""
import pytest

from src.tts.text.chunker import (
    chunk_text,
    estimate_seconds,
    max_chars_for,
    MAX_CHARS_HARD,
)

pytestmark = pytest.mark.unit


def test_empty_text_returns_no_chunks():
    assert chunk_text("") == []
    assert chunk_text("   ") == []
    assert chunk_text(None) == []  # type: ignore[arg-type]


def test_short_text_is_single_chunk():
    chunks = chunk_text("Olá, tudo bem com você?", speed=1.0)
    assert len(chunks) == 1
    assert chunks[0].text == "Olá, tudo bem com você?"
    assert chunks[0].boundary == "sentence"  # ends with '?'


def test_short_sentences_are_merged_up_to_the_cap():
    text = "Um. Dois. Três. Quatro. Cinco."
    chunks = chunk_text(text, speed=1.0)
    # Plenty of room -> everything fits in one chunk.
    assert len(chunks) == 1
    assert chunks[0].text == text


def test_long_text_is_split_and_respects_char_cap():
    speed = 1.0
    cap = max_chars_for(speed)
    sentence = ("Esta é uma frase razoavelmente longa que serve para testar o "
                "fatiamento do texto em pedaços menores. ")
    text = sentence * 12  # well above any single chunk

    chunks = chunk_text(text, speed=speed)

    assert len(chunks) > 1
    for c in chunks:
        assert len(c.text) <= cap
        assert len(c.text) <= MAX_CHARS_HARD
        assert c.est_seconds <= chunk_max_seconds() + 0.5


def test_prefers_sentence_then_clause_boundaries():
    # Two sentences, each too long to merge -> split at the sentence boundary.
    s1 = "Primeira frase que ja ocupa um bom espaco do limite disponivel aqui."
    s2 = "Segunda frase tambem comprida para forcar a separacao entre elas hoje."
    chunks = chunk_text(s1 + " " + s2, speed=1.0, max_seconds=6, cps=13)
    assert len(chunks) >= 2
    # The first chunk must end on sentence-final punctuation, not mid-word.
    assert chunks[0].text.rstrip()[-1] in ".!?…"


def test_punctuation_is_preserved():
    text = "Bom dia, pessoal! Como vão? Vamos começar; já está na hora."
    joined = " ".join(c.text for c in chunk_text(text, speed=1.0))
    for mark in [",", "!", "?", ";", "."]:
        assert mark in joined


def test_clause_split_when_single_sentence_too_long():
    # One sentence, no sentence breaks, but commas to split on.
    text = ("comprei pao, comprei leite, comprei queijo, comprei cafe, "
            "comprei manteiga, comprei suco, comprei frutas e comprei arroz")
    chunks = chunk_text(text, speed=1.0, max_seconds=4, cps=13)
    assert len(chunks) > 1
    cap = max_chars_for(1.0, max_seconds=4, cps=13)
    for c in chunks:
        assert len(c.text) <= cap


def test_word_split_for_unpunctuated_long_run():
    text = "palavra " * 80  # no punctuation at all
    chunks = chunk_text(text.strip(), speed=1.0, max_seconds=3, cps=13)
    cap = max_chars_for(1.0, max_seconds=3, cps=13)
    assert len(chunks) > 1
    for c in chunks:
        assert len(c.text) <= cap
        assert c.boundary == "word"


def test_speed_changes_chunk_size():
    text = ("Frase de teste para medir o efeito da velocidade no tamanho dos "
            "pedacos gerados pelo algoritmo de fatiamento. ") * 6
    slow = chunk_text(text, speed=0.7)
    fast = chunk_text(text, speed=1.3)
    # Slower speech -> longer audio per char -> fewer chars per chunk -> more chunks.
    assert len(slow) >= len(fast)


def test_estimate_seconds_scales_with_speed():
    base = estimate_seconds("a" * 130, speed=1.0, cps=13)
    assert base == pytest.approx(10.0, abs=0.01)
    slower = estimate_seconds("a" * 130, speed=0.5, cps=13)
    assert slower > base


def chunk_max_seconds() -> float:
    from src.tts.text.chunker import MAX_SECONDS
    return MAX_SECONDS
