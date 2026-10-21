"""Framework-independent replenishment calculations.

The formula follows Appendix A of the Group 8 proposal:
S = d(L + R + b), IP = OH + OO, and q is rounded up to a full supplier pack.
"""

from dataclasses import dataclass, replace
from math import ceil
from typing import Iterable


@dataclass(frozen=True)
class ReplenishmentItem:
    """Input and result for one SKU in the replenishment basket."""

    product_id: int
    sku: str
    name: str
    daily_demand: float
    lead_time_days: int
    review_period_days: int
    safety_stock_days: int
    pack_size: int
    on_hand: int
    on_order: int
    unit_cost: float
    storage_units_per_item: float = 1.0
    target_stock: float = 0.0
    inventory_position: int = 0
    days_cover: float | None = None
    recommended_quantity: int = 0
    allocated_quantity: int = 0
    constrained_reason: str | None = None


def calculate_target_stock(
    daily_demand: float,
    lead_time_days: int,
    review_period_days: int,
    safety_stock_days: int,
) -> float:
    """Return stock required until the next safe delivery.

    Assumes daily demand is non-negative and that lead time, review period and
    safety-stock allowance are measured in whole days.
    """
    _validate_non_negative(daily_demand=daily_demand)
    _validate_non_negative(
        lead_time_days=lead_time_days,
        review_period_days=review_period_days,
        safety_stock_days=safety_stock_days,
    )
    return daily_demand * (lead_time_days + review_period_days + safety_stock_days)


def calculate_inventory_position(on_hand: int, on_order: int) -> int:
    """Return available plus confirmed incoming stock."""
    _validate_non_negative(on_hand=on_hand, on_order=on_order)
    return on_hand + on_order


def calculate_recommended_quantity(
    target_stock: float, inventory_position: int, pack_size: int
) -> int:
    """Return a non-negative order quantity rounded up to a full pack."""
    _validate_non_negative(target_stock=target_stock, inventory_position=inventory_position)
    if pack_size <= 0:
        raise ValueError("pack_size must be greater than zero")
    gap = max(0.0, target_stock - inventory_position)
    return pack_size * ceil(gap / pack_size) if gap else 0


def calculate_days_of_cover(inventory_position: int, daily_demand: float) -> float | None:
    """Return days of stock remaining, or ``None`` when demand is unknown/zero."""
    _validate_non_negative(inventory_position=inventory_position, daily_demand=daily_demand)
    if daily_demand == 0:
        return None
    return inventory_position / daily_demand


def build_recommendation(item: ReplenishmentItem) -> ReplenishmentItem:
    """Calculate target, inventory position, cover and unconstrained quantity."""
    target = calculate_target_stock(
        item.daily_demand,
        item.lead_time_days,
        item.review_period_days,
        item.safety_stock_days,
    )
    position = calculate_inventory_position(item.on_hand, item.on_order)
    quantity = calculate_recommended_quantity(target, position, item.pack_size)
    return replace(
        item,
        target_stock=target,
        inventory_position=position,
        days_cover=calculate_days_of_cover(position, item.daily_demand),
        recommended_quantity=quantity,
    )


def allocate_with_constraints(
    items: Iterable[ReplenishmentItem],
    budget: float,
    available_storage_units: float,
    delivery_fee: float = 0.0,
) -> list[ReplenishmentItem]:
    """Allocate full packs to urgent SKUs within cash and storage limits.

    SKUs with the fewest days of cover receive priority. The delivery fee is
    reserved once, before products are allocated. No partial packs are used.
    """
    _validate_non_negative(
        budget=budget,
        available_storage_units=available_storage_units,
        delivery_fee=delivery_fee,
    )
    calculated = [build_recommendation(item) for item in items]
    remaining_cash = max(0.0, budget - delivery_fee)
    remaining_storage = available_storage_units
    results: dict[int, ReplenishmentItem] = {}

    def urgency(item: ReplenishmentItem):
        return float("inf") if item.days_cover is None else item.days_cover

    for item in sorted(calculated, key=lambda candidate: (urgency(candidate), candidate.sku)):
        if item.recommended_quantity == 0:
            results[item.product_id] = replace(item, allocated_quantity=0)
            continue
        pack_cost = item.pack_size * item.unit_cost
        pack_storage = item.pack_size * item.storage_units_per_item
        allocated = 0
        while (
            allocated < item.recommended_quantity
            and remaining_cash + 1e-9 >= pack_cost
            and remaining_storage + 1e-9 >= pack_storage
        ):
            allocated += item.pack_size
            remaining_cash -= pack_cost
            remaining_storage -= pack_storage
        reason = None
        if allocated < item.recommended_quantity:
            can_afford = remaining_cash + 1e-9 >= pack_cost
            has_space = remaining_storage + 1e-9 >= pack_storage
            if not can_afford and not has_space:
                reason = "cash and storage limits"
            elif not can_afford:
                reason = "cash limit"
            else:
                reason = "storage limit"
        results[item.product_id] = replace(
            item, allocated_quantity=allocated, constrained_reason=reason
        )

    return [results[item.product_id] for item in calculated]


def basket_totals(items: Iterable[ReplenishmentItem], delivery_fee: float = 0.0) -> dict:
    """Return product, delivery and total cost for allocated quantities."""
    product_cost = sum(item.allocated_quantity * item.unit_cost for item in items)
    applied_fee = delivery_fee if product_cost > 0 else 0.0
    return {
        "product_cost": round(product_cost, 2),
        "delivery_fee": round(applied_fee, 2),
        "total_cost": round(product_cost + applied_fee, 2),
    }


def _validate_non_negative(**values):
    for name, value in values.items():
        if value < 0:
            raise ValueError(f"{name} cannot be negative")

