from datetime import date, timedelta

from sqlalchemy import func

from models.replenishment import ReplenishmentItem, allocate_with_constraints, basket_totals

from ..extensions import db
from ..models import DemandHistory, InventoryBalance, Order, OrderLine, Product, Shop


def generate_recommendations(shop: Shop, supplier_id=None, budget=None):
    """Build constrained recommendations from the latest inventory and demand."""
    budget = float(shop.cash_budget if budget is None else budget)
    inventory_rows = InventoryBalance.query.filter_by(shop_id=shop.id).all()
    current_storage = sum(
        row.on_hand * float(row.product.storage_units_per_item) for row in inventory_rows
    )
    available_storage = max(0.0, shop.storage_capacity_units - current_storage)
    products = Product.query.filter_by(active=True)
    if supplier_id:
        products = products.filter_by(supplier_id=supplier_id)

    items = []
    cutoff = date.today() - timedelta(days=13)
    for product in products.order_by(Product.sku).all():
        balance = next((row for row in inventory_rows if row.product_id == product.id), None)
        on_hand = balance.on_hand if balance else 0
        daily_demand = _average_daily_demand(shop.id, product.id, cutoff)
        on_order = (
            db.session.query(func.coalesce(func.sum(OrderLine.quantity_ordered - OrderLine.quantity_received), 0))
            .join(Order)
            .filter(
                Order.shop_id == shop.id,
                Order.status.in_(["approved", "placed"]),
                OrderLine.product_id == product.id,
            )
            .scalar()
        )
        items.append(
            ReplenishmentItem(
                product_id=product.id,
                sku=product.sku,
                name=product.name,
                daily_demand=daily_demand,
                lead_time_days=product.supplier.lead_time_days,
                review_period_days=shop.review_period_days,
                safety_stock_days=shop.safety_stock_days,
                pack_size=product.pack_size,
                on_hand=on_hand,
                on_order=int(on_order or 0),
                unit_cost=float(product.unit_cost),
                storage_units_per_item=float(product.storage_units_per_item),
            )
        )

    delivery_fee = max(
        (float(product.supplier.delivery_fee) for product in products.all()), default=0.0
    )
    recommendations = allocate_with_constraints(items, budget, available_storage, delivery_fee)
    return recommendations, basket_totals(recommendations, delivery_fee)


def _average_daily_demand(shop_id, product_id, cutoff):
    total = (
        db.session.query(func.coalesce(func.sum(DemandHistory.quantity_sold), 0))
        .filter(
            DemandHistory.shop_id == shop_id,
            DemandHistory.product_id == product_id,
            DemandHistory.demand_date >= cutoff,
        )
        .scalar()
    )
    return round(float(total or 0) / 14, 2)
