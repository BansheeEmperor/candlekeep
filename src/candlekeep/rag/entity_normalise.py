"""Entity name normalization: lowercase + strip separators."""
import re

_STRIP_RE = re.compile(r"[-_.]")


def normalise_entity(name: str) -> str:
    """Normalize entity name: lowercase and strip hyphens, underscores, dots.

    Examples:
        EXPANSION_SIMILARITY_THRESHOLD -> expansionsimilaritythreshold
        ArcaneRecall                   -> arcanerecall
        bge-small-en-v1.5              -> bgesmallenV15  (no, lowercase)
        cross-encoder                  -> crossencoder
    """
    return _STRIP_RE.sub("", name.lower())
