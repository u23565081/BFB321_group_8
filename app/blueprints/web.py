import json
from datetime import date, timedelta
from pathlib import Path

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


def _impact_results_path():
    return Path(__file__).resolve().parents[2] / "docs" / "generated" / "impact_results.json"


def _format_impact_value(kind, value):
    if kind == "money":
        return "R" + f"{value:,.2f}".replace(",", " ")
    if kind == "percent":
        return f"{value:.1f}%"
    return str(value)


def _impact_change(kind, baseline, observed):
    if kind == "percent":
        delta = round(observed - baseline, 1)
        if delta > 0:
            return f"{delta:.1f} percentage points higher"
        if delta < 0:
            return f"{abs(delta):.1f} percentage points lower"
        return "No change"
    if observed == baseline:
        return "No change"
    if baseline == 0:
        return "Baseline was zero"
    percent = abs(baseline - observed) / baseline * 100
    if kind == "money":
        direction = "lower" if observed < baseline else "higher"
    else:
        direction = "fewer" if observed < baseline else "more"
    return f"{percent:.1f}% {direction}"


def _impact_kpi_rows(results):
    specs = (
        ("Stockout SKU-days", "stockout_sku_days", "count"),
        ("Emergency collections", "emergency_collections", "count"),
        ("Emergency trip days", "emergency_trip_days", "count"),
        ("Average stock value", "average_stock_value", "money"),
        ("Availability", "availability_percent", "percent"),
        ("Cash breaches", "cash_breaches", "count"),
        ("Storage breach days", "storage_breach_days", "count"),
        ("Pack violations", "pack_violations", "count"),
    )
    reactive = results["reactive"]
    stockwise = results["stockwise"]
    rows = []
    for label, key, kind in specs:
        if key not in reactive or key not in stockwise:
            continue
        baseline = reactive[key]
        observed = stockwise[key]
        rows.append(
            {
                "label": label,
                "reactive": _format_impact_value(kind, baseline),
                "stockwise": _format_impact_value(kind, observed),
                "change": _impact_change(kind, baseline, observed),
            }
        )
    return rows


def _impact_sensitivity(results):
    runs = []
    for run in (results.get("sensitivity") or {}).get("runs", []):
        totals = run["total_stockout_sku_days"]
        runs.append(
            {
                "opening_cover": f"{run['opening_cover']:.1f}",
                "seed_count": run["seed_count"],
                "reached": run["seeds_with_at_least_20_percent_reduction"],
                "median": f"{run['median_reduction_percent']:.1f}",
                "minimum": f"{run['min_reduction_percent']:.1f}",
                "min_seed": run["min_reduction_seed"],
                "maximum": f"{run['max_reduction_percent']:.1f}",
                "max_seed": run["max_reduction_seed"],
                "reactive_stockouts": totals["reactive"],
                "stockwise_stockouts": totals["stockwise"],
                "stock_value_seeds": run["seeds_stock_value_at_or_below_baseline"],
                "breaches": run["stockwise_breach_events"],
                "emergency": run["stockwise_emergency_collections"],
            }
        )
    return runs


@web_bp.route("/impact")
@login_required
def impact():
    shop = current_shop()
    results_path = _impact_results_path()
    if not results_path.is_file():
        return render_template("impact.html", shop=shop, results_missing=True)

    results = json.loads(results_path.read_text(encoding="utf-8"))
    reactive_stockouts = results["reactive"]["stockout_sku_days"]
    stockwise_stockouts = results["stockwise"]["stockout_sku_days"]
    if reactive_stockouts:
        reduction = (reactive_stockouts - stockwise_stockouts) / reactive_stockouts * 100
        stockwise_bar = min(100.0, stockwise_stockouts / reactive_stockouts * 100)
    else:
        reduction = 0.0
        stockwise_bar = 0.0
    return render_template(
        "impact.html",
        shop=shop,
        results_missing=False,
        kpi_rows=_impact_kpi_rows(results),
        sensitivity_runs=_impact_sensitivity(results),
        reactive_stockouts=reactive_stockouts,
        stockwise_stockouts=stockwise_stockouts,
        stockout_reduction=f"{reduction:.1f}",
        stockwise_bar=f"{stockwise_bar:.1f}",
    )
