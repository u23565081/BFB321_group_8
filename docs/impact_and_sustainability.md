# Impact and sustainability analysis

## Evaluation approach

The project includes a deterministic 28-day model comparison. The same simulated demand and supplier lead times are used for both methods. The reactive baseline waits until stock reaches zero and then buys a larger catch-up quantity. StockWise reviews every three days and uses the proposal formula, full packs and a R2 500 review budget.

The evaluation covers 20 non-refrigerated SKUs. It uses a fixed random seed (`321`) so another marker can reproduce the same result with `python scripts/evaluate_impact.py`. These figures are simulation outputs and must not be presented as results from operating shops.

## Before-and-after KPI table

| Measure | Reactive baseline | StockWise rule | Change |
|---|---:|---:|---:|
| Stockout SKU-days | 18 | 5 | 72.2% fewer |
| Emergency collection events | 56 | 0 | 100% fewer in this run |
| Average stock value | R3 507.05 | R3 384.36 | 3.5% lower |
| Availability | 96.8% | 99.1% | 2.3 percentage points higher |
| Recorded cash-limit breaches | 0 | 0 | Target maintained |

The result passes the proposal's O2 target of at least 20% fewer stockout SKU-days. It also passes O3 in this model run because stock value does not rise above the baseline and no budget breach occurs. A field trial may produce a different result.

```text
Stockout SKU-days (lower is better)
Reactive baseline  ██████████████████  18
StockWise rule     █████                5
```

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

