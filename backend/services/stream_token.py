"""Generate Stream Video SDK user tokens (JWT) for camera/spectator roles."""

from getstream import Stream


def create_stream_token(
    api_key: str,
    api_secret: str,
    user_id: str,
    expiration_seconds: int = 3600,
) -> str:
    """Create a Stream user JWT for the given user_id."""
    client = Stream(api_key=api_key, api_secret=api_secret)
    return client.create_token(user_id, expiration=expiration_seconds)
