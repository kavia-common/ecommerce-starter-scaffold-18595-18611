from flask.views import MethodView
from flask_smorest import Blueprint, abort

from ..auth import create_access_token, hash_password, verify_password
from ..db import db
from ..models import User
from ..schemas import TokenSchema, UserLoginSchema, UserPublicSchema, UserRegisterSchema
from ..deps import require_auth
from flask import g, current_app

blp = Blueprint("Auth", "auth", url_prefix="/auth", description="User registration and login")


@blp.route("/register")
class Register(MethodView):
    @blp.arguments(UserRegisterSchema)
    @blp.response(201, UserPublicSchema)
    def post(self, payload):
        """Register a new user."""
        existing = db.session.execute(db.select(User).where(User.email == payload["email"])).scalar_one_or_none()
        if existing:
            abort(409, message="Email already registered")

        user = User(
            email=payload["email"].lower(),
            password_hash=hash_password(payload["password"]),
            name=payload.get("name"),
        )
        db.session.add(user)
        db.session.commit()
        return user


@blp.route("/login")
class Login(MethodView):
    @blp.arguments(UserLoginSchema)
    @blp.response(200, TokenSchema)
    def post(self, payload):
        """Login and receive an access token."""
        user = db.session.execute(db.select(User).where(User.email == payload["email"].lower())).scalar_one_or_none()
        if not user or not verify_password(payload["password"], user.password_hash):
            abort(401, message="Invalid credentials")

        token = create_access_token(user.id)
        expires_in_seconds = int(current_app.config["JWT_ACCESS_TOKEN_EXPIRES"].total_seconds())
        return {"access_token": token, "token_type": "Bearer", "expires_in_seconds": expires_in_seconds}


@blp.route("/me")
class Me(MethodView):
    @require_auth
    @blp.response(200, UserPublicSchema)
    def get(self):
        """Get current authenticated user."""
        return g.current_user
