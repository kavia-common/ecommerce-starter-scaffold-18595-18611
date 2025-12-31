from flask import g
from flask.views import MethodView
from flask_smorest import Blueprint, abort

from ..db import db
from ..deps import require_auth
from ..models import Cart, CartItem, Product
from ..schemas import CartAddItemSchema, CartSchema, CartUpdateItemSchema

blp = Blueprint("Cart", "cart", url_prefix="/cart", description="Shopping cart management")


def _get_or_create_active_cart(user_id: int) -> Cart:
    cart = (
        db.session.execute(
            db.select(Cart).where(Cart.user_id == user_id, Cart.status == "ACTIVE")
        )
        .scalar_one_or_none()
    )
    if cart:
        return cart
    cart = Cart(user_id=user_id, status="ACTIVE")
    db.session.add(cart)
    db.session.flush()
    return cart


def _serialize_cart(cart: Cart) -> dict:
    items_payload = []
    subtotal = 0
    for item in cart.items:
        line_total = item.quantity * item.product.price_cents
        subtotal += line_total
        items_payload.append(
            {
                "id": item.id,
                "product": item.product,
                "quantity": item.quantity,
                "line_total_cents": line_total,
            }
        )
    return {"id": cart.id, "status": cart.status, "items": items_payload, "subtotal_cents": subtotal}


@blp.route("")
class CartView(MethodView):
    @require_auth
    @blp.response(200, CartSchema)
    def get(self):
        """Get the current user's active cart."""
        cart = _get_or_create_active_cart(g.current_user.id)
        # ensure items relationship loaded
        db.session.refresh(cart)
        return _serialize_cart(cart)


@blp.route("/items")
class CartAddItem(MethodView):
    @require_auth
    @blp.arguments(CartAddItemSchema)
    @blp.response(200, CartSchema)
    def post(self, payload):
        """Add an item to cart (or increment quantity)."""
        product = db.session.get(Product, payload["product_id"])
        if not product or not product.is_active:
            abort(404, message="Product not found")

        cart = _get_or_create_active_cart(g.current_user.id)

        item = (
            db.session.execute(
                db.select(CartItem).where(CartItem.cart_id == cart.id, CartItem.product_id == product.id)
            )
            .scalar_one_or_none()
        )
        if item:
            item.quantity += payload["quantity"]
        else:
            item = CartItem(cart_id=cart.id, product_id=product.id, quantity=payload["quantity"])
            db.session.add(item)

        db.session.commit()
        cart = _get_or_create_active_cart(g.current_user.id)
        return _serialize_cart(cart)


@blp.route("/items/<int:item_id>")
class CartItemUpdateDelete(MethodView):
    @require_auth
    @blp.arguments(CartUpdateItemSchema)
    @blp.response(200, CartSchema)
    def put(self, payload, item_id: int):
        """Update cart item quantity."""
        cart = _get_or_create_active_cart(g.current_user.id)
        item = db.session.get(CartItem, item_id)
        if not item or item.cart_id != cart.id:
            abort(404, message="Cart item not found")

        item.quantity = payload["quantity"]
        db.session.commit()
        return _serialize_cart(cart)

    @require_auth
    @blp.response(200, CartSchema)
    def delete(self, item_id: int):
        """Remove an item from the cart."""
        cart = _get_or_create_active_cart(g.current_user.id)
        item = db.session.get(CartItem, item_id)
        if not item or item.cart_id != cart.id:
            abort(404, message="Cart item not found")

        db.session.delete(item)
        db.session.commit()
        return _serialize_cart(cart)


@blp.route("/clear")
class CartClear(MethodView):
    @require_auth
    @blp.response(200, CartSchema)
    def post(self):
        """Clear the active cart."""
        cart = _get_or_create_active_cart(g.current_user.id)
        for item in list(cart.items):
            db.session.delete(item)
        db.session.commit()
        return _serialize_cart(cart)
