"""BM25 token normalisation for surface-form agnostic matching.

BM25 is an exact token matcher. Technical documentation contains surface-form
variations for the same concept: `ChromaDB` / `Chroma DB` / `chroma-db`,
`bge-small-en-v1.5` / `bge small` / `BGE Small`. When queries use different
forms than documents, BM25 assigns zero overlap, causing precision failures.

This module automatically derives a corpus-specific normalisation map from
documents and applies it symmetrically at index and query time, making BM25
surface-form agnostic.

Architecture:
- NormalisationMap: Load/save to JSON, normalise(token) method
- generate_normalisation_map(): Main generation entry point
- get_normalisation_map(): Global singleton with thread-safe lazy loading
- clear_normalisation_cache(): Clear for regeneration
- schedule_background_rebuild(): Fire-and-forget background rebuild after ingest
  (mirrors the ColBERT dirty-flag + background-thread pattern)

Clustering algorithm:
- Pre-filter tokens by length similarity (within 30%)
- For each pair: if edit distance ≤ 0.15 AND embedding similarity ≥ 0.82 → same cluster
- Elect canonical: most frequent wins, ties broken by longest form

See: docs/RESEARCH_DIARY.md for implementation rationale.
"""
import json
import logging
import threading
from pathlib import Path
from typing import Callable, Dict, List, Optional, Set, Tuple

logger = logging.getLogger("candlekeep")

# Thresholds for clustering
EDIT_DISTANCE_THRESHOLD = 0.15  # Normalized Levenshtein distance
EMBEDDING_SIMILARITY_THRESHOLD = 0.82  # Cosine similarity (lower for bare tokens vs sentences)
LENGTH_RATIO_THRESHOLD = 0.30  # Max length difference ratio


def _normalized_edit_distance(a: str, b: str) -> float:
    """Compute normalized Levenshtein distance between two strings.

    Returns distance / max(len(a), len(b)), so values are in [0, 1].
    Uses dynamic programming with O(min(len(a), len(b))) space.
    """
    if a == b:
        return 0.0

    len_a, len_b = len(a), len(b)
    if len_a == 0 or len_b == 0:
        return 1.0

    # Ensure len_a <= len_b for O(min(m,n)) space
    if len_a > len_b:
        a, b = b, a
        len_a, len_b = len_b, len_a

    # Use two rows for DP (previous and current)
    prev = list(range(len_a + 1))
    curr = [0] * (len_a + 1)

    for j in range(1, len_b + 1):
        curr[0] = j
        for i in range(1, len_a + 1):
            if a[i - 1] == b[j - 1]:
                curr[i] = prev[i - 1]
            else:
                curr[i] = 1 + min(prev[i], curr[i - 1], prev[i - 1])
        prev, curr = curr, prev

    distance = prev[len_a]
    max_len = max(len_a, len_b)
    return distance / max_len


def _cosine_similarity(vec_a: List[float], vec_b: List[float]) -> float:
    """Compute cosine similarity between two vectors.

    Returns dot(a, b) / (||a|| * ||b||), in [0, 1] for unit vectors.
    """
    if not vec_a or not vec_b or len(vec_a) != len(vec_b):
        return 0.0

    dot = sum(a * b for a, b in zip(vec_a, vec_b))
    norm_a = sum(a * a for a in vec_a) ** 0.5
    norm_b = sum(b * b for b in vec_b) ** 0.5

    if norm_a == 0 or norm_b == 0:
        return 0.0

    return dot / (norm_a * norm_b)


