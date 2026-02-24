"""Generate Stream Video SDK user tokens (JWT) for camera/spectator roles."""

import time

import jwt


def create_stream_token(
    api_key: str,
    api_secret: str,
    user_id: str,
    expiration_seconds: int = 3600,
) -> str:
    """Create a Stream user JWT for the given user_id.
    Sets iat 60s in the past to avoid AuthErrorTokenUsedBeforeIssuedAt when
    server or Stream clocks are slightly out of sync.
    """
    now = int(time.time())
    payload = {
        "user_id": user_id,
        "iat": now - 60,
        "exp": now + expiration_seconds,
    }
    return jwt.encode(
        payload,
        api_secret,
        algorithm="HS256",
    )
