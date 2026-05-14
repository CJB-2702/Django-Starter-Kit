"""Shared utilities for the events app: UUID7 generation and URL-safe slug generation."""

from __future__ import annotations

import os
import time
import uuid


def generate_uuid7() -> uuid.UUID:
    """
    Generate a UUID version 7 (time-ordered, random).

    Structure (128 bits):
      [0:47]   unix_ts_ms  — 48-bit millisecond timestamp
      [48:51]  version     — 0x7
      [52:63]  rand_a      — 12 random bits
      [64:65]  variant     — 0b10
      [66:127] rand_b      — 62 random bits
    """
    unix_ts_ms = int(time.time() * 1000)
    rand_bits = int.from_bytes(os.urandom(10), "big")  # 80 random bits
    rand_a = (rand_bits >> 68) & 0xFFF   # top 12 bits
    rand_b = rand_bits & 0x3FFFFFFFFFFFFFFF  # low 62 bits

    uuid_int = (unix_ts_ms & 0xFFFFFFFFFFFF) << 80
    uuid_int |= 0x7 << 76       # version 7
    uuid_int |= rand_a << 64
    uuid_int |= 0x2 << 62       # variant 10xx
    uuid_int |= rand_b

    return uuid.UUID(int=uuid_int)


