# Production Docker deployment

This bundle deploys DevGuide AI to a single Linux VPS with Docker Compose. Nginx is the only
publicly exposed service. PostgreSQL, Redis, FastAPI, and the ARQ worker remain on an internal
Docker network.

## 1. VPS requirements

- A maintained 64-bit Linux distribution with at least 2 CPU cores, 4 GB RAM, and adequate SSD
  space for repositories, PostgreSQL, images, logs, and backups.
- Docker Engine with the Compose v2 plugin, Git, Bash, and outbound HTTPS/DNS access.
- A non-root deployment user in the `docker` group. Protect Docker access as root-equivalent.
- A supported public domain and a separate tested backup destination.

## 2. DNS and firewall

Create an `A`/`AAAA` record for the domain pointing to the VPS. Allow SSH only from trusted source
ranges when practical, and expose TCP 80 and 443. Do not expose PostgreSQL 5432, Redis 6379, or API
8015 in the host firewall or cloud security group.

## 3. Install Docker

Install Docker Engine and Compose from Docker's repository for the VPS distribution. Verify:

```bash
docker version
docker compose version
```

## 4. Clone and configure

```bash
git clone https://github.com/YOUR_ORG/devguide-ai.git
cd devguide-ai
cp .env.production.example .env.production
chmod 600 .env.production
chmod +x scripts/*.sh
```

Edit `.env.production` without committing it. Replace every placeholder. Use a long random
PostgreSQL password and URL-encode that password in `DEVGUIDE_DATABASE_URL`. Set the production
domain in the JSON-formatted CORS origin. Keep `DEVGUIDE_AUTH_COOKIE_SECURE=true` behind HTTPS.

For Claude, set `DEVGUIDE_AI_PROVIDER=claude`, an approved model, and the Anthropic key. To operate
explicitly without Claude, select `mock`; the application never silently falls back to mock.

## 5. Deploy

```bash
./scripts/deploy.sh deploy
```

The script validates configuration, builds images, starts PostgreSQL/Redis, waits for health,
executes `python -m alembic upgrade head` once, then starts API, worker, and Nginx. It never removes
volumes. It does not pull Git changes unless explicitly requested:

```bash
./scripts/deploy.sh deploy --pull
```

## 6. Status and logs

```bash
./scripts/deploy.sh status
./scripts/deploy.sh logs
docker compose --env-file .env.production -f docker-compose.prod.yml logs --tail=200 postgres redis
```

Public checks after HTTPS is configured:

```text
https://YOUR_DOMAIN/
https://YOUR_DOMAIN/api/v1/health
https://YOUR_DOMAIN/api/v1/ready
```

Perform the authenticated submission-to-dashboard demo after every production release.

## 7. Migrations

Normal deployment runs migrations once before API/worker startup. For an explicit maintenance run:

```bash
docker compose --env-file .env.production -f docker-compose.prod.yml run --rm --no-deps api python -m alembic upgrade head
```

Never run migrations concurrently from API or worker replicas. Review migration compatibility and
back up the database before schema changes.

## 8. Backups

```bash
./scripts/backup-db.sh
```

Backups use PostgreSQL custom format, have UTC timestamps, restrictive permissions, and are stored
under ignored `backups/`. Copy them promptly to encrypted off-host storage and test restoration on
a non-production database. Local files alone are not a backup strategy.

## 9. Restore

Restore replaces production data and temporarily stops API/worker writes:

```bash
./scripts/restore-db.sh backups/devguide-YYYYMMDDTHHMMSSZ.dump
```

The script requires typing `RESTORE`. Automation may use `--yes` only with an explicit operator
decision:

```bash
./scripts/restore-db.sh backups/devguide-YYYYMMDDTHHMMSSZ.dump --yes
```

Verify readiness, logs, authentication, analysis ownership, and representative records afterward.

## 10. Upgrade and rollback

Before upgrading, create and copy an off-host backup, review migrations, and note the current Git
revision/image tag. Then use `deploy --pull` or check out an explicitly reviewed revision and run
`deploy`.

For application rollback, check out the previous compatible revision, set a distinct
`DEVGUIDE_IMAGE_TAG`, and redeploy. Database rollback is not automatic: only restore a known-good
backup after assessing migration compatibility and accepting data loss since that backup.

## 11. HTTPS

The bundled Nginx listens on HTTP port 80. Terminate TLS with a maintained host proxy such as
Certbot-managed Nginx, Caddy, or a cloud load balancer, forwarding to this port. Redirect HTTP to
HTTPS at that layer and forward the original scheme. Do not expose this deployment publicly with
secure cookies enabled until HTTPS works. If certificates are mounted into this container later,
add a reviewed 443 server block and certificate renewal process; never commit private keys.

## 12. Operations and security

- Keep Docker, base images, and the VPS patched.
- Restrict SSH, disable password login where feasible, and protect Docker-group membership.
- Monitor disk, memory, queue depth, database health, worker failures, and certificate expiry.
- Rotate database and Anthropic credentials through `.env.production` and redeploy.
- Never mount the Docker socket or run containers privileged.
- Do not execute code from analyzed repositories; the worker only performs bounded static analysis.

## 13. Common failures

- **Configuration rejected:** replace all placeholders; ensure passwords match and the database URL
  contains a URL-encoded password.
- **PostgreSQL/Redis unhealthy:** inspect service logs, volume permissions, disk capacity, and memory.
- **Migration failure:** keep API/worker stopped, inspect the migration error, and do not retry
  destructive operations blindly. Restore only after a reviewed decision.
- **API unhealthy:** check `/api/v1/health`, `/ready`, API logs, database URL, Redis URL, and resource
  pressure.
- **Login cookie missing:** verify same-origin `/api`, HTTPS, forwarded scheme, domain, and
  `DEVGUIDE_AUTH_COOKIE_SECURE=true`.
- **Frontend route 404:** confirm requests reach the bundled Nginx configuration and SPA fallback.
- **Claude error:** verify explicit provider selection, key availability, model access, outbound
  HTTPS, and provider limits without printing the key.
- **Disk full:** inspect Docker usage and backup retention. Never delete production volumes as an
  ad-hoc cleanup step.
