from flask.views import MethodView
from flask_smorest import Blueprint

blp = Blueprint("Health", "health", url_prefix="/", description="Health check route")


@blp.route("/")
class HealthCheck(MethodView):
    def get(self):
        """Health check endpoint."""
        return {"message": "Healthy"}
