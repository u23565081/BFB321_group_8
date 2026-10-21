#!/usr/bin/env sh
set -eu
: "${MYSQL_HOST:=localhost}"
: "${MYSQL_DATABASE:=spaza_inventory}"
: "${MYSQL_USER:=spaza_user}"
: "${BACKUP_DIR:=./backups}"
mkdir -p "$BACKUP_DIR"
mysqldump -h "$MYSQL_HOST" -u "$MYSQL_USER" -p "$MYSQL_DATABASE" > "$BACKUP_DIR/spaza_$(date +%Y%m%d_%H%M%S).sql"
find "$BACKUP_DIR" -type f -name 'spaza_*.sql' -mtime +14 -delete