def _cluster_tokens(
    tokens: List[str],
    frequencies: Dict[str, int],
    embed_fn: Callable[[List[str]], List[List[float]]]
) -> Dict[str, str]:
    """Cluster tokens by surface-form similarity and elect canonical forms.

    Two-pass strategy to keep embedding cost low:
    1. Find all pairs that pass the edit-distance pre-filter (cheap, O(n²) string ops).
    2. Embed only the tokens involved in at least one such pair (often <5% of corpus).
    3. Re-check those pairs with cosine similarity to confirm the cluster.

    Args:
        tokens: Unique tokens from the corpus (appearing ≥ 2 times)
        frequencies: Token → frequency mapping
        embed_fn: Function to compute embeddings for a list of tokens

    Returns:
        Dict mapping variant → canonical token
    """
    if len(tokens) < 2:
        return {}

    # Pre-filter: group by first character for faster comparison
    groups: Dict[str, List[str]] = {}
    for token in tokens:
        first_char = token[0].lower() if token else ""
        if first_char not in groups:
            groups[first_char] = []
        groups[first_char].append(token)

    # Pass 1: find candidate pairs that pass length + edit-distance filters.
    # Collect only the tokens that appear in at least one candidate pair.
    candidate_pairs: List[Tuple[str, str]] = []
    tokens_needing_embed: Set[str] = set()

    for group_tokens in groups.values():
        n = len(group_tokens)
        for i in range(n):
            for j in range(i + 1, n):
                t1, t2 = group_tokens[i], group_tokens[j]

                len1, len2 = len(t1), len(t2)
                if max(len1, len2) > 0:
                    len_ratio = abs(len1 - len2) / max(len1, len2)
                    if len_ratio > LENGTH_RATIO_THRESHOLD:
                        continue

                edit_dist = _normalized_edit_distance(t1, t2)
                if edit_dist > EDIT_DISTANCE_THRESHOLD:
                    continue

                candidate_pairs.append((t1, t2))
                tokens_needing_embed.add(t1)
                tokens_needing_embed.add(t2)

    # Pass 2: embed only the candidate tokens (typically a small fraction).
    embed_map: Dict[str, List[float]] = {}
    if candidate_pairs and tokens_needing_embed:
        embed_list = list(tokens_needing_embed)
        try:
            embeddings = embed_fn(embed_list)
            for token, emb in zip(embed_list, embeddings):
                embed_map[token] = emb
        except Exception as e:
            logger.warning(
                "[candlekeep] Token embedding failed, using edit-distance-only clustering: %s", e
            )

    # Union-Find for clustering
    parent: Dict[str, str] = {t: t for t in tokens}

    def find(t: str) -> str:
        if parent[t] != t:
            parent[t] = find(parent[t])
        return parent[t]

    def union(t1: str, t2: str):
        p1, p2 = find(t1), find(t2)
        if p1 != p2:
            if frequencies.get(p1, 0) >= frequencies.get(p2, 0):
                parent[p2] = p1
            else:
                parent[p1] = p2

    for t1, t2 in candidate_pairs:
        # Embedding similarity check (if available)
        if embed_map:
            sim = _cosine_similarity(embed_map.get(t1, []), embed_map.get(t2, []))
            if sim < EMBEDDING_SIMILARITY_THRESHOLD:
                continue
        union(t1, t2)

    # Elect canonical for each cluster
    clusters: Dict[str, List[str]] = {}
    for token in tokens:
        root = find(token)
        if root not in clusters:
            clusters[root] = []
        clusters[root].append(token)

    # Map each variant to its canonical
    variant_to_canonical: Dict[str, str] = {}
    for cluster_tokens in clusters.values():
        if len(cluster_tokens) == 1:
            continue

        # Elect canonical: most frequent, ties broken by longest form
        canonical = max(
            cluster_tokens,
            key=lambda t: (frequencies.get(t, 0), len(t))
        )
        for token in cluster_tokens:
            if token != canonical:
                variant_to_canonical[token] = canonical

    return variant_to_canonical


