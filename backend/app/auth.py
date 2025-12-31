from __future__ import annotations

from datetime import datetime, timezone

from flask import current_app
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


# PUBLIC_INTERFACE
def hash_password(password: str) -> str:
    """Hash a plaintext password using bcrypt."""
    return pwd_context.hash(password)


# PUBLIC_INTERFACE
def verify_password(password: str, password_hash: str) -> bool:
    """Verify plaintext password against a hash."""
    return pwd_context.verify(password, password_hash)


def _serializer() -> URLSafeTimedSerializer:
    secret = current_app.config.get("JWT_SECRET") or current_app.config.get("SECRET_KEY")
    return URLSafeTimedSerializer(secret_key=secret, salt="ecommerce-auth")


# PUBLIC_INTERFACE
def create_access_token(user_id: int) -> str:
    """Create a signed access token for a user_id.

    Note: this is a lightweight token for the scaffold; it is NOT a full JWT.
    """
    payload = {"sub": user_id, "iat": datetime.now(timezone.utc).isoformat()}
    return _serializer().dumps(payload)


# PUBLIC_INTERFACE
def verify_access_token(token: str, max_age_seconds: int) -> int | None:
    """Verify an access token and return user_id if valid."""
    try:
        data = _serializer().loads(token, max_age=max_age_seconds)
    except (BadSignature, SignatureExpired):
        return None
    user_id = data.get("sub")
    if not isinstance(user_id, int):
        return None
    return user_id
