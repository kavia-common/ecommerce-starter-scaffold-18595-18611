from flask.views import MethodView
from flask_smorest import Blueprint, abort
from sqlalchemy import or_

from ..db import db
from ..models import Product
from ..pagination import build_pagination_metadata, get_pagination_params
from ..schemas import ProductCreateSchema, ProductListResponseSchema, ProductSchema

blp = Blueprint(
    "Products",
    "products",
    url_prefix="/products",
    description="Product browsing and management",
)


@blp.route("")
class ProductList(MethodView):
    @blp.response(200, ProductListResponseSchema)
    def get(self):
        """List products with pagination and optional search.

        Query params:
          - page: 1-based page number
          - page_size: items per page
          - q: optional search string (matches sku or name)
        """
        from flask import request  # local import to keep module import-light

        page, page_size = get_pagination_params(default_page_size=12)

        q = db.select(Product).where(Product.is_active.is_(True)).order_by(Product.name.asc())

        query_str = request.args.get("q")
        if query_str:
            like = f"%{query_str.strip()}%"
            q = q.where(or_(Product.name.ilike(like), Product.sku.ilike(like)))

        total = db.session.execute(db.select(db.func.count()).select_from(q.subquery())).scalar_one()
        items = (
            db.session.execute(q.offset((page - 1) * page_size).limit(page_size))
            .scalars()
            .all()
        )

        return {"items": items, "pagination": build_pagination_metadata(total, page, page_size)}


@blp.route("/<int:product_id>")
class ProductDetail(MethodView):
    @blp.response(200, ProductSchema)
    def get(self, product_id: int):
        """Get a single product."""
        product = db.session.get(Product, product_id)
        if not product or not product.is_active:
            abort(404, message="Product not found")
        return product


@blp.route("")
class ProductCreate(MethodView):
    @blp.arguments(ProductCreateSchema)
    @blp.response(201, ProductSchema)
    def post(self, payload):
        """Create a product (no admin auth in scaffold)."""
        existing = (
            db.session.execute(db.select(Product).where(Product.sku == payload["sku"]))
            .scalar_one_or_none()
        )
        if existing:
            abort(409, message="SKU already exists")

        product = Product(**payload)
        db.session.add(product)
        db.session.commit()
        return product