class NormalisationMap:
    """Token normalisation map for BM25 surface-form matching.

    Stores variant → canonical mappings and provides normalise(token) method.
    Can be saved to/loaded from JSON for persistence.
    """

    def __init__(self, variant_map: Optional[Dict[str, str]] = None):
        """Initialize the normalisation map.

        Args:
            variant_map: Dict mapping variant tokens to canonical forms
        """
        self._variant_map = variant_map or {}
        # Pre-compute reverse lookup for fast normalise()
        self._lookup: Dict[str, str] = {}
        for variant, canonical in self._variant_map.items():
            self._lookup[variant.lower()] = canonical.lower()
            # Also store canonical form itself (identity)
            self._lookup[canonical.lower()] = canonical.lower()

    def normalise(self, token: str) -> str:
        """Normalise a token to its canonical form.

        Args:
            token: Token to normalise

        Returns:
            Canonical form of the token, or the original if unknown
        """
        return self._lookup.get(token.lower(), token.lower())

    def normalise_all(self, tokens: List[str]) -> List[str]:
        """Normalise a list of tokens.

        Args:
            tokens: Tokens to normalise

        Returns:
            List of canonical forms
        """
        return [self.normalise(t) for t in tokens]

    def save(self, path: Path) -> None:
        """Save the normalisation map to a JSON file.

        Args:
            path: Path to save the map
        """
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, 'w', encoding='utf-8') as f:
            json.dump({
                "variant_map": self._variant_map,
                "version": 1
            }, f, indent=2)

    @classmethod
    def load(cls, path: Path) -> Optional["NormalisationMap"]:
        """Load a normalisation map from a JSON file.

        Args:
            path: Path to load the map from

        Returns:
            NormalisationMap instance, or None if file doesn't exist or is invalid
        """
        if not path.exists():
            return None

        try:
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            variant_map = data.get("variant_map", {})
            return cls(variant_map)
        except (json.JSONDecodeError, KeyError) as e:
            logger.warning("[candlekeep] Invalid normalisation map at %s: %s", path, e)
            return None

    @property
    def size(self) -> int:
        """Number of variant → canonical mappings."""
        return len(self._variant_map)

    def __len__(self) -> int:
        return self.size

    def __repr__(self) -> str:
        return f"NormalisationMap(size={self.size})"


def generate_normalisation_map(
    corpus_tokens: List[str],
    token_frequencies: Dict[str, int],
    embed_fn: Callable[[List[str]], List[List[float]]],
    output_path: Path
) -> NormalisationMap:
    """Generate a normalisation map from corpus tokens.

    Args:
        corpus_tokens: List of all tokens from the corpus (with duplicates)
        token_frequencies: Token → frequency mapping
        embed_fn: Function to compute embeddings for a list of tokens
        output_path: Path to save the generated map

    Returns:
        NormalisationMap instance
    """
    # Filter to tokens appearing ≥ 2 times and length ≥ 4 chars.
    # Only include tokens that contain separators OR whose stripped form
    # also appears in the corpus — these are the only tokens where
    # normalisation can bridge a surface-form gap.
    separator_chars = set('-._')
    candidate_set = set()
    for t, freq in token_frequencies.items():
        if freq < 2 or len(t) < 4:
            continue
        if any(c in t for c in separator_chars):
            stripped = t.replace('-','').replace('.','').replace('_','')
            if stripped != t and stripped in token_frequencies:
                candidate_set.add(t)
                candidate_set.add(stripped)

    unique_tokens = list(candidate_set)

    if not unique_tokens:
        logger.info("[candlekeep] No tokens to cluster, creating empty normalisation map")
        norm_map = NormalisationMap()
        norm_map.save(output_path)
        return norm_map

    logger.info("[candlekeep] Clustering %d tokens for normalisation map", len(unique_tokens))

    # Cluster tokens
    variant_map = _cluster_tokens(unique_tokens, token_frequencies, embed_fn)

    # Create and save map
    norm_map = NormalisationMap(variant_map)
    norm_map.save(output_path)

    logger.info(
        "[candlekeep] Normalisation map created: %d variants → canonical forms",
        norm_map.size
    )

    return norm_map


# ── Global singleton with thread-safe lazy loading ──────────────────────────────

_normalisation_map: Optional[NormalisationMap] = None
_map_lock = threading.Lock()


def get_normalisation_map(data_dir: Path) -> Optional["NormalisationMap"]:
    """Get the normalisation map singleton, loading from disk if needed.

    Thread-safe lazy loading. Returns None if no map exists on disk.

    Args:
        data_dir: Data directory containing normalisation_map.json

    Returns:
        NormalisationMap instance, or None if not available
    """
    global _normalisation_map

    with _map_lock:
        if _normalisation_map is not None:
            return _normalisation_map

        map_path = data_dir / "normalisation_map.json"

        if not map_path.exists():
            logger.debug("[candlekeep] No normalisation map found at %s", map_path)
            return None

        _normalisation_map = NormalisationMap.load(map_path)
        if _normalisation_map is None:
            logger.warning("[candlekeep] Failed to load normalisation map from %s", map_path)
            return None

        logger.debug("[candlekeep] Loaded normalisation map (%d variants)", _normalisation_map.size)
        return _normalisation_map


