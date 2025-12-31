from __future__ import annotations

from datetime import datetime


from sqlalchemy import CheckConstraint, ForeignKey, Index, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import db


class TimestampMixin:
    """Mixin adding created_at/updated_at timestamps."""

    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )


class User(db.Model, TimestampMixin):
    """Registered user account."""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(unique=True, index=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(nullable=False)
    name: Mapped[str | None] = mapped_column(nullable=True)

    carts: Mapped[list["Cart"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    orders: Mapped[list["Order"]] = relationship(back_populates="user", cascade="all, delete-orphan")


class Product(db.Model, TimestampMixin):
    """Sellable product."""

    __tablename__ = "products"

    id: Mapped[int] = mapped_column(primary_key=True)
    sku: Mapped[str] = mapped_column(unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(index=True, nullable=False)
    description: Mapped[str | None] = mapped_column(nullable=True)
    price_cents: Mapped[int] = mapped_column(nullable=False)
    image_url: Mapped[str | None] = mapped_column(nullable=True)
    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)

    __table_args__ = (
        CheckConstraint("price_cents >= 0", name="ck_products_price_nonnegative"),
        Index("ix_products_active_name", "is_active", "name"),
    )


class Cart(db.Model, TimestampMixin):
    """Shopping cart; we use one ACTIVE cart per user."""

    __tablename__ = "carts"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    status: Mapped[str] = mapped_column(default="ACTIVE", nullable=False)  # ACTIVE, CHECKED_OUT

    user: Mapped["User"] = relationship(back_populates="carts")
    items: Mapped[list["CartItem"]] = relationship(
        back_populates="cart", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("ix_carts_user_status", "user_id", "status"),
    )


class CartItem(db.Model, TimestampMixin):
    """Cart line item."""

    __tablename__ = "cart_items"

    id: Mapped[int] = mapped_column(primary_key=True)
    cart_id: Mapped[int] = mapped_column(ForeignKey("carts.id", ondelete="CASCADE"), nullable=False)
    product_id: Mapped[int] = mapped_column(
        ForeignKey("products.id", ondelete="RESTRICT"), nullable=False
    )
    quantity: Mapped[int] = mapped_column(nullable=False)

    cart: Mapped["Cart"] = relationship(back_populates="items")
    product: Mapped["Product"] = relationship()

    __table_args__ = (
        UniqueConstraint("cart_id", "product_id", name="uq_cart_item_cart_product"),
        CheckConstraint("quantity > 0", name="ck_cart_items_quantity_positive"),
        Index("ix_cart_items_cart", "cart_id"),
        Index("ix_cart_items_product", "product_id"),
    )


class Order(db.Model, TimestampMixin):
    """Order created from a cart checkout."""

    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)

    # Money values stored as integer cents.
    subtotal_cents: Mapped[int] = mapped_column(nullable=False)
    total_cents: Mapped[int] = mapped_column(nullable=False)

    currency: Mapped[str] = mapped_column(default="USD", nullable=False)
    status: Mapped[str] = mapped_column(default="PLACED", nullable=False)  # PLACED, PAID, CANCELED

    shipping_name: Mapped[str | None] = mapped_column(nullable=True)
    shipping_address1: Mapped[str | None] = mapped_column(nullable=True)
    shipping_address2: Mapped[str | None] = mapped_column(nullable=True)
    shipping_city: Mapped[str | None] = mapped_column(nullable=True)
    shipping_state: Mapped[str | None] = mapped_column(nullable=True)
    shipping_postal_code: Mapped[str | None] = mapped_column(nullable=True)
    shipping_country: Mapped[str | None] = mapped_column(nullable=True)

    user: Mapped["User"] = relationship(back_populates="orders")
    items: Mapped[list["OrderItem"]] = relationship(
        back_populates="order", cascade="all, delete-orphan"
    )

    __table_args__ = (
        CheckConstraint("subtotal_cents >= 0", name="ck_orders_subtotal_nonnegative"),
        CheckConstraint("total_cents >= 0", name="ck_orders_total_nonnegative"),
        Index("ix_orders_user_created", "user_id", "created_at"),
    )


class OrderItem(db.Model, TimestampMixin):
    """Order line item capturing price at time of purchase."""

    __tablename__ = "order_items"

    id: Mapped[int] = mapped_column(primary_key=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id", ondelete="CASCADE"), nullable=False)
    product_id: Mapped[int] = mapped_column(
        ForeignKey("products.id", ondelete="RESTRICT"), nullable=False
    )
    quantity: Mapped[int] = mapped_column(nullable=False)
    unit_price_cents: Mapped[int] = mapped_column(nullable=False)

    order: Mapped["Order"] = relationship(back_populates="items")
    product: Mapped["Product"] = relationship()

    __table_args__ = (
        CheckConstraint("quantity > 0", name="ck_order_items_quantity_positive"),
        CheckConstraint("unit_price_cents >= 0", name="ck_order_items_price_nonnegative"),
        Index("ix_order_items_order", "order_id"),
    )
