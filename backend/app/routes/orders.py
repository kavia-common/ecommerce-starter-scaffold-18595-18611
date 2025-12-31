from flask import g
from flask.views import MethodView
from flask_smorest import Blueprint, abort

from ..db import db
from ..deps import require_auth
from ..models import Cart, Order, OrderItem, Product
from ..pagination import build_pagination_metadata, get_pagination_params
from ..schemas import OrderListResponseSchema, OrderSchema, ShippingAddressSchema

blp = Blueprint("Orders", "orders", url_prefix="/orders", description="Orders and checkout")


def _active_cart(user_id: int) -> Cart | None:
    return (
        db.session.execute(db.select(Cart).where(Cart.user_id == user_id, Cart.status == "ACTIVE"))
        .scalar_one_or_none()
    )


def _serialize_order(order: Order) -> dict:
    items_payload = []
    for item in order.items:
        line_total = item.quantity * item.unit_price_cents
        items_payload.append(
            {
                "id": item.id,
                "product": item.product,
                "quantity": item.quantity,
                "unit_price_cents": item.unit_price_cents,
                "line_total_cents": line_total,
            }
        )
    return {
        "id": order.id,
        "status": order.status,
        "currency": order.currency,
        "subtotal_cents": order.subtotal_cents,
        "total_cents": order.total_cents,
        "created_at": order.created_at,
        "items": items_payload,
        "shipping_name": order.shipping_name,
        "shipping_address1": order.shipping_address1,
        "shipping_address2": order.shipping_address2,
        "shipping_city": order.shipping_city,
        "shipping_state": order.shipping_state,
        "shipping_postal_code": order.shipping_postal_code,
        "shipping_country": order.shipping_country,
    }


@blp.route("/checkout")
class Checkout(MethodView):
    @require_auth
    @blp.arguments(ShippingAddressSchema)
    @blp.response(201, OrderSchema)
    def post(self, payload):
        """Checkout the current active cart and create an order."""
        cart = _active_cart(g.current_user.id)
        if not cart:
            abort(400, message="No active cart")
        if not cart.items:
            abort(400, message="Cart is empty")

        # Compute totals and create order
        subtotal = 0
        for item in cart.items:
            # Ensure product still active
            product = db.session.get(Product, item.product_id)
            if not product or not product.is_active:
                abort(400, message=f"Product {item.product_id} no longer available")
            subtotal += item.quantity * product.price_cents

        total = subtotal  # taxes/shipping not modeled in scaffold

        order = Order(
            user_id=g.current_user.id,
            subtotal_cents=subtotal,
            total_cents=total,
            currency="USD",
            status="PLACED",
            **payload,
        )
        db.session.add(order)
        db.session.flush()

        for item in cart.items:
            product = db.session.get(Product, item.product_id)
            order_item = OrderItem(
                order_id=order.id,
                product_id=product.id,
                quantity=item.quantity,
                unit_price_cents=product.price_cents,
            )
            db.session.add(order_item)

        # Mark cart checked out and clear items
        cart.status = "CHECKED_OUT"
        for item in list(cart.items):
            db.session.delete(item)

        db.session.commit()
        db.session.refresh(order)
        return _serialize_order(order)


@blp.route("")
class OrderList(MethodView):
    @require_auth
    @blp.response(200, OrderListResponseSchema)
    def get(self):
        """List current user's orders with pagination."""
        page, page_size = get_pagination_params(default_page_size=10)
        q = (
            db.select(Order)
            .where(Order.user_id == g.current_user.id)
            .order_by(Order.created_at.desc())
        )

        total = db.session.execute(db.select(db.func.count()).select_from(q.subquery())).scalar_one()
        orders = (
            db.session.execute(q.offset((page - 1) * page_size).limit(page_size))
            .scalars()
            .all()
        )

        return {
            "items": [_serialize_order(o) for o in orders],
            "pagination": build_pagination_metadata(total, page, page_size),
        }


@blp.route("/<int:order_id>")
class OrderDetail(MethodView):
    @require_auth
    @blp.response(200, OrderSchema)
    def get(self, order_id: int):
        """Get a single order belonging to the current user."""
        order = db.session.get(Order, order_id)
        if not order or order.user_id != g.current_user.id:
            abort(404, message="Order not found")
        return _serialize_order(order)
