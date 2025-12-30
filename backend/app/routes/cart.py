from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from flask.views import MethodView
from flask_smorest import Blueprint
from psycopg2.extras import RealDictCursor

from ..db import get_conn
from ..errors import error_response
from ..schemas import (
    AddItemRequestSchema,
    CartSchema,
    CheckoutRequestSchema,
    CreateCartResponseSchema,
    OrderSchema,
    UpdateItemQuantityRequestSchema,
)

blp = Blueprint(
    "Cart",
    "cart",
    url_prefix="",
    description="Shopping cart and checkout endpoints",
)


def _cart_exists_open(cur: Any, cart_id: int) -> Optional[Dict[str, Any]]:
    cur.execute("SELECT id, status, created_at, updated_at FROM carts WHERE id=%s", (cart_id,))
    row = cur.fetchone()
    return dict(row) if row else None


def _get_product_for_sale(cur: Any, product_id: int) -> Optional[Dict[str, Any]]:
    cur.execute(
        """
        SELECT p.id, p.name, p.price_cents, p.currency_code, p.active,
               COALESCE(i.quantity, 0) AS quantity, COALESCE(i.reserved, 0) AS reserved
        FROM products p
        LEFT JOIN inventory i ON i.product_id = p.id
        WHERE p.id=%s
        """,
        (product_id,),
    )
    row = cur.fetchone()
    return dict(row) if row else None


def _compute_cart_subtotal(items: List[Dict[str, Any]]) -> Tuple[int, str]:
    subtotal = 0
    currency = "USD"
    for it in items:
        subtotal += int(it["quantity"]) * int(it["unit_price_cents"])
        currency = it.get("currency_code") or currency
    return subtotal, currency


def _get_cart_with_items(cur: Any, cart_id: int) -> Optional[Dict[str, Any]]:
    cart = _cart_exists_open(cur, cart_id)
    if not cart:
        return None

    cur.execute(
        """
        SELECT
          ci.id,
          ci.cart_id,
          ci.product_id,
          ci.quantity,
          ci.unit_price_cents,
          ci.currency_code,
          p.sku,
          p.name,
          p.description,
          p.image_url,
          p.active,
          COALESCE(i.quantity, 0) AS quantity,
          COALESCE(i.reserved, 0) AS reserved,
          p.price_cents,
          p.currency_code AS product_currency_code
        FROM cart_items ci
        JOIN products p ON p.id = ci.product_id
        LEFT JOIN inventory i ON i.product_id = p.id
        WHERE ci.cart_id = %s
        ORDER BY ci.id ASC
        """,
        (cart_id,),
    )
    rows = [dict(r) for r in cur.fetchall()]
    items: List[Dict[str, Any]] = []
    for r in rows:
        product = {
            "id": r["product_id"],
            "sku": r["sku"],
            "name": r["name"],
            "description": r["description"],
            "image_url": r["image_url"],
            "price_cents": r["price_cents"],
            "currency_code": r["product_currency_code"],
            "active": r["active"],
            "quantity": r["quantity"],
            "reserved": r["reserved"],
        }
        items.append(
            {
                "id": r["id"],
                "cart_id": r["cart_id"],
                "product_id": r["product_id"],
                "quantity": r["quantity"],
                "unit_price_cents": r["unit_price_cents"],
                "currency_code": r["currency_code"],
                "product": product,
            }
        )

    subtotal_cents, currency_code = _compute_cart_subtotal(items)
    return {
        **cart,
        "items": items,
        "subtotal_cents": subtotal_cents,
        "currency_code": currency_code,
    }


@blp.route("/carts")
class CartsCollection(MethodView):
    @blp.response(201, CreateCartResponseSchema)
    def post(self):
        """Create a new cart (status=open)."""
        with get_conn() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("INSERT INTO carts(status) VALUES('open') RETURNING id")
                cart_id = cur.fetchone()["id"]
                return {"cart_id": cart_id}


@blp.route("/carts/<int:cart_id>")
class CartById(MethodView):
    @blp.response(200, CartSchema)
    def get(self, cart_id: int):
        """Get cart and its items."""
        with get_conn() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cart = _get_cart_with_items(cur, cart_id)
                if not cart:
                    return error_response(404, f"Cart {cart_id} not found")
                return cart

    def delete(self, cart_id: int):
        """Clear cart items (keeps cart)."""
        with get_conn() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cart = _cart_exists_open(cur, cart_id)
                if not cart:
                    return error_response(404, f"Cart {cart_id} not found")
                if cart["status"] != "open":
                    return error_response(409, f"Cart {cart_id} is not open and cannot be cleared")
                cur.execute("DELETE FROM cart_items WHERE cart_id=%s", (cart_id,))
                cur.execute("UPDATE carts SET updated_at=NOW() WHERE id=%s", (cart_id,))
                return {"message": "Cart cleared"}, 200


