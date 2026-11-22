"""Repeatable 28-day comparison of reactive and StockWise replenishment rules.

This is a model experiment, not evidence collected from operating spaza shops.
It writes the result used in docs/impact_and_sustainability.md, including a
30-seed sensitivity run at two opening-cover levels.
"""

import csv
import json
import math
import random
import sys
from pathlib import Path
from statistics import median

_PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from models.replenishment import ReplenishmentItem, allocate_with_constraints


SEED = 321
DAYS = 28
SKU_COUNT = 20
# Both policies open with the same stock: ceil(daily_mean * OPENING_COVER) units per SKU.
OPENING_COVER = 3.2


def simulate(
    method: str,
    seed: int = SEED,
    opening_cover: float = OPENING_COVER,
    order_log: list | None = None,
) -> dict:
    rng = random.Random(seed)
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
                "stock": math.ceil(daily_mean * opening_cover),
                "pipeline": [],
            }
        )

    stockout_days = 0
    emergency_trips = 0
    emergency_trip_days = 0
    constraint_breaches = 0
    cash_breaches = 0
    storage_breach_days = 0
    pack_violations = 0
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
            restocked_today = False
            for product in products:
                if product["stock"] == 0:
                    emergency_trips += 1
                    restocked_today = True
                    # Reactive buying tends to use a larger "catch-up" quantity after a stockout.
                    quantity = product["pack"] * math.ceil((product["d"] * 9) / product["pack"])
                    if quantity % product["pack"] != 0:
                        pack_violations += 1
                    daily_cost += quantity * product["cost"]
                    product["stock"] += quantity
            if restocked_today:
                emergency_trip_days += 1
            if daily_cost > cash_budget:
                constraint_breaches += 1
            if daily_cost > 2500:
                cash_breaches += 1
        elif day % 3 == 0:
            items = []
            for index, product in enumerate(products):
                on_order = sum(qty for _, qty in product["pipeline"])
                items.append(
                    ReplenishmentItem(
                        product_id=index,
                        sku=f"{index:02d}",
                        name=f"SKU {index + 1}",
                        daily_demand=product["d"],
                        lead_time_days=product["lead"],
                        review_period_days=3,
                        safety_stock_days=1,
                        pack_size=product["pack"],
                        on_hand=product["stock"],
                        on_order=on_order,
                        unit_cost=product["cost"],
                    )
                )
            used_storage = sum(product["stock"] for product in products)
            allocated_items = allocate_with_constraints(
                items,
                budget=cash_budget,
                available_storage_units=max(0, storage_capacity - used_storage),
                delivery_fee=40,
            )
            basket = [
                (products[item.product_id], item.allocated_quantity)
                for item in allocated_items
                if item.allocated_quantity
            ]
            for product, quantity in basket:
                if quantity % product["pack"] != 0:
                    pack_violations += 1
                if order_log is not None:
                    order_log.append((product["pack"], quantity))
                product["pipeline"].append((day + product["lead"], quantity))
            if basket:
                basket_spend = sum(quantity * product["cost"] for product, quantity in basket)
                if basket_spend + 40 > 2500:
                    cash_breaches += 1

        on_hand_units = sum(product["stock"] for product in products)
        if on_hand_units > storage_capacity:
            storage_breach_days += 1
        inventory_values.append(sum(product["stock"] * product["cost"] for product in products))

    availability = 100 * (1 - stockout_days / (DAYS * SKU_COUNT))
    return {
        "stockout_sku_days": stockout_days,
        "emergency_trips": emergency_trips,
        "emergency_collections": emergency_trips,
        "emergency_trip_days": emergency_trip_days,
        "average_stock_value": round(sum(inventory_values) / len(inventory_values), 2),
        "constraint_breaches": constraint_breaches,
        "cash_breaches": cash_breaches,
        "storage_breach_days": storage_breach_days,
        "pack_violations": pack_violations,
        "availability_percent": round(availability, 1),
    }


