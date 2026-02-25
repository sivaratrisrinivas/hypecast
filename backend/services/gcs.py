"""GCS client and signed URL generation for session recordings and reels."""

import os
from datetime import datetime, timedelta, timezone

DEFAULT_BUCKET = "hypecast-media"
REEL_EXPIRATION_SECONDS = 48 * 3600  # 48 hours


def upload_blob(
    blob_name: str,
    data: bytes,
    *,
    bucket_name: str | None = None,
) -> None:
    """
    Upload raw bytes to a GCS object (e.g. session raw.webm).

    :param blob_name: Object path in bucket, e.g. "sessions/sid123/raw.webm"
    :param data: Raw bytes to upload
    :param bucket_name: GCS bucket; default from GCS_BUCKET env or "hypecast-media"
    """
    from google.cloud import storage

    bucket_name = bucket_name or get_bucket_name()
    client = storage.Client()
    bucket = client.bucket(bucket_name)
    blob = bucket.blob(blob_name)
    blob.upload_from_string(data, content_type="video/webm")


def get_bucket_name() -> str:
    """Bucket name from env or default."""
    return os.environ.get("GCS_BUCKET", "").strip() or DEFAULT_BUCKET


def generate_signed_url(
    blob_name: str,
    *,
    bucket_name: str | None = None,
    expiration_seconds: int = REEL_EXPIRATION_SECONDS,
    method: str = "GET",
):
    """
    Generate a signed URL for a GCS object (e.g. reel MP4 or session raw.webm).

    Uses default credentials (GOOGLE_APPLICATION_CREDENTIALS or ADC).
    Returns a URL valid for expiration_seconds (default 48h for shareable reels).

    :param blob_name: Object path in bucket, e.g. "reels/abc123.mp4" or "sessions/sid/raw.webm"
    :param bucket_name: GCS bucket; default from GCS_BUCKET env or "hypecast-media"
    :param expiration_seconds: URL validity in seconds
    :param method: HTTP method for the signed URL ("GET" for download)
    :return: Signed URL string
    """
    from google.cloud import storage

    bucket_name = bucket_name or get_bucket_name()
    client = storage.Client()
    bucket = client.bucket(bucket_name)
    blob = bucket.blob(blob_name)
    expiration = datetime.now(timezone.utc) + timedelta(seconds=expiration_seconds)
    return blob.generate_signed_url(
        expiration=expiration,
        method=method,
        version="v4",
    )
