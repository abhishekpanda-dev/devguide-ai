#!/usr/bin/env bash
set -Eeuo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
COMPOSE_FILE="$ROOT_DIR/docker-compose.prod.yml"
ENV_FILE="$ROOT_DIR/.env.production"
COMMAND="${1:-deploy}"
PULL_REQUESTED="${2:-}"

cd "$ROOT_DIR"

require_command() {
  command -v "$1" >/dev/null 2>&1 || {
    echo "Required command is not installed: $1" >&2
    exit 1
  }
}

read_env_value() {
  local key="$1"
  awk -F= -v key="$key" '$1 == key { sub(/^[^=]*=/, ""); sub(/\r$/, ""); print; exit }' "$ENV_FILE"
}

validate_environment() {
  [[ -f "$ENV_FILE" ]] || {
    echo "Missing .env.production. Copy .env.production.example and set production values." >&2
    exit 1
  }

  local required=(
    POSTGRES_DB POSTGRES_USER POSTGRES_PASSWORD
    DEVGUIDE_ENVIRONMENT DEVGUIDE_DATABASE_URL DEVGUIDE_REDIS_URL
    DEVGUIDE_CORS_ALLOWED_ORIGINS DEVGUIDE_AUTH_COOKIE_SECURE DEVGUIDE_AI_PROVIDER
  )
  local key value
  for key in "${required[@]}"; do
    value="$(read_env_value "$key")"
    if [[ -z "$value" || "$value" == *CHANGE_ME* || "$value" == *YOUR_DOMAIN* ]]; then
      echo "Required production variable is missing or still a placeholder: $key" >&2
      exit 1
    fi
  done

  [[ "$(read_env_value DEVGUIDE_ENVIRONMENT)" == "production" ]] || {
    echo "DEVGUIDE_ENVIRONMENT must be production." >&2
    exit 1
  }
  [[ "$(read_env_value DEVGUIDE_AUTH_COOKIE_SECURE)" == "true" ]] || {
    echo "DEVGUIDE_AUTH_COOKIE_SECURE must be true for the HTTPS production deployment." >&2
    exit 1
  }
  if [[ "$(read_env_value DEVGUIDE_AI_PROVIDER)" == "claude" ]] \
    && [[ -z "$(read_env_value DEVGUIDE_ANTHROPIC_API_KEY)" ]]; then
    echo "DEVGUIDE_ANTHROPIC_API_KEY is required when the Claude provider is selected." >&2
    exit 1
  fi
}

compose() {
  docker compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE" "$@"
}

wait_for_health() {
  local service="$1" attempts="${2:-60}" container health
  echo "Waiting for $service to become healthy..."
  for ((i = 1; i <= attempts; i++)); do
    container="$(compose ps -q "$service")"
    if [[ -n "$container" ]]; then
      health="$(docker inspect --format '{{if .State.Health}}{{.State.Health.Status}}{{else}}{{.State.Status}}{{end}}' "$container")"
      [[ "$health" == "healthy" ]] && return 0
      [[ "$health" == "unhealthy" || "$health" == "exited" ]] && break
    fi
    sleep 2
  done
  echo "$service did not become healthy." >&2
  return 1
}

show_failure_logs() {
  local exit_code=$?
  echo "Deployment failed. Recent service logs follow." >&2
  compose logs --tail=100 postgres redis api worker web >&2 || true
  exit "$exit_code"
}

require_command docker
docker compose version >/dev/null 2>&1 || {
  echo "Docker Compose v2 is required." >&2
  exit 1
}

case "$COMMAND" in
  deploy)
    validate_environment
    trap show_failure_logs ERR
    if [[ "$PULL_REQUESTED" == "--pull" ]]; then
      require_command git
      git pull --ff-only
    elif [[ -n "$PULL_REQUESTED" ]]; then
      echo "Unknown deploy option: $PULL_REQUESTED (supported: --pull)" >&2
      exit 2
    fi
    compose config --quiet
    compose build api web
    compose up -d postgres redis
    wait_for_health postgres
    wait_for_health redis
    echo "Applying database migrations once..."
    compose run --rm --no-deps api python -m alembic upgrade head
    compose up -d api worker web
    wait_for_health api
    wait_for_health web
    trap - ERR
    compose ps
    ;;
  status)
    validate_environment
    compose ps
    ;;
  logs)
    validate_environment
    compose logs --tail=200 -f api worker web
    ;;
  restart)
    validate_environment
    compose restart api worker web
    compose ps
    ;;
  stop)
    validate_environment
    compose stop
    compose ps
    ;;
  *)
    echo "Usage: $0 {deploy [--pull]|status|logs|restart|stop}" >&2
    exit 2
    ;;
esac
