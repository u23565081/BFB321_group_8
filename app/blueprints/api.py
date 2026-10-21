from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

from flask import Blueprint, current_app, jsonify, request
from flask_login import current_user, login_required
from sqlalchemy import func, or_

from ..extensions import db
from ..models import (
    DemandHistory,
    InventoryBalance,
    Order,
    OrderLine,
    Product,
    Shop,
    StockMovement,
    Supplier,
)
from ..services.replenishment_service import generate_recommendations


api_bp = Blueprint("api", __name__)


def error(message, status=400, code="validation_error", fields=None):
    payload = {"error": code, "message": message}
    if fields:
        payload["fields"] = fields
    return jsonify(payload), status


def owned_shop(shop_id=None):
    query = Shop.query
    if current_user.role != "admin":
        query = query.filter_by(owner_user_id=current_user.id)
    if shop_id:
        return query.filter_by(id=shop_id).first()
    return query.order_by(Shop.id).first()


@api_bp.get("/inventory")
@login_required
def inventory_list():
    shop = owned_shop(request.args.get("shop_id", type=int))
    if not shop:
        return error("Shop not found or access denied.", 404, "not_found")
    page = max(1, request.args.get("page", 1, type=int))
    per_page = min(50, max(1, request.args.get("per_page", current_app.config["ITEMS_PER_PAGE"], type=int)))
    search = request.args.get("q", "").strip()
    query = InventoryBalance.query.filter_by(shop_id=shop.id).join(Product)
    if search:
        query = query.filter(or_(Product.name.ilike(f"%{search}%"), Product.sku.ilike(f"%{search}%")))
    pagination = query.order_by(Product.name).paginate(page=page, per_page=per_page, error_out=False)
    return jsonify(
        {
            "items": [serialize_inventory(row) for row in pagination.items],
            "page": pagination.page,
            "pages": pagination.pages,
            "total": pagination.total,
        }
    )


@api_bp.post("/movements")
@login_required
def create_movement():
    data = request.get_json(silent=True) or {}
    required = {"shop_id", "product_id", "movement_type", "quantity"}
    missing = sorted(required - data.keys())
    if missing:
        return error("Please complete all required fields.", fields=missing)
    shop = owned_shop(_int(data.get("shop_id")))
    if not shop:
        return error("Shop not found or access denied.", 404, "not_found")
    movement_type = str(data.get("movement_type", "")).lower()
    allowed = {"sale", "loss", "receipt", "return", "adjustment_in", "adjustment_out"}
    if movement_type not in allowed:
        return error("Movement type is not supported.", fields=["movement_type"])
    quantity = _int(data.get("quantity"))
    if not quantity or quantity <= 0:
        return error("Quantity must be a whole number greater than zero.", fields=["quantity"])
    product = db.session.get(Product, _int(data.get("product_id")))
    if not product:
        return error("Product not found.", 404, "not_found")
    balance = InventoryBalance.query.filter_by(shop_id=shop.id, product_id=product.id).first()
    if not balance:
        balance = InventoryBalance(shop_id=shop.id, product_id=product.id, on_hand=0)
        db.session.add(balance)
    direction = -1 if movement_type in {"sale", "loss", "adjustment_out"} else 1
    signed_quantity = direction * quantity
    if balance.on_hand + signed_quantity < 0:
        return error(
            f"Only {balance.on_hand} units are available. The balance cannot be negative.",
            fields=["quantity"],
        )
    balance.on_hand += signed_quantity
    movement = StockMovement(
        shop_id=shop.id,
        product_id=product.id,
        movement_type=movement_type,
        quantity=signed_quantity,
        note=str(data.get("note", ""))[:255],
    )
    db.session.add(movement)
    if movement_type == "sale":
        demand = DemandHistory.query.filter_by(
            shop_id=shop.id, product_id=product.id, demand_date=date.today()
        ).first()
        if demand:
            demand.quantity_sold += quantity
        else:
            db.session.add(
                DemandHistory(
                    shop_id=shop.id,
                    product_id=product.id,
                    demand_date=date.today(),
                    quantity_sold=quantity,
                )
            )
    db.session.commit()
    current_app.logger.info("Movement %s recorded for product %s", movement_type, product.sku)
    return jsonify({"message": "Stock movement recorded.", "item": serialize_inventory(balance)}), 201


