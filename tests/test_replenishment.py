import pytest

from models.replenishment import (
    ReplenishmentItem,
    allocate_with_constraints,
    basket_totals,
    calculate_days_of_cover,
    calculate_inventory_position,
    calculate_recommended_quantity,
    calculate_target_stock,
)


def test_appendix_a_maize_meal_example():
    target = calculate_target_stock(4, lead_time_days=1, review_period_days=3, safety_stock_days=1)
    position = calculate_inventory_position(on_hand=4, on_order=0)
    quantity = calculate_recommended_quantity(target, position, pack_size=6)

    assert target == 20
    assert position == 4
    assert quantity == 18
    assert calculate_days_of_cover(position, 4) == 1


def test_appendix_a_soap_example():
    target = calculate_target_stock(3, 1, 3, 1)
    assert calculate_recommended_quantity(target, inventory_position=6, pack_size=6) == 12


def test_zero_demand_has_no_cover_and_no_order_when_stock_exists():
    assert calculate_days_of_cover(10, 0) is None
    assert calculate_recommended_quantity(0, 10, 6) == 0


def test_invalid_values_are_rejected():
    with pytest.raises(ValueError):
        calculate_target_stock(-1, 1, 3, 1)
    with pytest.raises(ValueError):
        calculate_recommended_quantity(10, 2, 0)


def test_constraint_allocation_uses_full_packs_and_prioritises_low_cover():
    urgent = ReplenishmentItem(
        product_id=1, sku="A", name="Urgent", daily_demand=4, lead_time_days=1,
        review_period_days=3, safety_stock_days=1, pack_size=6, on_hand=2,
        on_order=0, unit_cost=10, storage_units_per_item=1,
    )
    less_urgent = ReplenishmentItem(
        product_id=2, sku="B", name="Less urgent", daily_demand=2, lead_time_days=1,
        review_period_days=3, safety_stock_days=1, pack_size=6, on_hand=8,
        on_order=0, unit_cost=10, storage_units_per_item=1,
    )
    result = allocate_with_constraints([less_urgent, urgent], budget=130, available_storage_units=12, delivery_fee=10)
    by_sku = {item.sku: item for item in result}

    assert by_sku["A"].allocated_quantity == 12
    assert by_sku["B"].allocated_quantity == 0
    assert by_sku["B"].constrained_reason in {"cash limit", "storage limit", "cash and storage limits"}
    assert all(item.allocated_quantity % item.pack_size == 0 for item in result)


def test_storage_only_constraint_and_empty_basket_total():
    item = ReplenishmentItem(
        product_id=1, sku="A", name="Product", daily_demand=5, lead_time_days=1,
        review_period_days=3, safety_stock_days=1, pack_size=6, on_hand=0,
        on_order=0, unit_cost=1, storage_units_per_item=2,
    )
    result = allocate_with_constraints([item], budget=1000, available_storage_units=10)[0]
    assert result.allocated_quantity == 0
    assert result.constrained_reason == "storage limit"
    assert basket_totals([result], delivery_fee=40) == {
        "product_cost": 0,
        "delivery_fee": 0.0,
        "total_cost": 0.0,
    }


def test_negative_allocator_limits_are_rejected():
    with pytest.raises(ValueError):
        allocate_with_constraints([], budget=-1, available_storage_units=1)
