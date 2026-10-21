from datetime import date, timedelta

from flask import Blueprint, abort, render_template, request
from flask_login import current_user, login_required
from sqlalchemy import func

from ..extensions import db
from ..models import InventoryBalance, Order, Product, Shop, StockMovement, Supplier


web_bp = Blueprint("web", __name__)


def current_shop():
    shop_id = request.args.get("shop_id", type=int)
    query = Shop.query
    if current_user.role != "admin":
        query = query.filter_by(owner_user_id=current_user.id)
    shop = query.filter_by(id=shop_id).first() if shop_id else query.order_by(Shop.id).first()
    if not shop:
        abort(403)
    return shop


@web_bp.route("/")
def home():
    return render_template("home.html")


@web_bp.route("/dashboard")
@login_required
def dashboard():
    shop = current_shop()
    balances = InventoryBalance.query.filter_by(shop_id=shop.id).all()
    inventory_value = sum(row.on_hand * float(row.product.unit_cost) for row in balances)
    low_stock = sum(1 for row in balances if row.on_hand <= row.product.pack_size)
    stockouts = sum(1 for row in balances if row.on_hand == 0)
    open_orders = Order.query.filter(
        Order.shop_id == shop.id, Order.status.in_(["approved", "placed"])
    ).count()
    recent_movements = (
        StockMovement.query.filter_by(shop_id=shop.id)
        .order_by(StockMovement.created_at.desc())
        .limit(6)
        .all()
    )
    return render_template(
        "dashboard.html",
        shop=shop,
        inventory_value=inventory_value,
        low_stock=low_stock,
        stockouts=stockouts,
        open_orders=open_orders,
        recent_movements=recent_movements,
        shops=Shop.query.filter_by(owner_user_id=current_user.id).all(),
    )


@web_bp.route("/inventory")
@login_required
def inventory():
    shop = current_shop()
    balances = (
        InventoryBalance.query.filter_by(shop_id=shop.id)
        .join(Product)
        .order_by(Product.name)
        .all()
    )
    return render_template("inventory.html", shop=shop, balances=balances)


@web_bp.route("/replenishment")
@login_required
def replenishment():
    shop = current_shop()
    return render_template(
        "replenishment.html", shop=shop, suppliers=Supplier.query.order_by(Supplier.name).all()
    )


@web_bp.route("/orders")
@login_required
def orders():
    shop = current_shop()
    rows = Order.query.filter_by(shop_id=shop.id).order_by(Order.created_at.desc()).all()
    return render_template("orders.html", shop=shop, orders=rows)


@web_bp.route("/impact")
@login_required
def impact():
    return render_template("impact.html", shop=current_shop())
