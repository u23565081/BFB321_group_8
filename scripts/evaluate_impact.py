"""Repeatable 28-day comparison of reactive and StockWise replenishment rules.

This is a model experiment, not evidence collected from operating spaza shops.
It writes the result used in docs/impact_and_sustainability.md.
"""

import csv
import json
import math
import random
from pathlib import Path


SEED = 321
DAYS = 28
SKU_COUNT = 20


def simulate(method: str) -> dict:
    rng = random.Random(SEED)
    products = []
    for index in range(SKU_COUNT):
        # A small-shop demand profile: most SKUs sell below two units per day.
        daily_mean = 0.6 + (index % 6) * 0.22
        pack = [4, 6, 8, 10, 12][index % 5]
        cost = 7.5 + (index % 8) * 5.5
        lead = 1 + index % 2
        products.append(
            {
                "d": daily_mean,
                "pack": pack,
                "cost": cost,
                "lead": lead,
                "stock": math.ceil(daily_mean * (3.2 if method == "reactive" else 4.5)),
                "pipeline": [],
            }
        )

    stockout_days = 0
    emergency_trips = 0
    constraint_breaches = 0
    inventory_values = []
    cash_budget = 2500.0
    storage_capacity = 600

    for day in range(DAYS):
        for product in products:
            arriving = sum(qty for due, qty in product["pipeline"] if due == day)
            product["stock"] += arriving
            product["pipeline"] = [(due, qty) for due, qty in product["pipeline"] if due > day]

        for product in products:
            demand = max(0, round(rng.gauss(product["d"], 0.85)))
            sold = min(product["stock"], demand)
            product["stock"] -= sold
            if sold < demand:
                stockout_days += 1

        if method == "reactive":
            daily_cost = 0.0
            for product in products:
                if product["stock"] == 0:
                    emergency_trips += 1
                    # Reactive buying tends to use a larger "catch-up" quantity after a stockout.
                    quantity = product["pack"] * math.ceil((product["d"] * 9) / product["pack"])
                    daily_cost += quantity * product["cost"]
                    product["stock"] += quantity
            if daily_cost > cash_budget:
                constraint_breaches += 1
        elif day % 3 == 0:
            remaining_cash = cash_budget - 40
            used_storage = sum(product["stock"] for product in products)
            remaining_storage = storage_capacity - used_storage
            basket = []
            for product in sorted(products, key=lambda item: item["stock"] / item["d"]):
                on_order = sum(qty for _, qty in product["pipeline"])
                target = product["d"] * (product["lead"] + 3 + 1)
                gap = max(0, target - product["stock"] - on_order)
                quantity = product["pack"] * math.ceil(gap / product["pack"]) if gap else 0
                pack_cost = product["pack"] * product["cost"]
                allocated = 0
                while allocated < quantity and remaining_cash >= pack_cost and remaining_storage >= product["pack"]:
                    allocated += product["pack"]
                    remaining_cash -= pack_cost
                    remaining_storage -= product["pack"]
                if allocated:
                    basket.append((product, allocated))
            for product, quantity in basket:
                product["pipeline"].append((day + product["lead"], quantity))

        inventory_values.append(sum(product["stock"] * product["cost"] for product in products))

    availability = 100 * (1 - stockout_days / (DAYS * SKU_COUNT))
    return {
        "stockout_sku_days": stockout_days,
        "emergency_trips": emergency_trips,
        "average_stock_value": round(sum(inventory_values) / len(inventory_values), 2),
        "constraint_breaches": constraint_breaches,
        "availability_percent": round(availability, 1),
    }


def main():
    project_root = Path(__file__).resolve().parents[1]
    output_dir = project_root / "docs" / "generated"
    output_dir.mkdir(parents=True, exist_ok=True)
    results = {"reactive": simulate("reactive"), "stockwise": simulate("stockwise")}
    (output_dir / "impact_results.json").write_text(json.dumps(results, indent=2), encoding="utf-8")
    with (output_dir / "impact_results.csv").open("w", newline="", encoding="utf-8") as stream:
        writer = csv.writer(stream)
        writer.writerow(["metric", "reactive_baseline", "stockwise_rule"])
        for metric in results["reactive"]:
            writer.writerow([metric, results["reactive"][metric], results["stockwise"][metric]])
    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()
