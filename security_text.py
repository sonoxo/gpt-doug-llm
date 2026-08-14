"""Canonicalize untrusted text before deterministic policy checks."""

import re
import unicodedata


CONFUSABLES = str.maketrans({
    "а": "a", "е": "e", "о": "o", "р": "p", "с": "c", "х": "x",
    "і": "i", "ј": "j", "ѕ": "s", "Α": "A", "Β": "B", "Ε": "E",
    "Ο": "O", "Ρ": "P", "Χ": "X",
})


def normalize_security_text(text: str) -> str:
    value = unicodedata.normalize("NFKC", text).translate(CONFUSABLES)
    value = "".join(char for char in value if unicodedata.category(char) not in {"Cf", "Cc"} or char.isspace())
    return re.sub(r"\s+", " ", value).strip()
