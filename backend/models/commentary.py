from dataclasses import dataclass


@dataclass
class CommentaryEntry:
    timestamp: float           # seconds from session start
    text: str                  # raw commentary text
    energy_level: float        # 0.0–1.0
    is_highlight: bool         # flagged by energy threshold


HIGHLIGHT_KEYWORDS = [
    "INCREDIBLE",
    "UNBELIEVABLE",
    "WHAT A SHOT",
    "OH MY",
    "ARE YOU KIDDING",
    "AMAZING",
    "SPECTACULAR",
    "WOW",
]

ENERGY_THRESHOLD = 0.75        # entries above this are highlight candidates
