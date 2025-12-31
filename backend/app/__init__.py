import os
from datetime import timedelta

from dotenv import load_dotenv
from flask import Flask, jsonify, request
from flask_cors import CORS
from flask_migrate import Migrate
from flask_smorest import Api

from .db import db
from .routes.auth import blp as auth_blp
from .routes.cart import blp as cart_blp
from .routes.health import blp as health_blp
from .routes.orders import blp as orders_blp
from .routes.products import blp as products_blp
from .routes.seed import blp as seed_blp


def _get_env(key: str, default: str | None = None) -> str | None:
    """Internal helper to fetch environment variables with optional defaults."""
    return os.getenv(key, default)


# PUBLIC_INTERFACE
def create_app() -> Flask:
    """Create and configure the Flask application.

    Loads environment configuration, wires PostgreSQL (SQLAlchemy), migrations,
    Flask-Smorest OpenAPI, registers all API blueprints, and installs JSON error handlers.

    Returns:
        Flask: Configured Flask app instance.
    """
    load_dotenv()

    app = Flask(__name__)
    app.url_map.strict_slashes = False

    # CORS
    cors_origins = _get_env("CORS_ORIGINS", "*")
    if cors_origins == "*" or cors_origins is None:
        CORS(app, resources={r"/*": {"origins": "*"}})
    else:
        origins = [o.strip() for o in cors_origins.split(",") if o.strip()]
        CORS(app, resources={r"/*": {"origins": origins}})

    # OpenAPI / Docs config
    app.config["API_TITLE"] = "Ecommerce API"
    app.config["API_VERSION"] = "v1"
    app.config["OPENAPI_VERSION"] = "3.0.3"
    app.config["OPENAPI_URL_PREFIX"] = "/docs"
    app.config["OPENAPI_SWAGGER_UI_PATH"] = ""
    app.config["OPENAPI_SWAGGER_UI_URL"] = "https://cdn.jsdelivr.net/npm/swagger-ui-dist/"

    app.config["SECRET_KEY"] = _get_env("SECRET_KEY", "dev-secret-key")

    # Database
    database_url = _get_env("DATABASE_URL")
    # NOTE: DATABASE_URL must be provided via .env in real deployments.
    # Example: postgresql+psycopg2://user:pass@database:5001/ecommerce_db
    if not database_url:
        # Keep app bootable even if DB isn't configured yet; routes requiring DB will error clearly.
        # This is helpful for CI and initial scaffolds.
        database_url = "sqlite+pysqlite:///:memory:"
    app.config["SQLALCHEMY_DATABASE_URI"] = database_url
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    # Auth config
    app.config["JWT_SECRET"] = _get_env("JWT_SECRET", "dev-jwt-secret")
    app.config["JWT_ACCESS_TOKEN_EXPIRES"] = timedelta(
        minutes=int(_get_env("JWT_ACCESS_TOKEN_EXPIRES_MINUTES", "60"))
    )

    db.init_app(app)
    Migrate(app, db)

    api = Api(app)

    # Error handlers (in addition to Flask-Smorest DEFAULT_ERROR)
    @app.errorhandler(404)
    def _not_found(_err):
        return jsonify({"message": "Not found"}), 404

    @app.errorhandler(400)
    def _bad_request(err):
        return jsonify({"message": "Bad request", "details": str(err)}), 400

    @app.errorhandler(500)
    def _server_error(err):
        return jsonify({"message": "Internal server error", "details": str(err)}), 500

    # Register routes
    api.register_blueprint(health_blp)
    api.register_blueprint(auth_blp)
    api.register_blueprint(products_blp)
    api.register_blueprint(cart_blp)
    api.register_blueprint(orders_blp)
    api.register_blueprint(seed_blp)

    # Helpful request ID echo (simple)
    @app.after_request
    def _after(resp):
        req_id = request.headers.get("X-Request-Id")
        if req_id:
            resp.headers["X-Request-Id"] = req_id
        return resp

    return app


# Backwards-compatible module-level app (used by run.py and generate_openapi.py)
app = create_app()
api = Api(app)
# Register blueprints on the module-level Api too (used by generate_openapi.py).
api.register_blueprint(health_blp)
api.register_blueprint(auth_blp)
api.register_blueprint(products_blp)
api.register_blueprint(cart_blp)
api.register_blueprint(orders_blp)
api.register_blueprint(seed_blp)
