#!/usr/bin/env bash
set -Eeuo pipefail
umask 077

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENV_FILE="$ROOT_DIR/.env.production"
COMPOSE_FILE="$ROOT_DIR/docker-compose.prod.yml"
BACKUP_DIR="$ROOT_DIR/backups"

[[ -f "$ENV_FILE" ]] || { echo "Missing .env.production." >&2; exit 1; }
command -v docker >/dev/null 2>&1 || { echo "Docker is required." >&2; exit 1; }
docker compose version >/dev/null 2>&1 || { echo "Docker Compose v2 is required." >&2; exit 1; }

mkdir -p "$BACKUP_DIR"
backup="$BACKUP_DIR/devguide-$(date -u +%Y%m%dT%H%M%SZ).dump"
compose=(docker compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE")

"${compose[@]}" exec -T postgres sh -c \
  'PGPASSWORD="$POSTGRES_PASSWORD" pg_dump --format=custom --no-owner --no-acl --username="$POSTGRES_USER" --dbname="$POSTGRES_DB"' \
  >"$backup"

[[ -s "$backup" ]] || { rm -f "$backup"; echo "Backup failed or produced an empty file." >&2; exit 1; }
echo "Database backup created: ${backup#$ROOT_DIR/}"