@api_bp.get("/recommendations")
@login_required
def recommendations():
    shop = owned_shop(request.args.get("shop_id", type=int))
    if not shop:
        return error("Shop not found or access denied.", 404, "not_found")
    supplier_id = request.args.get("supplier_id", type=int)
    budget = request.args.get("budget", type=float)
    if budget is not None and budget < 0:
        return error("Budget cannot be negative.", fields=["budget"])
    items, totals = generate_recommendations(shop, supplier_id=supplier_id, budget=budget)
    return jsonify(
        {
            "items": [serialize_recommendation(item) for item in items],
            "totals": totals,
            "provisional": any(item.daily_demand == 0 for item in items),
            "message": "Some results are provisional because demand history is missing."
            if any(item.daily_demand == 0 for item in items)
            else "Recommendations use the latest 14 days of demand.",
        }
    )


@api_bp.get("/orders")
@login_required
def order_list():
    shop = owned_shop(request.args.get("shop_id", type=int))
    if not shop:
        return error("Shop not found or access denied.", 404, "not_found")
    page = max(1, request.args.get("page", 1, type=int))
    per_page = min(50, max(1, request.args.get("per_page", 10, type=int)))
    query = Order.query.filter_by(shop_id=shop.id)
    status = request.args.get("status")
    if status:
        query = query.filter_by(status=status)
    pagination = query.order_by(Order.created_at.desc()).paginate(page=page, per_page=per_page, error_out=False)
    return jsonify(
        {"items": [serialize_order(row) for row in pagination.items], "page": page, "pages": pagination.pages, "total": pagination.total}
    )


@api_bp.post("/orders")
@login_required
def create_order():
    data = request.get_json(silent=True) or {}
    shop = owned_shop(_int(data.get("shop_id")))
    if not shop:
        return error("Shop not found or access denied.", 404, "not_found")
    supplier = db.session.get(Supplier, _int(data.get("supplier_id")))
    lines = data.get("lines")
    if not supplier or not isinstance(lines, list) or not lines:
        return error("Choose a supplier and at least one product.")
    order = Order(
        shop_id=shop.id,
        supplier_id=supplier.id,
        status="draft",
        delivery_fee=supplier.delivery_fee,
    )
    db.session.add(order)
    product_cost = Decimal("0")
    seen = set()
    for index, raw_line in enumerate(lines):
        product = db.session.get(Product, _int(raw_line.get("product_id")))
        quantity = _int(raw_line.get("quantity"))
        if not product or product.supplier_id != supplier.id:
            db.session.rollback()
            return error(f"Line {index + 1} does not belong to the selected supplier.")
        if product.id in seen or not quantity or quantity <= 0 or quantity % product.pack_size != 0:
            db.session.rollback()
            return error(f"Line {index + 1} must be unique and use full packs of {product.pack_size}.")
        seen.add(product.id)
        db.session.add(
            OrderLine(
                order=order,
                product_id=product.id,
                quantity_ordered=quantity,
                unit_cost=product.unit_cost,
            )
        )
        product_cost += product.unit_cost * quantity
    order.total_cost = product_cost + supplier.delivery_fee
    db.session.commit()
    return jsonify({"message": "Draft order created.", "order": serialize_order(order)}), 201