def clear_normalisation_cache() -> None:
    """Clear the cached normalisation map.

    Used after repopulate_database to force regeneration on next query.
    """
    global _normalisation_map
    with _map_lock:
        _normalisation_map = None


# ── Background rebuild (mirrors ColBERT dirty-flag pattern) ─────────────────
#
# After each ingest(), schedule_background_rebuild() is called. It fires a
# daemon thread that regenerates the map from the current corpus. Queries
# during the rebuild use the stale map — no latency impact on either ingest
# or query paths. If a rebuild is already running, the new call is a no-op:
# the in-flight thread will finish with the latest corpus state anyway
# (it reads from ChromaDB at execution time, not at scheduling time).

_rebuild_building = False
_rebuild_lock = threading.Lock()


def schedule_background_rebuild(db) -> None:
    """Schedule a background normalisation map rebuild after an ingest.

    Non-blocking. If a rebuild is already in progress, this is a no-op —
    the running thread will complete with the latest corpus state.

    Args:
        db: VectorDatabase instance (read at thread execution time)
    """
    global _rebuild_building

    with _rebuild_lock:
        if _rebuild_building:
            return
        _rebuild_building = True

    thread = threading.Thread(
        target=_rebuild_worker,
        args=(db,),
        daemon=True,
        name="normalisation-map-rebuild",
    )
    thread.start()


def _rebuild_worker(db) -> None:
    """Background thread: regenerate map and update singleton."""
    global _rebuild_building
    try:
        norm_map = regenerate_normalisation_map(db)
        if norm_map is not None:
            logger.info(
                "[candlekeep] Background normalisation map rebuild complete "
                "(%d variants)", norm_map.size
            )
    except Exception:
        logger.exception("[candlekeep] Background normalisation map rebuild failed")
    finally:
        global _rebuild_building
        with _rebuild_lock:
            _rebuild_building = False


def regenerate_normalisation_map(db) -> Optional[NormalisationMap]:
    """Regenerate the normalisation map from the current corpus.

    Fetches all chunks from the database, extracts tokens, clusters them,
    and saves the new map to disk. Updates the in-memory singleton.

    Args:
        db: VectorDatabase instance

    Returns:
        Generated NormalisationMap, or None if corpus is empty
    """
    import time
    from candlekeep.config import Settings
    from candlekeep.rag.hybrid import _WORD_RE

    settings = Settings.from_env()
    output_path = settings.normalisation_map_path

    # Get all chunks from the database
    chunks = db.get_all_chunks()
    if not chunks:
        logger.info("[candlekeep] Empty corpus, skipping normalisation map generation")
        return None

    t0 = time.monotonic()

    # Extract tokens and compute frequencies — same expansion as _tokenize()
    # so the map is built from the same token space used at query time.
    token_frequencies: Dict[str, int] = {}
    for chunk in chunks:
        text = chunk.text.lower()
        for token in _WORD_RE.findall(text):
            token_frequencies[token] = token_frequencies.get(token, 0) + 1
            # Also count the stripped form
            if any(c in token for c in "-._"):
                stripped = token.replace("-", "").replace(".", "").replace("_", "")
                if stripped != token:
                    token_frequencies[stripped] = token_frequencies.get(stripped, 0) + 1

    if not token_frequencies:
        logger.info("[candlekeep] No tokens found in corpus")
        return None

    # Get embedding function from the database
    def embed_fn(texts: List[str]) -> List[List[float]]:
        return db.get_embeddings(texts)

    # Generate the map
    corpus_tokens = list(token_frequencies.keys())
    norm_map = generate_normalisation_map(corpus_tokens, token_frequencies, embed_fn, output_path)

    elapsed = time.monotonic() - t0
    logger.info("[candlekeep] Normalisation map generated in %.2fs", elapsed)

    # Update the in-memory singleton
    global _normalisation_map
    with _map_lock:
        _normalisation_map = norm_map

    return norm_map