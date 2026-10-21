# Website quality assurance report

## Summary

StockWise Soweto passed the final functional and visual review on 21 October 2026. All 34 automated tests passed and the tested application/model code reached 98% coverage. The main owner workflow was also completed manually in a browser, from login and stock capture through to replenishment, order approval and delivery receipt.

## Test environment

- Python 3.12 and Flask development server
- fresh isolated SQLite demonstration database
- in-app Chromium browser
- desktop: 1280 × 720
- tablet: 768 × 900
- phone: 360 × 740

Docker was not available on the test computer. This prevented a live MySQL 8 container test, but it did not prevent testing the website, API, database rules or calculation model through the supported SQLite demonstration setup.

## Automated results

| Check | Result |
|---|---|
| Full pytest suite | 34 passed in 43.10 seconds |
| Application and model coverage | 98% |
| Python compilation | Passed |
| Repeatable 28-day impact simulation | Passed |

The suite tests authentication, role access, page protection, inventory and demand updates, API validation, pagination, filters, calculation boundaries, full-pack rounding, cash and storage limits, draft approval, receipt processing, error handlers and seed-data repeatability.

## Functional browser results

| Area | Actions completed | Result |
|---|---|---|
| Authentication | incorrect password, owner login and logout | Passed |
| Dashboard | KPI cards, attention items and recent movements | Passed |
| Stock ledger | search, no-result state, sale, over-sale rejection and receipt | Passed |
| Replenishment | initial state, zero budget and R2 500 basket | Passed |
| Orders | create draft, approve order and receive all stock | Passed |
| Inventory integration | received quantities appeared in the stock ledger | Passed |
| Impact | comparison values and supporting cards rendered | Passed |
| Browser console | warnings and errors checked after the journey | None found |

The R2 500 replenishment test created a basket worth R1 945, including the R55 delivery fee. It contained full supplier packs and stayed below the available cash amount. After receipt, the ordered quantities were added to the stock ledger.

## Visual results

- No tested page produced page-level horizontal overflow.
- Desktop KPI cards had equal widths and matching top and bottom edges.
- Tablet cards, forms and order lines changed cleanly to narrower layouts.
- Phone pages used one-column cards with readable headings and full-width form controls.
- Wide inventory and recommendation tables remained inside their cards and used local horizontal scrolling on small screens.
- Buttons, totals, status labels and empty states remained inside their panels.
- The landing-page phone mock-up stayed centred and within the viewport.

## Defects corrected

1. **Old stock quantity in the product selector.** The ledger updated after a movement, but the selector still showed its earlier on-hand value. The JavaScript now updates the matching option text at the same time. A receipt changed maize meal from 1 to 3 units in both places during the re-test.
2. **Clipped phone navigation.** The five links previously appeared in a horizontal scroller and the Impact link was partly hidden. The phone menu now uses a two-row, three-column grid. All five links are visible without overflow.
3. **Cached interface files.** Version parameters were added to the main CSS and JavaScript links so corrected assets are loaded after an update.

## Final status

The website is ready for demonstration and submission in its current scope. Before a production deployment, run the supplied Docker configuration on a computer with Docker Desktop, use a private production secret key, place the app behind HTTPS and complete the backup/restore check described in the maintenance guide.
