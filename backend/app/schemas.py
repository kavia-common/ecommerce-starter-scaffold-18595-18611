from marshmallow import Schema, fields, validate


class ProductSchema(Schema):
    id = fields.Int(required=True, metadata={"description": "Product ID"})
    sku = fields.Str(required=True, metadata={"description": "Unique SKU"})
    name = fields.Str(required=True)
    description = fields.Str(required=True)
    image_url = fields.Str(allow_none=True)
    price_cents = fields.Int(required=True, validate=validate.Range(min=0))
    currency_code = fields.Str(required=True, validate=validate.Length(equal=3))
    active = fields.Bool(required=True)
    quantity = fields.Int(required=True, metadata={"description": "Available quantity (excluding reserved)"})
    reserved = fields.Int(required=True, metadata={"description": "Reserved quantity"})


class CartItemSchema(Schema):
    id = fields.Int(required=True)
    cart_id = fields.Int(required=True)
    product_id = fields.Int(required=True)
    quantity = fields.Int(required=True, validate=validate.Range(min=1))
    unit_price_cents = fields.Int(required=True, validate=validate.Range(min=0))
    currency_code = fields.Str(required=True, validate=validate.Length(equal=3))
    product = fields.Nested(ProductSchema, required=False, allow_none=True)


class CartSchema(Schema):
    id = fields.Int(required=True)
    status = fields.Str(required=True)
    created_at = fields.DateTime(allow_none=True)
    updated_at = fields.DateTime(allow_none=True)
    items = fields.List(fields.Nested(CartItemSchema), required=True)
    subtotal_cents = fields.Int(required=True)
    currency_code = fields.Str(required=True, validate=validate.Length(equal=3))


class CreateCartResponseSchema(Schema):
    cart_id = fields.Int(required=True)


class AddItemRequestSchema(Schema):
    product_id = fields.Int(required=True)
    quantity = fields.Int(required=True, validate=validate.Range(min=1))


class UpdateItemQuantityRequestSchema(Schema):
    quantity = fields.Int(required=True, validate=validate.Range(min=1))


class CheckoutRequestSchema(Schema):
    customer_email = fields.Email(required=False, allow_none=True)


class OrderItemSchema(Schema):
    id = fields.Int(required=True)
    order_id = fields.Int(required=True)
    product_id = fields.Int(allow_none=True)
    product_name = fields.Str(required=True)
    quantity = fields.Int(required=True)
    unit_price_cents = fields.Int(required=True)
    line_total_cents = fields.Int(required=True)
    currency_code = fields.Str(required=True, validate=validate.Length(equal=3))


class OrderSchema(Schema):
    id = fields.Int(required=True)
    cart_id = fields.Int(allow_none=True)
    status = fields.Str(required=True)
    customer_email = fields.Str(allow_none=True)
    subtotal_cents = fields.Int(required=True)
    tax_cents = fields.Int(required=True)
    shipping_cents = fields.Int(required=True)
    total_cents = fields.Int(required=True)
    currency_code = fields.Str(required=True)
    created_at = fields.DateTime(allow_none=True)
    updated_at = fields.DateTime(allow_none=True)
    items = fields.List(fields.Nested(OrderItemSchema), required=True)
