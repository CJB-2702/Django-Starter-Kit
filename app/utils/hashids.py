from __future__ import annotations

from hashids import Hashids
from django.conf import settings


def _hashids() -> Hashids:
    return Hashids(salt=settings.HASHIDS_SALT, min_length=8)


def encode_id(pk: int) -> str:
    """Encode an integer PK to an 8-character hashid string."""
    return _hashids().encode(pk)


def decode_hash(hash_str: str) -> int | None:
    """Decode a hashid string to an integer PK. Returns None if invalid."""
    result = _hashids().decode(hash_str)
    return result[0] if result else None