@blp.route("/carts/<int:cart_id>/items")
class CartItemsCollection(MethodView):
    @blp.arguments(AddItemRequestSchema)
    @blp.response(200, CartSchema)
    def post(self, payload: Dict[str, Any], cart_id: int):
        """Add an item to cart (or increment quantity if already present)."""
        product_id = int(payload["product_id"])
        add_qty = int(payload["quantity"])

        with get_conn() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cart = _cart_exists_open(cur, cart_id)
                if not cart:
                    return error_response(404, f"Cart {cart_id} not found")
                if cart["status"] != "open":
                    return error_response(409, f"Cart {cart_id} is not open and cannot be modified")

                product = _get_product_for_sale(cur, product_id)
                if not product or not product.get("active"):
                    return error_response(404, f"Product {product_id} not found")

                available = int(product["quantity"]) - int(product["reserved"])
                if available < add_qty:
                    return error_response(
                        409,
                        f"Insufficient inventory for product {product_id}",
                        errors={"available": available, "requested": add_qty},
                    )

                # Upsert cart item (unique constraint on (cart_id, product_id))
                cur.execute(
                    """
                    INSERT INTO cart_items(cart_id, product_id, quantity, unit_price_cents, currency_code)
                    VALUES (%s, %s, %s, %s, %s)
                    ON CONFLICT (cart_id, product_id)
                    DO UPDATE SET
                      quantity = cart_items.quantity + EXCLUDED.quantity,
                      updated_at = NOW()
                    RETURNING id
                    """,
                    (cart_id, product_id, add_qty, product["price_cents"], product["currency_code"]),
                )
                cur.execute("UPDATE carts SET updated_at=NOW() WHERE id=%s", (cart_id,))

                cart_full = _get_cart_with_items(cur, cart_id)
                return cart_full


@blp.route("/carts/<int:cart_id>/items/<int:product_id>")
class CartItemByProduct(MethodView):
    @blp.arguments(UpdateItemQuantityRequestSchema)
    @blp.response(200, CartSchema)
    def put(self, payload: Dict[str, Any], cart_id: int, product_id: int):
        """Update quantity for a product in the cart (quantity >= 1)."""
        qty = int(payload["quantity"])

        with get_conn() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cart = _cart_exists_open(cur, cart_id)
                if not cart:
                    return error_response(404, f"Cart {cart_id} not found")
                if cart["status"] != "open":
                    return error_response(409, f"Cart {cart_id} is not open and cannot be modified")

                product = _get_product_for_sale(cur, product_id)
                if not product or not product.get("active"):
                    return error_response(404, f"Product {product_id} not found")

                available = int(product["quantity"]) - int(product["reserved"])
                if available < qty:
                    return error_response(
                        409,
                        f"Insufficient inventory for product {product_id}",
                        errors={"available": available, "requested": qty},
                    )

                cur.execute(
                    """
                    UPDATE cart_items
                    SET quantity=%s, updated_at=NOW()
                    WHERE cart_id=%s AND product_id=%s
                    """,
                    (qty, cart_id, product_id),
                )
                if cur.rowcount == 0:
                    return error_response(404, f"Cart item not found for product {product_id} in cart {cart_id}")

                cur.execute("UPDATE carts SET updated_at=NOW() WHERE id=%s", (cart_id,))
                cart_full = _get_cart_with_items(cur, cart_id)
                return cart_full

    @blp.response(200, CartSchema)
    def delete(self, cart_id: int, product_id: int):
        """Remove a product from cart."""
        with get_conn() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cart = _cart_exists_open(cur, cart_id)
                if not cart:
                    return error_response(404, f"Cart {cart_id} not found")
                if cart["status"] != "open":
                    return error_response(409, f"Cart {cart_id} is not open and cannot be modified")

                cur.execute("DELETE FROM cart_items WHERE cart_id=%s AND product_id=%s", (cart_id, product_id))
                if cur.rowcount == 0:
                    return error_response(404, f"Cart item not found for product {product_id} in cart {cart_id}")

                cur.execute("UPDATE carts SET updated_at=NOW() WHERE id=%s", (cart_id,))
                cart_full = _get_cart_with_items(cur, cart_id)
                return cart_full


