from flask.views import MethodView
from flask_smorest import Blueprint

from ..db import fetch_all, fetch_one
from ..errors import error_response
from ..schemas import ProductSchema

blp = Blueprint(
    "Products",
    "products",
    url_prefix="",
    description="Product catalog endpoints",
)


_PRODUCTS_SELECT = """
SELECT
  p.id,
  p.sku,
  p.name,
  p.description,
  p.image_url,
  p.price_cents,
  p.currency_code,
  p.active,
  COALESCE(i.quantity, 0) AS quantity,
  COALESCE(i.reserved, 0) AS reserved
FROM products p
LEFT JOIN inventory i ON i.product_id = p.id
WHERE p.active = TRUE
ORDER BY p.id ASC
"""


@blp.route("/products")
class ProductsCollection(MethodView):
    @blp.response(200, ProductSchema(many=True))
    def get(self):
        """List active products (includes inventory quantity/reserved)."""
        return fetch_all(_PRODUCTS_SELECT)


@blp.route("/products/<int:product_id>")
class ProductById(MethodView):
    @blp.response(200, ProductSchema)
    def get(self, product_id: int):
        """Get a single active product by id."""
        row = fetch_one(_PRODUCTS_SELECT + " AND p.id = %s", (product_id,))
        if not row:
            return error_response(404, f"Product {product_id} not found")
        return row
