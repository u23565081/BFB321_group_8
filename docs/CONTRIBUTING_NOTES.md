# Contribution notes

These notes help markers read the repository. They do not change how the Flask application, API, database, or replenishment model runs.

## Accounts

Confirmed GitHub usernames are listed in the README:

- Andrew Holdt (`u23565081`) — `u23565081`
- David Plumb (`u23526263`) — `u23526263-hash`
- Austin Ferraz (`u23627132`) — `(GitHub TBD)`
- David de Villiers (`u23570972`) — `(GitHub TBD)`

Replace `(GitHub TBD)` only when that member confirms the account. Do not invent a username.

## What the history supports

Commits by `u23565081` include the initial project upload and the Windows run documentation (`README.md` and `scripts/start.ps1`).

Documentation commits by `u23526263-hash` add the GitHub username column, the high-level task allocation, checklist clarifications, and this file. They do not change routes, schema, model formulas, or tests.

Austin Ferraz and David de Villiers are group members. Their task rows stay `(TBD / shared)` until they record their own work.

## Evidence that must stay labelled

- The KPI table in `docs/impact_and_sustainability.md` and the files in `docs/generated/` are simulation outputs. Reproduce them with `python scripts/evaluate_impact.py` (random seed `321`). Do not present them as results from operating shops.
- `docs/usability_test_results.md` records a scripted device walkthrough and the protocol for a later field session. It is not a completed study of five independent owners.
- `SUBMISSION_CHECKLIST.md` leaves representative-only steps unchecked on purpose. A person ticks those at submission time.

## Tests

With the development requirements installed:

```sh
python -m pytest
```

`config.py` points the `testing` configuration at an in-memory SQLite database. Docker and the MySQL scripts are unchanged and remain the way to run against MySQL 8.
