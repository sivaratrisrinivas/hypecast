"""Tests for GCS signed URL generation (Sprint 3.3)."""

import sys
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest

from services.gcs import (
    DEFAULT_BUCKET,
    REEL_EXPIRATION_SECONDS,
    generate_signed_url,
    get_bucket_name,
)


def test_get_bucket_name_default() -> None:
    with patch.dict("os.environ", {}, clear=False):
        assert get_bucket_name() == DEFAULT_BUCKET


def test_get_bucket_name_from_env() -> None:
    with patch.dict("os.environ", {"GCS_BUCKET": "my-bucket"}, clear=False):
        assert get_bucket_name() == "my-bucket"


def test_get_bucket_name_strips_whitespace() -> None:
    with patch.dict("os.environ", {"GCS_BUCKET": "  my-bucket  "}, clear=False):
        assert get_bucket_name() == "my-bucket"


def test_generate_signed_url_builds_correct_parameters() -> None:
    """Mock google.cloud.storage and assert generate_signed_url is called with correct params."""
    mock_blob = MagicMock()
    mock_blob.generate_signed_url.return_value = "https://storage.example.com/signed"

    mock_bucket = MagicMock()
    mock_bucket.blob.return_value = mock_blob

    mock_client = MagicMock()
    mock_client.bucket.return_value = mock_bucket

    mock_storage = MagicMock()
    mock_storage.Client.return_value = mock_client
    # Satisfy "from google.cloud import storage" without real package
    mock_cloud = MagicMock()
    mock_cloud.storage = mock_storage

    with (
        patch.dict(
            sys.modules,
            {"google": MagicMock(), "google.cloud": mock_cloud, "google.cloud.storage": mock_storage},
        ),
        patch.dict("os.environ", {"GCS_BUCKET": ""}, clear=False),
    ):
        url = generate_signed_url(
            "reels/reel_xyz.mp4",
            bucket_name="hypecast-media",
            expiration_seconds=3600,
            method="GET",
        )

    assert url == "https://storage.example.com/signed"
    mock_client.bucket.assert_called_once_with("hypecast-media")
    mock_bucket.blob.assert_called_once_with("reels/reel_xyz.mp4")
    mock_blob.generate_signed_url.assert_called_once()
    call_kw = mock_blob.generate_signed_url.call_args[1]
    assert call_kw["method"] == "GET"
    assert call_kw["version"] == "v4"
    expiration = call_kw["expiration"]
    now_utc = datetime.now(timezone.utc)
    assert abs((expiration - now_utc).total_seconds() - 3600) < 5


def test_generate_signed_url_default_expiration_48h() -> None:
    mock_blob = MagicMock()
    mock_blob.generate_signed_url.return_value = "https://signed.example/url"

    mock_bucket = MagicMock()
    mock_bucket.blob.return_value = mock_blob

    mock_client = MagicMock()
    mock_client.bucket.return_value = mock_bucket

    mock_storage = MagicMock()
    mock_storage.Client.return_value = mock_client
    mock_cloud = MagicMock()
    mock_cloud.storage = mock_storage

    with (
        patch.dict(
            sys.modules,
            {"google": MagicMock(), "google.cloud": mock_cloud, "google.cloud.storage": mock_storage},
        ),
        patch("services.gcs.get_bucket_name", return_value=DEFAULT_BUCKET),
    ):
        generate_signed_url("sessions/sid123/raw.webm")

    call_kw = mock_blob.generate_signed_url.call_args[1]
    expiration = call_kw["expiration"]
    now_utc = datetime.now(timezone.utc)
    expected_seconds = REEL_EXPIRATION_SECONDS
    assert abs((expiration - now_utc).total_seconds() - expected_seconds) < 5