def _stockout_reduction_percent(baseline: int, observed: int) -> float:
    """Return the percent reduction in stockout SKU-days.

    A negative result means the StockWise run had more stockout SKU-days than
    the reactive run for that seed.
    """
    if baseline == 0:
        return 0.0 if observed == 0 else -100.0
    return (baseline - observed) / baseline * 100.0


def _stockwise_breach_events(result: dict) -> int:
    return (
        result["cash_breaches"]
        + result["storage_breach_days"]
        + result["pack_violations"]
        + result["constraint_breaches"]
    )


def _sensitivity_run(opening_cover: float) -> dict:
    """Repeat the comparison for seeds 1-30 at one opening cover."""
    per_seed = []
    raw_reductions = []
    for seed in range(1, 31):
        reactive = simulate("reactive", seed=seed, opening_cover=opening_cover)
        stockwise = simulate("stockwise", seed=seed, opening_cover=opening_cover)
        reduction = _stockout_reduction_percent(
            reactive["stockout_sku_days"], stockwise["stockout_sku_days"]
        )
        breach_events = _stockwise_breach_events(stockwise)
        raw_reductions.append(reduction)
        per_seed.append(
            {
                "seed": seed,
                "reactive_stockout_sku_days": reactive["stockout_sku_days"],
                "stockwise_stockout_sku_days": stockwise["stockout_sku_days"],
                "reduction_percent": round(reduction, 1),
                "reactive_average_stock_value": reactive["average_stock_value"],
                "stockwise_average_stock_value": stockwise["average_stock_value"],
                "stock_value_at_or_below_baseline": (
                    stockwise["average_stock_value"] <= reactive["average_stock_value"]
                ),
                "stockwise_breach_events": breach_events,
                "stockwise_emergency_collections": stockwise["emergency_collections"],
            }
        )

    def _seed_at(extreme: str) -> tuple[int, float]:
        # Ties keep the lowest seed. Max sorts the seed descending so the
        # smallest seed wins when two reductions are equal.
        if extreme == "min":
            chosen = min(zip(raw_reductions, per_seed), key=lambda item: (item[0], item[1]["seed"]))
        else:
            chosen = max(zip(raw_reductions, per_seed), key=lambda item: (item[0], -item[1]["seed"]))
        return chosen[1]["seed"], chosen[0]

    min_seed, min_reduction = _seed_at("min")
    max_seed, max_reduction = _seed_at("max")
    return {
        "opening_cover": opening_cover,
        "seed_count": len(per_seed),
        "per_seed": per_seed,
        "median_reduction_percent": round(median(raw_reductions), 1),
        "min_reduction_percent": round(min_reduction, 1),
        "min_reduction_seed": min_seed,
        "max_reduction_percent": round(max_reduction, 1),
        "max_reduction_seed": max_seed,
        "seeds_with_at_least_20_percent_reduction": sum(
            reduction >= 20 for reduction in raw_reductions
        ),
        "total_stockout_sku_days": {
            "reactive": sum(row["reactive_stockout_sku_days"] for row in per_seed),
            "stockwise": sum(row["stockwise_stockout_sku_days"] for row in per_seed),
        },
        "seeds_stock_value_at_or_below_baseline": sum(
            row["stock_value_at_or_below_baseline"] for row in per_seed
        ),
        "stockwise_breach_events": sum(row["stockwise_breach_events"] for row in per_seed),
        "stockwise_emergency_collections": sum(
            row["stockwise_emergency_collections"] for row in per_seed
        ),
        "seeds_with_stockwise_breach_or_emergency_collection": sum(
            (row["stockwise_breach_events"] or row["stockwise_emergency_collections"])
            for row in per_seed
        ),
    }


