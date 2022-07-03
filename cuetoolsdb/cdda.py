#!/usr/bin/env python3

from dataclasses import dataclass
from enum import Enum

SAMPLES_PER_SECOND = 44100
FRAMES_PER_SECOND = 75
SAMPLES_PER_FRAME = SAMPLES_PER_SECOND / FRAMES_PER_SECOND
assert(SAMPLES_PER_FRAME == 588)

class TrackContents(Enum):
    audio = "audio"
    data = "data"


@dataclass(frozen=True, kw_only=True)
class Track:
    start: int
    """Start position in frames"""
    length: int
    """Length in frames"""
    contents: TrackContents = TrackContents.audio
    """Track contents"""

@dataclass(frozen=True, kw_only=True)
class TOC:
    tracks: list[Track]
    """Disc tracks"""
