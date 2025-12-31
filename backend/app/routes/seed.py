from flask.views import MethodView
from flask_smorest import Blueprint

from ..auth import hash_password
from ..db import db
from ..models import Product, User
from ..schemas import MessageSchema

blp = Blueprint("Seed", "seed", url_prefix="/seed", description="Seed sample data into database")


SAMPLE_PRODUCTS = [
    {
        "sku": "OCEAN-TSHIRT-BLUE-S",
        "name": "Ocean T-Shirt (Blue, Small)",
        "description": "Soft cotton tee in ocean blue.",
        "price_cents": 1999,
        "image_url": "https://picsum.photos/seed/ocean-tee-blue-s/600/600",
        "is_active": True,
    },
    {
        "sku": "OCEAN-MUG-WHITE",
        "name": "Ocean Mug (White)",
        "description": "Ceramic mug with minimalist ocean motif.",
        "price_cents": 1499,
        "image_url": "https://picsum.photos/seed/ocean-mug/600/600",
        "is_active": True,
    },
    {
        "sku": "OCEAN-CAP-NAVY",
        "name": "Ocean Cap (Navy)",
        "description": "Navy cap with embroidered wave.",
        "price_cents": 2499,
        "image_url": "https://picsum.photos/seed/ocean-cap/600/600",
        "is_active": True,
    },
]


@blp.route("")
class SeedData(MethodView):
    @blp.response(200, MessageSchema)
    def post(self):
        """Seed products and a demo user.

        This endpoint is intentionally open in the scaffold. In production, protect it.
        """
        # Demo user
        demo_email = "demo@example.com"
        demo = db.session.execute(db.select(User).where(User.email == demo_email)).scalar_one_or_none()
        if not demo:
            demo = User(email=demo_email, password_hash=hash_password("password123"), name="Demo User")
            db.session.add(demo)

        # Products
        created = 0
        for p in SAMPLE_PRODUCTS:
            existing = db.session.execute(db.select(Product).where(Product.sku == p["sku"])).scalar_one_or_none()
            if not existing:
                db.session.add(Product(**p))
                created += 1

        db.session.commit()
        return {"message": f"Seed complete. Created {created} product(s). Demo user: {demo_email} / password123"}
