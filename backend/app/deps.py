from __future__ import annotations

from functools import wraps

from flask import current_app, g, request

from .auth import verify_access_token
from .db import db
from .models import User


# PUBLIC_INTERFACE
def require_auth(fn):
    """Decorator that enforces Bearer token auth and sets g.current_user.

    Returns 401 if missing/invalid token.
    """

    @wraps(fn)
    def _wrapped(*args, **kwargs):
        header = request.headers.get("Authorization", "")
        if not header.startswith("Bearer "):
            return {"message": "Missing Bearer token"}, 401
        token = header.removeprefix("Bearer ").strip()
        max_age_seconds = int(current_app.config["JWT_ACCESS_TOKEN_EXPIRES"].total_seconds())
        user_id = verify_access_token(token, max_age_seconds=max_age_seconds)
        if not user_id:
            return {"message": "Invalid or expired token"}, 401

        user = db.session.get(User, user_id)
        if not user:
            return {"message": "User not found"}, 401

        g.current_user = user
        return fn(*args, **kwargs)

    return _wrapped
