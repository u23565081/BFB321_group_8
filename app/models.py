from datetime import datetime, timezone

from flask_login import UserMixin
from werkzeug.security import check_password_hash, generate_password_hash

from .extensions import db, login_manager


def utcnow():
    return datetime.now(timezone.utc)


class TimestampMixin:
    created_at = db.Column(db.DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at = db.Column(
        db.DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False
    )


class User(UserMixin, TimestampMixin, db.Model):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(160), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False, default="owner")
    shops = db.relationship("Shop", back_populates="owner")

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))


class Shop(TimestampMixin, db.Model):
    __tablename__ = "shops"
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(20), unique=True, nullable=False)
    name = db.Column(db.String(120), nullable=False)
    cash_budget = db.Column(db.Numeric(12, 2), nullable=False, default=2500)
    storage_capacity_units = db.Column(db.Integer, nullable=False, default=600)
    review_period_days = db.Column(db.Integer, nullable=False, default=3)
    safety_stock_days = db.Column(db.Integer, nullable=False, default=1)
    owner_user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    owner = db.relationship("User", back_populates="shops")
    inventory = db.relationship("InventoryBalance", back_populates="shop", cascade="all, delete-orphan")
    orders = db.relationship("Order", back_populates="shop", cascade="all, delete-orphan")


class Supplier(TimestampMixin, db.Model):
    __tablename__ = "suppliers"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    contact_phone = db.Column(db.String(30))
    lead_time_days = db.Column(db.Integer, nullable=False, default=2)
    delivery_fee = db.Column(db.Numeric(10, 2), nullable=False, default=0)
    products = db.relationship("Product", back_populates="supplier")


class Product(TimestampMixin, db.Model):
    __tablename__ = "products"
    id = db.Column(db.Integer, primary_key=True)
    sku = db.Column(db.String(40), unique=True, nullable=False, index=True)
    name = db.Column(db.String(120), nullable=False)
    category = db.Column(db.String(80), nullable=False)
    pack_size = db.Column(db.Integer, nullable=False)
    unit_cost = db.Column(db.Numeric(10, 2), nullable=False)
    storage_units_per_item = db.Column(db.Numeric(8, 3), nullable=False, default=1)
    active = db.Column(db.Boolean, nullable=False, default=True)
    supplier_id = db.Column(db.Integer, db.ForeignKey("suppliers.id"), nullable=False)
    supplier = db.relationship("Supplier", back_populates="products")


class InventoryBalance(TimestampMixin, db.Model):
    __tablename__ = "inventory_balances"
    id = db.Column(db.Integer, primary_key=True)
    shop_id = db.Column(db.Integer, db.ForeignKey("shops.id"), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey("products.id"), nullable=False)
    on_hand = db.Column(db.Integer, nullable=False, default=0)
    shop = db.relationship("Shop", back_populates="inventory")
    product = db.relationship("Product")
    __table_args__ = (
        db.UniqueConstraint("shop_id", "product_id", name="uq_inventory_shop_product"),
        db.CheckConstraint("on_hand >= 0", name="ck_inventory_non_negative"),
        db.Index("ix_inventory_shop_product", "shop_id", "product_id"),
    )


class StockMovement(TimestampMixin, db.Model):
    __tablename__ = "stock_movements"
    id = db.Column(db.Integer, primary_key=True)
    shop_id = db.Column(db.Integer, db.ForeignKey("shops.id"), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey("products.id"), nullable=False)
    movement_type = db.Column(db.String(20), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    note = db.Column(db.String(255))
    shop = db.relationship("Shop")
    product = db.relationship("Product")
    __table_args__ = (
        db.CheckConstraint("quantity != 0", name="ck_movement_non_zero"),
        db.Index("ix_movement_shop_product_date", "shop_id", "product_id", "created_at"),
    )


class DemandHistory(TimestampMixin, db.Model):
    __tablename__ = "demand_history"
    id = db.Column(db.Integer, primary_key=True)
    shop_id = db.Column(db.Integer, db.ForeignKey("shops.id"), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey("products.id"), nullable=False)
    demand_date = db.Column(db.Date, nullable=False)
    quantity_sold = db.Column(db.Integer, nullable=False)
    __table_args__ = (
        db.UniqueConstraint("shop_id", "product_id", "demand_date", name="uq_daily_demand"),
        db.Index("ix_demand_shop_product_date", "shop_id", "product_id", "demand_date"),
    )


class Order(TimestampMixin, db.Model):
    __tablename__ = "orders"
    id = db.Column(db.Integer, primary_key=True)
    shop_id = db.Column(db.Integer, db.ForeignKey("shops.id"), nullable=False)
    supplier_id = db.Column(db.Integer, db.ForeignKey("suppliers.id"), nullable=False)
    status = db.Column(db.String(20), nullable=False, default="draft", index=True)
    delivery_fee = db.Column(db.Numeric(10, 2), nullable=False, default=0)
    total_cost = db.Column(db.Numeric(12, 2), nullable=False, default=0)
    placed_at = db.Column(db.DateTime(timezone=True))
    expected_at = db.Column(db.DateTime(timezone=True))
    received_at = db.Column(db.DateTime(timezone=True))
    shop = db.relationship("Shop", back_populates="orders")
    supplier = db.relationship("Supplier")
    lines = db.relationship("OrderLine", back_populates="order", cascade="all, delete-orphan")


class OrderLine(TimestampMixin, db.Model):
    __tablename__ = "order_lines"
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey("orders.id"), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey("products.id"), nullable=False)
    quantity_ordered = db.Column(db.Integer, nullable=False)
    quantity_received = db.Column(db.Integer, nullable=False, default=0)
    unit_cost = db.Column(db.Numeric(10, 2), nullable=False)
    order = db.relationship("Order", back_populates="lines")
    product = db.relationship("Product")
    __table_args__ = (
        db.UniqueConstraint("order_id", "product_id", name="uq_order_product"),
        db.CheckConstraint("quantity_ordered > 0", name="ck_order_line_positive"),
    )
