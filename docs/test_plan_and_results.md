# Test plan and results

## Test levels

| Level | What is checked | Evidence |
|---|---|---|
| Unit | Formula, validation, days of cover, pack rounding, budget/storage allocation | `tests/test_replenishment.py` |
| Integration | Authentication, movement write, demand update, recommendations, order lifecycle | `tests/test_api.py` |
| Interface | Main pages render, mobile layout, validation, loading/empty/error states | `tests/test_pages.py` and browser review |
| Data | Keys, checks, unique constraints, indexes and rollback order | `database/schema.sql` and migration scripts |

## Boundary cases

- zero demand returns no finite days-of-cover value;
- negative demand, stock and budget inputs are rejected;
- pack size must be greater than zero;
- a sale cannot reduce stock below zero;
- an order line must use a full supplier pack;
- draft-only approval and approved-only receipt rules are enforced;
- cash and storage are checked again at approval;
- no-demand recommendations are marked provisional.

## Automated result

The final verification was completed on 21 October 2026 with Python 3.12. The suite covers the calculation model, API, authentication, database rules, role access, page rendering, error handling and end-to-end order flow.

```text
python -m pytest --cov=app --cov=models --cov-report=term-missing
34 passed in 43.10s
Total coverage: 98% (589 statements, 13 not covered)
```

`python -m compileall -q app models tests run.py config.py` also passed. The repeatable impact evaluation completed successfully and reproduced the values shown on the Impact page.

## Browser result

The full working demonstration was reviewed in the local in-app browser with a fresh isolated database.

| Viewport | Pages checked | Result |
|---|---|---|
| 1280 × 720 desktop | Landing, login, dashboard, stock, replenishment, orders and impact | Passed; grids, cards, forms and totals were aligned with no page-level horizontal overflow |
| 768 × 900 tablet | Dashboard, stock, replenishment, orders and impact | Passed; content changed cleanly to two-column or single-column layouts |
| 360 × 740 phone | Landing, login, dashboard, stock, replenishment, orders and impact | Passed; controls remained usable and wide tables scrolled inside their own cards |

The following user actions were completed successfully: invalid and valid login, logout, stock search, no-result search, valid sale, rejected over-sale, receipt capture, zero-budget recommendation, R2 500 recommendation, draft creation, owner approval, full receipt and inventory update. Browser console review showed no warnings or errors.

Two interface defects were found and corrected during the review:

- the phone navigation used a clipped horizontal row; it now uses a clear two-row grid; and
- the product selector kept its old stock quantity after a movement; it now updates immediately with the ledger.

Static asset version parameters were also added so browsers load the corrected CSS and JavaScript instead of using old cached copies. Full evidence and environment notes are recorded in `docs/qa_report.md`. Interface previews in `docs/screenshots/` show the final visual direction.

## Environment note

The complete application flow was tested with the supported SQLite demonstration configuration. Docker is not installed on the test computer, so the MySQL 8 Docker container could not be started here. The MySQL schema, migration, rollback, Docker configuration and MySQL connection path remain included for deployment and further testing.

## Acceptance criteria

- all automated tests pass;
- no unexplained balance mismatch is created by tested flows;
- every allocated quantity is a full pack;
- basket total does not exceed the supplied budget;
- all main pages work at 360 px without clipped controls;
- keyboard focus is visible and forms have labels; and
- empty, loading and error states are present.
