# Maintenance and handover guide

## Daily owner tasks

1. Record sales, receipts, losses and returns as they happen, or enter a daily total before closing.
2. Review low-stock suggestions once a day.
3. Confirm the cash figure before creating a basket.
4. Approve each order manually.
5. Receive the order when it arrives so the stock ledger is updated.

## Weekly checks

- Compare five randomly selected ledger balances with a physical count.
- Review late deliveries and update supplier lead times if a pattern develops.
- Check the application log for repeated validation or server errors.

## Monthly checks

- Confirm product costs and pack sizes with suppliers.
- Disable products that are no longer stocked; do not delete history.
- Test a database restore using the newest backup.
- Review user access and remove accounts that no longer need access.

## Backup and restore

Run `scripts/backup_mysql.sh` daily through cron or the hosting scheduler. Keep encrypted backups for 14 days and store them separately from the live database. Restore into a new database first, count key tables, then switch the application only after verification.

## Troubleshooting

| Problem | Check | Action |
|---|---|---|
| App cannot connect to MySQL | `DATABASE_URL`, database health, firewall | Correct the environment value and restart the web service |
| Suggestions are zero | Recent sales and current stock | Capture missing demand; treat the result as provisional |
| Order cannot be approved | Cash budget, storage capacity, status | Reduce the basket or correct the shop settings |
| Stock does not match a count | Recent movements and receipts | Enter a labelled count adjustment and investigate the cause |
| Server error | `logs/app.log` | Record time and action, preserve the log and roll back the failed session |

## Change control

Make schema changes through a numbered migration with a tested rollback. Run all tests before deployment. Back up the database first. Keep `.env` files and passwords out of source control. For a public system, use HTTPS and change both demo passwords immediately.

