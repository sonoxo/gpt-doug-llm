"""Strict, bounded JSON and input validation shared by memory and inference."""
from __future__ import annotations

import json
import math
from typing import Any

MAX_BYTES = 1048576


def finite_number(value: Any, *, name: str, minimum: float,
                  maximum: float | None = None, exclusive_minimum: bool = False) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f'{name} must be a finite number')
    try:
        number = float(value)
    except (OverflowError, ValueError) as exc:
        raise ValueError(f'{name} must be finite') from exc
    if (not math.isfinite(number) or number < minimum or
            (exclusive_minimum and number == minimum) or
            (maximum is not None and number > maximum)):
        raise ValueError(f'{name} is outside its finite bounds')
    return number


def bounded_int(value: Any, *, name: str, minimum: int, maximum: int) -> int:
    if type(value) is not int or not minimum <= value <= maximum:
        raise ValueError(f'{name} must be an integer between {minimum} and {maximum}')
    return value


def bounded_text(value: Any, *, name: str, max_bytes: int) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f'{name} must be nonempty text')
    try:
        length = len(value.encode('utf-8'))
    except UnicodeError as exc:
        raise ValueError(f'{name} must be valid UTF-8') from exc
    if length > max_bytes:
        raise ValueError(f'{name} exceeds its UTF-8 byte limit')
    return value


def encode_json(value: Any, *, max_bytes: int = MAX_BYTES) -> bytes:
    bounded_int(max_bytes, name='max_bytes', minimum=1, maximum=MAX_BYTES)
    output = bytearray()
    try:
        encoder = json.JSONEncoder(sort_keys=True, ensure_ascii=False, allow_nan=False)
        for chunk in encoder.iterencode(value):
            output.extend(chunk.encode('utf-8'))
            if len(output) > max_bytes:
                raise ValueError('JSON exceeds byte limit')
    except (TypeError, UnicodeError, RecursionError, OverflowError) as exc:
        raise ValueError('Value is not bounded JSON') from exc
    return bytes(output)


def decode_json(raw: bytes, *, max_bytes: int = MAX_BYTES) -> Any:
    bounded_int(max_bytes, name='max_bytes', minimum=1, maximum=MAX_BYTES)
    if not isinstance(raw, bytes) or len(raw) > max_bytes:
        raise ValueError('JSON exceeds byte limit')
    def invalid_constant(value):
        raise ValueError('nonfinite JSON number')
    def unique_object(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError('duplicate JSON field')
            result[key] = value
        return result
    try:
        result = json.loads(raw.decode('utf-8'), parse_constant=invalid_constant,
                            object_pairs_hook=unique_object)
        encode_json(result, max_bytes=max_bytes)
        return result
    except (UnicodeError, RecursionError, OverflowError, TypeError) as exc:
        raise ValueError('invalid bounded UTF-8 JSON') from exc