def _write_sensitivity_csv(path: Path, runs: list[dict]) -> None:
    fieldnames = [
        "opening_cover",
        "record",
        "seed",
        "reactive_stockout_sku_days",
        "stockwise_stockout_sku_days",
        "reduction_percent",
        "reactive_average_stock_value",
        "stockwise_average_stock_value",
        "stock_value_at_or_below_baseline",
        "stockwise_breach_events",
        "stockwise_emergency_collections",
        "summary_value",
    ]
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=fieldnames, lineterminator="\r\n")
        writer.writeheader()
        for run in runs:
            cover = run["opening_cover"]
            for row in run["per_seed"]:
                writer.writerow(
                    {
                        "opening_cover": cover,
                        "record": "seed",
                        "seed": row["seed"],
                        "reactive_stockout_sku_days": row["reactive_stockout_sku_days"],
                        "stockwise_stockout_sku_days": row["stockwise_stockout_sku_days"],
                        "reduction_percent": row["reduction_percent"],
                        "reactive_average_stock_value": row["reactive_average_stock_value"],
                        "stockwise_average_stock_value": row["stockwise_average_stock_value"],
                        "stock_value_at_or_below_baseline": row["stock_value_at_or_below_baseline"],
                        "stockwise_breach_events": row["stockwise_breach_events"],
                        "stockwise_emergency_collections": row["stockwise_emergency_collections"],
                        "summary_value": "",
                    }
                )
            totals = run["total_stockout_sku_days"]
            summaries = [
                ("median_reduction_percent", "", "", "", run["median_reduction_percent"], run["median_reduction_percent"]),
                ("min_reduction_percent", run["min_reduction_seed"], "", "", run["min_reduction_percent"], run["min_reduction_percent"]),
                ("max_reduction_percent", run["max_reduction_seed"], "", "", run["max_reduction_percent"], run["max_reduction_percent"]),
                ("seeds_with_at_least_20_percent_reduction", "", "", "", "", run["seeds_with_at_least_20_percent_reduction"]),
                ("total_stockout_sku_days", "", totals["reactive"], totals["stockwise"], "", ""),
                ("seeds_stock_value_at_or_below_baseline", "", "", "", "", run["seeds_stock_value_at_or_below_baseline"]),
                ("stockwise_breach_events", "", "", "", "", run["stockwise_breach_events"]),
                ("stockwise_emergency_collections", "", "", "", "", run["stockwise_emergency_collections"]),
                (
                    "seeds_with_stockwise_breach_or_emergency_collection",
                    "",
                    "",
                    "",
                    "",
                    run["seeds_with_stockwise_breach_or_emergency_collection"],
                ),
            ]
            for record, seed, reactive_days, stockwise_days, reduction, summary in summaries:
                writer.writerow(
                    {
                        "opening_cover": cover,
                        "record": record,
                        "seed": seed,
                        "reactive_stockout_sku_days": reactive_days,
                        "stockwise_stockout_sku_days": stockwise_days,
                        "reduction_percent": reduction,
                        "reactive_average_stock_value": "",
                        "stockwise_average_stock_value": "",
                        "stock_value_at_or_below_baseline": "",
                        "stockwise_breach_events": "",
                        "stockwise_emergency_collections": "",
                        "summary_value": summary,
                    }
                )


def _write_json(path: Path, payload: dict) -> None:
    """Write JSON using CRLF and no trailing newline, matching the committed results file."""
    text = json.dumps(payload, indent=2).replace("\n", "\r\n")
    path.write_bytes(text.encode("utf-8"))


def main():
    project_root = Path(__file__).resolve().parents[1]
    output_dir = project_root / "docs" / "generated"
    output_dir.mkdir(parents=True, exist_ok=True)
    results = {"reactive": simulate("reactive"), "stockwise": simulate("stockwise")}
    results["sensitivity"] = {
        "seeds": "1-30",
        "reduction": "(reactive stockout SKU-days - stockwise stockout SKU-days) / reactive stockout SKU-days * 100, rounded to 1 decimal place",
        "runs": [_sensitivity_run(cover) for cover in (OPENING_COVER, 4.5)],
    }
    _write_json(output_dir / "impact_results.json", results)
    with (output_dir / "impact_results.csv").open("w", newline="", encoding="utf-8") as stream:
        writer = csv.writer(stream)
        writer.writerow(["metric", "reactive_baseline", "stockwise_rule"])
        for metric in results["reactive"]:
            writer.writerow([metric, results["reactive"][metric], results["stockwise"][metric]])
    _write_sensitivity_csv(output_dir / "impact_sensitivity.csv", results["sensitivity"]["runs"])
    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()
