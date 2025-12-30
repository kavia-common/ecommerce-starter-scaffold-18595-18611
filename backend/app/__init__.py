from flask import Flask, jsonify
from flask_cors import CORS
from flask_smorest import Api

from .routes.health import blp as health_blp
from .routes.products import blp as products_blp
from .routes.cart import blp as cart_blp


app = Flask(__name__)
app.url_map.strict_slashes = False

# Enable CORS for all origins (ecommerce frontend consumption).
CORS(app, resources={r"/*": {"origins": "*"}})

# OpenAPI / Swagger UI configuration for flask-smorest
app.config["API_TITLE"] = "Ecommerce Backend API"
app.config["API_VERSION"] = "v1"
app.config["OPENAPI_VERSION"] = "3.0.3"
# Swagger UI will be served at /docs (root)
app.config["OPENAPI_URL_PREFIX"] = "/docs"
app.config["OPENAPI_SWAGGER_UI_PATH"] = ""
app.config["OPENAPI_SWAGGER_UI_URL"] = "https://cdn.jsdelivr.net/npm/swagger-ui-dist/"
# Ensure OpenAPI json is served at /openapi.json (expected by orchestrator and running container metadata)
app.config["OPENAPI_JSON_PATH"] = "/openapi.json"

api = Api(app)

# Register routes
api.register_blueprint(health_blp)
api.register_blueprint(products_blp)
api.register_blueprint(cart_blp)


@app.errorhandler(404)
def _not_found(_err):
    """Return consistent JSON error payload for unknown routes."""
    return jsonify({"code": 404, "status": "404", "message": "Not Found", "errors": {}}), 404


@app.errorhandler(500)
def _server_error(_err):
    """Return consistent JSON error payload for unhandled server errors."""
    return jsonify({"code": 500, "status": "500", "message": "Internal Server Error", "errors": {}}), 500
