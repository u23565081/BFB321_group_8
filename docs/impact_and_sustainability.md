# Impact and sustainability analysis

## Evaluation approach

The project includes a deterministic 28-day model comparison. The same simulated demand and supplier lead times are used for both methods. Both policies open with the same stock: `ceil(daily_mean * OPENING_COVER)` units per SKU, with `OPENING_COVER = 3.2`. The reactive baseline waits until stock reaches zero and then buys a larger catch-up quantity. StockWise reviews every three days. The simulation builds that basket with `allocate_with_constraints` from `models/replenishment.py`: the proposal formula, full packs, a R40 delivery fee and a R2 500 review budget.

The evaluation covers 20 non-refrigerated SKUs. The headline comparison uses random seed `321`. A sensitivity run repeats both policies for seeds 1–30 at opening cover 3.2, then again at opening cover 4.5. Reproduce the files with `python scripts/evaluate_impact.py`. These figures are simulation outputs and must not be presented as results from operating shops.

The script keeps the previous result keys and adds the counters below. `emergency_collections` is an alias of `emergency_trips`.

- **Emergency trip days:** days on which the reactive rule restocked at least one SKU. Each day is counted once, even if several SKUs are bought that day.
- **Cash breaches:** for the reactive rule, a day whose emergency spend is above R2 500. For StockWise, a review whose basket is not empty and whose product spend plus the R40 delivery fee is above R2 500.
- **Storage breach days:** for both policies, days whose end-of-day units on hand, after that day's ordering, exceed 600. Stock that is still on order is not counted as on hand.
- **Pack violations:** for both policies, orders whose quantity is not a multiple of the SKU's pack size.
- **Constraint breaches:** the existing reactive counter for a day's emergency spend above the R2 500 budget. It is unchanged.

Percent reduction in the sensitivity run is `(reactive stockout SKU-days − StockWise stockout SKU-days) / reactive stockout SKU-days × 100`. Summary percentages are rounded to 1 decimal place. For an even number of seeds, the median is the mean of the two middle raw percentages, then rounded.

## Before-and-after KPI table

Headline run: seed 321, opening cover 3.2. Simulation outputs.

| Measure | Reactive baseline | StockWise rule | Change |
|---|---:|---:|---:|
| Stockout SKU-days | 18 | 10 | 44.4% fewer |
| Emergency collections | 56 | 0 | 100% fewer in this run |
| Emergency trip days | 23 | 0 | 100% fewer in this run |
| Average stock value | R3 507.05 | R3 117.73 | 11.1% lower |
| Availability | 96.8% | 98.2% | 1.4 percentage points higher |
| Cash breaches | 0 | 0 | None in this run |
| Storage breach days | 0 | 0 | None in this run |
| Pack violations | 0 | 0 | None in this run |

*Caption. These KPI figures are simulation outputs from one 28-day run (20 non-refrigerated SKUs, random seed 321, equal opening cover of 3.2 days). `scripts/evaluate_impact.py` writes the same numbers to `docs/generated/impact_results.json` and `docs/generated/impact_results.csv`. They are not measurements from operating spaza shops, and a field trial may differ.*

The seed 321 run passes the proposal's O2 target of at least 20% fewer stockout SKU-days. It also passes O3 in this model run because stock value does not rise above the baseline and no cash, storage or pack breach occurs. The sensitivity run below shows that this is not true for every seed. A field trial may produce a different result.

```text
Stockout SKU-days (lower is better)
Reactive baseline  ██████████████████  18
StockWise rule     ██████████          10
```

## Sensitivity

Per-seed rows and these summaries are written to the `sensitivity` section of `docs/generated/impact_results.json` and to `docs/generated/impact_sensitivity.csv`.

### Opening cover 3.2

| Summary | Result |
|---|---:|
| Seeds with at least a 20% stockout reduction | 27 of 30 |
| Median reduction | 58.0% |
| Minimum reduction | −14.3% (seed 12) |
| Maximum reduction | 84.6% (seed 10) |
| Total stockout SKU-days | 550 reactive, 258 StockWise |
| Seeds with StockWise stock value at or below the baseline | 29 of 30 |
| StockWise breach events | 0 |
| StockWise emergency collections | 0 |

Seed 12 has more stockout SKU-days under StockWise than under the reactive rule. One of the 30 seeds has a higher StockWise average stock value than the reactive baseline. These are simulation outputs.

### Opening cover 4.5

| Summary | Result |
|---|---:|
| Seeds with at least a 20% stockout reduction | 30 of 30 |
| Median reduction | 80.5% |
| Minimum reduction | 35.3% (seed 12) |
| Maximum reduction | 100% (seed 10) |
| Total stockout SKU-days | 555 reactive, 135 StockWise |
| Seeds with StockWise stock value at or below the baseline | 25 of 30 |
| StockWise breach events | 0 |
| StockWise emergency collections | 0 |

At this higher equal opening stock, every seed in the run reaches the 20% stockout target. Stock value is not lower on every seed. These are simulation outputs.

## Expected operational benefit

Earlier ordering can protect the contribution margin that would have been lost when a product is unavailable. Fewer emergency collections can also reduce transport spending and the owner's time away from the shop. The exact rand benefit depends on each product's margin, trip distance and transport cost; these values should be collected during a real trial rather than guessed.

## Sustainability

- **Low equipment requirement:** owners can use their current phones. The system does not require scanners or refrigerated monitoring equipment.
- **Simple maintenance:** product, supplier, pack and lead-time data can be reviewed monthly. A clear seed and backup process supports handover.
- **Privacy:** shop codes can be used in reports and no customer personal information is needed.
- **Human control:** the tool gives a recommendation, but the owner approves the order.
- **Honest uncertainty:** missing demand makes a suggestion provisional rather than giving false confidence.

## Scalability

The schema already separates records by shop and user. New sites, owners and suppliers can be added without changing the model. Composite indexes and API pagination help as data grows. A larger deployment should move logs and backups to managed services, add monitoring dashboards, test performance with representative traffic and introduce stronger role administration.

## Limits

The model does not solve theft, supplier shortages, poor roads, unreliable connectivity or limited business skills. Demand is represented with a short average and does not yet model promotions, pay-day effects or seasonality. Perishables are outside the project scope and would need expiry and waste logic. The simulation must be followed by a small, voluntary shop trial before claiming real impact.