@api_bp.post("/orders/<int:order_id>/approve")
@login_required
def approve_order(order_id):
    order = accessible_order(order_id)
    if not order:
        return error("Order not found or access denied.", 404, "not_found")
    if order.status != "draft":
        return error("Only draft orders can be approved.", 409, "invalid_status")
    if order.total_cost > order.shop.cash_budget:
        return error("The order is above the shop's cash budget.", 409, "constraint_violation")
    current_storage = sum(
        row.on_hand * float(row.product.storage_units_per_item) for row in order.shop.inventory
    )
    incoming_storage = sum(
        line.quantity_ordered * float(line.product.storage_units_per_item) for line in order.lines
    )
    if current_storage + incoming_storage > order.shop.storage_capacity_units:
        return error("The order is above the shop's storage capacity.", 409, "constraint_violation")
    order.status = "approved"
    order.placed_at = datetime.now(timezone.utc)
    order.expected_at = order.placed_at + timedelta(days=order.supplier.lead_time_days)
    db.session.commit()
    return jsonify({"message": "Order approved and marked as placed.", "order": serialize_order(order)})


@api_bp.post("/orders/<int:order_id>/receive")
@login_required
def receive_order(order_id):
    order = accessible_order(order_id)
    if not order:
        return error("Order not found or access denied.", 404, "not_found")
    if order.status not in {"approved", "placed"}:
        return error("Only approved or placed orders can be received.", 409, "invalid_status")
    for line in order.lines:
        outstanding = line.quantity_ordered - line.quantity_received
        if outstanding <= 0:
            continue
        balance = InventoryBalance.query.filter_by(shop_id=order.shop_id, product_id=line.product_id).first()
        if not balance:
            balance = InventoryBalance(shop_id=order.shop_id, product_id=line.product_id, on_hand=0)
            db.session.add(balance)
        balance.on_hand += outstanding
        line.quantity_received += outstanding
        db.session.add(
            StockMovement(
                shop_id=order.shop_id,
                product_id=line.product_id,
                movement_type="receipt",
                quantity=outstanding,
                note=f"Order #{order.id}",
            )
        )
    order.status = "received"
    order.received_at = datetime.now(timezone.utc)
    db.session.commit()
    return jsonify({"message": "Order received and stock balances updated.", "order": serialize_order(order)})


def accessible_order(order_id):
    order = db.session.get(Order, order_id)
    if not order or not owned_shop(order.shop_id):
        return None
    return order


def serialize_inventory(row):
    return {
        "product_id": row.product_id,
        "sku": row.product.sku,
        "name": row.product.name,
        "category": row.product.category,
        "on_hand": row.on_hand,
        "pack_size": row.product.pack_size,
        "unit_cost": float(row.product.unit_cost),
        "stock_value": round(row.on_hand * float(row.product.unit_cost), 2),
        "status": "out" if row.on_hand == 0 else "low" if row.on_hand <= row.product.pack_size else "healthy",
        "updated_at": row.updated_at.isoformat(),
    }


def serialize_recommendation(item):
    return {
        "product_id": item.product_id,
        "sku": item.sku,
        "name": item.name,
        "daily_demand": item.daily_demand,
        "on_hand": item.on_hand,
        "on_order": item.on_order,
        "target_stock": round(item.target_stock, 2),
        "days_cover": None if item.days_cover is None else round(item.days_cover, 1),
        "pack_size": item.pack_size,
        "recommended_quantity": item.recommended_quantity,
        "allocated_quantity": item.allocated_quantity,
        "unit_cost": item.unit_cost,
        "line_cost": round(item.allocated_quantity * item.unit_cost, 2),
        "constraint": item.constrained_reason,
    }


def serialize_order(order):
    return {
        "id": order.id,
        "status": order.status,
        "supplier": order.supplier.name,
        "supplier_id": order.supplier_id,
        "total_cost": float(order.total_cost),
        "delivery_fee": float(order.delivery_fee),
        "created_at": order.created_at.isoformat(),
        "expected_at": order.expected_at.isoformat() if order.expected_at else None,
        "lines": [
            {
                "product_id": line.product_id,
                "product": line.product.name,
                "quantity_ordered": line.quantity_ordered,
                "quantity_received": line.quantity_received,
                "unit_cost": float(line.unit_cost),
            }
            for line in order.lines
        ],
    }


def _int(value):
    try:
        return int(value)
    except (TypeError, ValueError):
        return None
