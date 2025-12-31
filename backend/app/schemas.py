from __future__ import annotations

from marshmallow import Schema, fields, validate


class MessageSchema(Schema):
    message = fields.String(required=True)


class TokenSchema(Schema):
    access_token = fields.String(required=True)
    token_type = fields.String(required=True)
    expires_in_seconds = fields.Integer(required=True)


class UserPublicSchema(Schema):
    id = fields.Integer(required=True)
    email = fields.Email(required=True)
    name = fields.String(allow_none=True)
    created_at = fields.DateTime(required=True)


class UserRegisterSchema(Schema):
    email = fields.Email(required=True)
    password = fields.String(required=True, validate=validate.Length(min=8, max=128))
    name = fields.String(allow_none=True)


class UserLoginSchema(Schema):
    email = fields.Email(required=True)
    password = fields.String(required=True)


class ProductSchema(Schema):
    id = fields.Integer(required=True)
    sku = fields.String(required=True)
    name = fields.String(required=True)
    description = fields.String(allow_none=True)
    price_cents = fields.Integer(required=True)
    image_url = fields.String(allow_none=True)
    is_active = fields.Boolean(required=True)


class ProductCreateSchema(Schema):
    sku = fields.String(required=True, validate=validate.Length(min=1, max=64))
    name = fields.String(required=True, validate=validate.Length(min=1, max=200))
    description = fields.String(allow_none=True)
    price_cents = fields.Integer(required=True, validate=validate.Range(min=0))
    image_url = fields.String(allow_none=True)
    is_active = fields.Boolean(load_default=True)


class ProductListResponseSchema(Schema):
    items = fields.List(fields.Nested(ProductSchema), required=True)
    pagination = fields.Dict(required=True)


class CartItemSchema(Schema):
    id = fields.Integer(required=True)
    product = fields.Nested(ProductSchema, required=True)
    quantity = fields.Integer(required=True)
    line_total_cents = fields.Integer(required=True)


class CartSchema(Schema):
    id = fields.Integer(required=True)
    status = fields.String(required=True)
    items = fields.List(fields.Nested(CartItemSchema), required=True)
    subtotal_cents = fields.Integer(required=True)


class CartAddItemSchema(Schema):
    product_id = fields.Integer(required=True)
    quantity = fields.Integer(required=True, validate=validate.Range(min=1, max=999))


class CartUpdateItemSchema(Schema):
    quantity = fields.Integer(required=True, validate=validate.Range(min=1, max=999))


class ShippingAddressSchema(Schema):
    shipping_name = fields.String(required=True)
    shipping_address1 = fields.String(required=True)
    shipping_address2 = fields.String(allow_none=True)
    shipping_city = fields.String(required=True)
    shipping_state = fields.String(required=True)
    shipping_postal_code = fields.String(required=True)
    shipping_country = fields.String(required=True)


class OrderItemSchema(Schema):
    id = fields.Integer(required=True)
    product = fields.Nested(ProductSchema, required=True)
    quantity = fields.Integer(required=True)
    unit_price_cents = fields.Integer(required=True)
    line_total_cents = fields.Integer(required=True)


class OrderSchema(Schema):
    id = fields.Integer(required=True)
    status = fields.String(required=True)
    currency = fields.String(required=True)
    subtotal_cents = fields.Integer(required=True)
    total_cents = fields.Integer(required=True)
    created_at = fields.DateTime(required=True)
    items = fields.List(fields.Nested(OrderItemSchema), required=True)
    shipping_name = fields.String(allow_none=True)
    shipping_address1 = fields.String(allow_none=True)
    shipping_address2 = fields.String(allow_none=True)
    shipping_city = fields.String(allow_none=True)
    shipping_state = fields.String(allow_none=True)
    shipping_postal_code = fields.String(allow_none=True)
    shipping_country = fields.String(allow_none=True)


class OrderListResponseSchema(Schema):
    items = fields.List(fields.Nested(OrderSchema), required=True)
    pagination = fields.Dict(required=True)
