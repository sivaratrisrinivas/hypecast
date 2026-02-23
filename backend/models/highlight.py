from dataclasses import dataclass


@dataclass
class Highlight:
    start_time: float          # seconds from session start
    end_time: float            # start_time + clip duration
    energy_score: float        # peak energy in this window
    commentary_text: str       # commentary during this moment


@dataclass
class ReelJob:
    session_id: str
    highlights: list[Highlight]
    raw_video_gcs_path: str    # gs://bucket/sessions/{id}/raw.webm
    output_gcs_path: str       # gs://bucket/reels/{reel_id}.mp4
    status: str = "pending"    # pending | processing | done | error