@blp.route("/checkout")
class Checkout(MethodView):
    @blp.arguments(CheckoutRequestSchema)
    @blp.response(201, OrderSchema)
    def post(self, payload: Dict[str, Any]):
        """
        Checkout a cart and create an order.

        Body:
          - cart_id (required, passed as query param ?cart_id=... to keep Angular-friendly simple call patterns)
          - customer_email (optional, JSON)

        Note: This implementation keeps tax/shipping at 0 for now.
        """
        # allow cart_id via query param to keep JSON simple across frontends
        from flask import request

        cart_id_raw = request.args.get("cart_id")
        if not cart_id_raw:
            return error_response(400, "Missing required query parameter: cart_id")
        try:
            cart_id = int(cart_id_raw)
        except ValueError:
            return error_response(400, "cart_id must be an integer")

        customer_email = payload.get("customer_email")

        with get_conn() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cart = _cart_exists_open(cur, cart_id)
                if not cart:
                    return error_response(404, f"Cart {cart_id} not found")
                if cart["status"] != "open":
                    return error_response(409, f"Cart {cart_id} is not open and cannot be checked out")

                cart_full = _get_cart_with_items(cur, cart_id)
                if not cart_full or len(cart_full["items"]) == 0:
                    return error_response(400, "Cannot checkout an empty cart")

                # Validate inventory again and decrement.
                for it in cart_full["items"]:
                    product_id = int(it["product_id"])
                    qty = int(it["quantity"])
                    product = _get_product_for_sale(cur, product_id)
                    if not product or not product.get("active"):
                        return error_response(409, f"Product {product_id} is no longer available")
                    available = int(product["quantity"]) - int(product["reserved"])
                    if available < qty:
                        return error_response(
                            409,
                            f"Insufficient inventory for product {product_id}",
                            errors={"available": available, "requested": qty},
                        )

                # Decrement inventory quantities
                for it in cart_full["items"]:
                    cur.execute(
                        "UPDATE inventory SET quantity = quantity - %s, updated_at=NOW() WHERE product_id=%s",
                        (int(it["quantity"]), int(it["product_id"])),
                    )

                subtotal_cents = int(cart_full["subtotal_cents"])
                tax_cents = 0
                shipping_cents = 0
                total_cents = subtotal_cents + tax_cents + shipping_cents
                currency_code = cart_full["currency_code"]

                # Create order
                cur.execute(
                    """
                    INSERT INTO orders(cart_id, status, customer_email, subtotal_cents, tax_cents, shipping_cents, total_cents, currency_code)
                    VALUES (%s, 'placed', %s, %s, %s, %s, %s, %s)
                    RETURNING id, cart_id, status, customer_email, subtotal_cents, tax_cents, shipping_cents, total_cents, currency_code, created_at, updated_at
                    """,
                    (cart_id, customer_email, subtotal_cents, tax_cents, shipping_cents, total_cents, currency_code),
                )
                order_row = dict(cur.fetchone())
                order_id = int(order_row["id"])

                # Create order_items snapshot
                items_out: List[Dict[str, Any]] = []
                for it in cart_full["items"]:
                    cur.execute(
                        """
                        INSERT INTO order_items(order_id, product_id, product_name, quantity, unit_price_cents, line_total_cents, currency_code)
                        VALUES (%s, %s, %s, %s, %s, %s, %s)
                        RETURNING id, order_id, product_id, product_name, quantity, unit_price_cents, line_total_cents, currency_code, created_at
                        """,
                        (
                            order_id,
                            int(it["product_id"]),
                            it["product"]["name"] if it.get("product") else "Unknown",
                            int(it["quantity"]),
                            int(it["unit_price_cents"]),
                            int(it["quantity"]) * int(it["unit_price_cents"]),
                            it["currency_code"],
                        ),
                    )
                    items_out.append(dict(cur.fetchone()))

                # Mark cart checked_out and clear items (optional; keep for record via orders.cart_id)
                cur.execute("UPDATE carts SET status='checked_out', updated_at=NOW() WHERE id=%s", (cart_id,))
                cur.execute("DELETE FROM cart_items WHERE cart_id=%s", (cart_id,))

                return {
                    **order_row,
                    "items": items_out,
                }
