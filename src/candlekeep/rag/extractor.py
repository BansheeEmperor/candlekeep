"""Two-layer entity extraction: spaCy NER + corpus-bootstrapped entity ruler."""
import json
import re
from pathlib import Path

from candlekeep.rag.entity_normalise import normalise_entity

# Patterns for technical tokens not caught by spaCy NER
_SCREAMING_SNAKE = re.compile(r"\b[A-Z][A-Z0-9]{2,}(?:_[A-Z0-9]+)+\b")   # EXPANSION_SIMILARITY_THRESHOLD
_CAMEL_PASCAL    = re.compile(r"\b[A-Z][A-Za-z0-9]*[A-Z][a-z][A-Za-z0-9]*\b")  # ArcaneRecall, BM25Searcher
_DOTTED_ID       = re.compile(r"\b[a-z][a-z0-9]*(?:\.[a-z][a-z0-9]*){2,}\b")  # bge.small.en
_VERSION_STR     = re.compile(r"\bv\d+(?:\.\d+)+\b")                       # v1.2.3

_TECH_PATTERNS = [_SCREAMING_SNAKE, _CAMEL_PASCAL, _DOTTED_ID, _VERSION_STR]

# Minimum normalised length to keep (avoids single-char noise)
_MIN_LEN = 3


def _tech_tokens(text: str) -> list[str]:
    found = []
    for pat in _TECH_PATTERNS:
        found.extend(pat.findall(text))
    return found


class EntityExtractor:
    """Extract technical entities using spaCy NER + entity ruler + pattern matching."""

    def __init__(self, ruler_path: Path | None = None):
        self._ruler_path = ruler_path
        self._nlp = None

    @property
    def nlp(self):
        if self._nlp is None:
            import spacy
            try:
                self._nlp = spacy.load("en_core_web_sm", disable=["parser", "lemmatizer"])
            except OSError:
                from spacy.cli import download
                download("en_core_web_sm")
                self._nlp = spacy.load("en_core_web_sm", disable=["parser", "lemmatizer"])

            if self._ruler_path and self._ruler_path.exists():
                ruler = self._nlp.add_pipe("entity_ruler", before="ner")
                patterns = []
                for line in self._ruler_path.read_text().splitlines():
                    line = line.strip()
                    if line:
                        patterns.append(json.loads(line))
                ruler.add_patterns(patterns)

        return self._nlp

    def extract(self, text: str) -> list[str]:
        """Return deduplicated normalised entity names from both layers."""
        seen: set[str] = set()
        result: list[str] = []

        def _add(raw: str):
            norm = normalise_entity(raw)
            if len(norm) >= _MIN_LEN and norm not in seen:
                seen.add(norm)
                result.append(norm)

        # Layer 1: spaCy NER + entity ruler
        doc = self.nlp(text)
        for ent in doc.ents:
            _add(ent.text)

        # Layer 2: pattern matchers for technical tokens spaCy misses
        for tok in _tech_tokens(text):
            _add(tok)

        return result


# ── Singleton ─────────────────────────────────────────────────────────────────

_extractor: EntityExtractor | None = None


def get_extractor(ruler_path: Path | None = None) -> EntityExtractor:
    global _extractor
    if _extractor is None:
        _extractor = EntityExtractor(ruler_path)
    return _extractor


def clear_extractor_cache():
    global _extractor
    _extractor = None
