from datetime import date, timedelta
from decimal import Decimal

from ..extensions import db
from ..models import DemandHistory, InventoryBalance, Product, Shop, Supplier, User


PRODUCTS = [
    ("MM-2.5", "Maize meal 2.5 kg", "Staples", 6, 32.50, 1.00, 0),
    ("RICE-2", "Rice 2 kg", "Staples", 6, 41.00, 0.80, 0),
    ("SUGAR-2", "Sugar 2 kg", "Staples", 10, 36.00, 0.70, 0),
    ("FLOUR-2.5", "Flour 2.5 kg", "Staples", 6, 34.00, 0.90, 0),
    ("OIL-2", "Cooking oil 2 L", "Staples", 6, 48.00, 0.70, 0),
    ("BEANS-410", "Baked beans 410 g", "Canned food", 12, 12.50, 0.25, 0),
    ("FISH-400", "Pilchards 400 g", "Canned food", 12, 18.00, 0.25, 0),
    ("MILK-1", "Long-life milk 1 L", "Beverages", 12, 16.00, 0.35, 0),
    ("TEA-100", "Tea 100 bags", "Beverages", 6, 42.00, 0.30, 0),
    ("COFFEE-200", "Instant coffee 200 g", "Beverages", 6, 55.00, 0.20, 0),
    ("SOAP-BAR", "Bath soap bar", "Household", 12, 9.00, 0.15, 1),
    ("WASH-1", "Washing powder 1 kg", "Household", 8, 29.00, 0.45, 1),
    ("DISH-750", "Dishwashing liquid 750 ml", "Household", 12, 18.50, 0.30, 1),
    ("TISSUE-9", "Toilet tissue 9 pack", "Household", 4, 48.00, 1.40, 1),
    ("TOOTH-100", "Toothpaste 100 ml", "Personal care", 12, 19.00, 0.12, 1),
    ("NAPKIN-10", "Sanitary pads 10 pack", "Personal care", 12, 16.00, 0.12, 1),
    ("BISCUIT-200", "Tea biscuits 200 g", "Snacks", 24, 7.50, 0.15, 1),
    ("CHIPS-125", "Potato chips 125 g", "Snacks", 20, 11.00, 0.20, 1),
    ("CANDLE-6", "Household candles 6 pack", "Household", 12, 18.00, 0.20, 1),
    ("MATCH-10", "Matches 10 pack", "Household", 20, 8.00, 0.08, 1),
]


def seed_database():
    """Create deterministic demonstration data for five modelled shops."""
    db.create_all()
    if User.query.filter_by(email="owner@demo.co.za").first():
        return

    owner = User(name="Thandi Mokoena", email="owner@demo.co.za", role="owner")
    owner.set_password("demo2026")
    admin = User(name="Project Administrator", email="admin@demo.co.za", role="admin")
    admin.set_password("admin2026")
    db.session.add_all([owner, admin])
    db.session.flush()

    shop_names = [
        ("SOW-01", "Thandi's Spaza", 2500, 600),
        ("SOW-02", "Vilakazi Mini Market", 3100, 720),
        ("SOW-03", "Maponya Corner Shop", 2200, 540),
        ("SOW-04", "Orlando Family Store", 2800, 650),
        ("SOW-05", "Kliptown Daily Needs", 1900, 480),
    ]
    shops = [
        Shop(
            code=code,
            name=name,
            cash_budget=Decimal(str(budget)),
            storage_capacity_units=capacity,
            owner_user_id=owner.id,
        )
        for code, name, budget, capacity in shop_names
    ]
    db.session.add_all(shops)

    suppliers = [
        Supplier(
            name="Soweto Cash & Carry",
            contact_phone="011 555 0141",
            lead_time_days=1,
            delivery_fee=Decimal("40.00"),
        ),
        Supplier(
            name="Jozi Wholesale Goods",
            contact_phone="011 555 0187",
            lead_time_days=2,
            delivery_fee=Decimal("55.00"),
        ),
    ]
    db.session.add_all(suppliers)
    db.session.flush()

    products = []
    for sku, name, category, pack, cost, storage, supplier_index in PRODUCTS:
        product = Product(
            sku=sku,
            name=name,
            category=category,
            pack_size=pack,
            unit_cost=Decimal(str(cost)),
            storage_units_per_item=Decimal(str(storage)),
            supplier_id=suppliers[supplier_index].id,
        )
        products.append(product)
    db.session.add_all(products)
    db.session.flush()

    for shop_index, shop in enumerate(shops):
        for product_index, product in enumerate(products):
            on_hand = 2 + ((product_index * 7 + shop_index * 3) % 24)
            db.session.add(
                InventoryBalance(shop_id=shop.id, product_id=product.id, on_hand=on_hand)
            )
            for day_offset in range(14):
                quantity = 1 + ((product_index + day_offset + shop_index) % 5)
                if product_index % 7 == 0 and day_offset % 4 == 0:
                    quantity += 2
                db.session.add(
                    DemandHistory(
                        shop_id=shop.id,
                        product_id=product.id,
                        demand_date=date.today() - timedelta(days=day_offset),
                        quantity_sold=quantity,
                    )
                )
    db.session.commit()

