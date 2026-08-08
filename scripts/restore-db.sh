#!/usr/bin/env bash
set -Eeuo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENV_FILE="$ROOT_DIR/.env.production"
COMPOSE_FILE="$ROOT_DIR/docker-compose.prod.yml"
BACKUP_PATH="${1:-}"
CONFIRM="${2:-}"

[[ -n "$BACKUP_PATH" ]] || { echo "Usage: $0 BACKUP_FILE [--yes]" >&2; exit 2; }
[[ -f "$BACKUP_PATH" ]] || { echo "Backup file does not exist: $BACKUP_PATH" >&2; exit 1; }
[[ -s "$BACKUP_PATH" ]] || { echo "Backup file is empty: $BACKUP_PATH" >&2; exit 1; }
[[ -f "$ENV_FILE" ]] || { echo "Missing .env.production." >&2; exit 1; }
command -v docker >/dev/null 2>&1 || { echo "Docker is required." >&2; exit 1; }
docker compose version >/dev/null 2>&1 || { echo "Docker Compose v2 is required." >&2; exit 1; }

if [[ "$CONFIRM" != "--yes" ]]; then
  echo "WARNING: this restore replaces data in the production database."
  read -r -p "Type RESTORE to continue: " answer
  [[ "$answer" == "RESTORE" ]] || { echo "Restore cancelled."; exit 1; }
fi

compose=(docker compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE")
restart_application=false
cleanup() {
  if [[ "$restart_application" == true ]]; then
    "${compose[@]}" up -d api worker web >/dev/null || true
  fi
}
trap cleanup EXIT

"${compose[@]}" stop api worker
restart_application=true
"${compose[@]}" exec -T postgres sh -c \
  'PGPASSWORD="$POSTGRES_PASSWORD" pg_restore --clean --if-exists --exit-on-error --no-owner --no-acl --username="$POSTGRES_USER" --dbname="$POSTGRES_DB"' \
  <"$BACKUP_PATH"
"${compose[@]}" up -d api worker web
restart_application=false
trap - EXIT
echo "Database restore completed. Verify application health and logs immediately."
