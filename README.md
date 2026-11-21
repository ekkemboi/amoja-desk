# Amoja Desk

**The A1 trading journal.**

A self-hosted trade journal. Flask and SQLite power the API, and a
server-rendered web dashboard (Jinja2 + HTMX + Tailwind + Chart.js) covers
metrics, trade history, accounts, favorites and analytics.

## Features

- Email/password and Google sign-in with JWT access and refresh tokens
- Manual trade entry with long/short direction, entry and exit prices, stop
  loss, take profit, size, fees, notes, tags and screenshots
- Partial exits with per-exit quantity, price and fees
- Automatic P&L using per-symbol point value and default fees from favorites
- Multiple accounts with balances, per-account filtering and bulk assignment
- Dashboard metrics: win rate, total P&L, profit factor, averages, equity curve
- Analytics: time-of-day and session performance, calendar, Monte Carlo,
  drawdown, tag performance and risk metrics
- Broker connection records (live sync is not implemented)

## Requirements

- Python 3.12+
- [uv](https://docs.astral.sh/uv/)

No Docker or database server is required.

## Development

```sh
make init     # uv sync + create instance/amoja-desk.db
make dev     # http://localhost:5000
```

`make help` lists all tasks. Equivalent commands:

```sh
uv sync
uv run alembic upgrade head
uv run python -m src.app
```

API docs are served at http://localhost:5000/api/docs.

## Database

The SQLite database lives at `instance/amoja-desk.db` and is created by the
Alembic migrations. Override the location with `DATABASE_URL` if needed.

```sh
make migrate     # apply pending migrations
make db-backup   # consistent copy in backups/
make db-shell    # sqlite3 prompt
make db-reset CONFIRM=yes   # delete and recreate (destructive)
```

SQLite runs with WAL mode, foreign keys and a busy timeout enabled. It is a good
fit for a single user or a small number of concurrent readers. Writes are
serialized, so avoid running many app workers against the same file.

## Tests

```sh
make test     # unit/API tests on in-memory SQLite
make test-e2e # Playwright tests; run `make run` in another terminal first
```

## Production

Run a single Gunicorn worker against the SQLite file and put a reverse proxy or
tunnel in front if the app must be reachable remotely:

```sh
SECRET_KEY=... JWT_SECRET_KEY=... \
  uv run gunicorn --bind 0.0.0.0:5000 --workers 1 --timeout 120 "src.app:create_app()"
```

Back up `instance/amoja-desk.db` regularly (`make db-backup`). For multi-user or
multi-writer workloads, migrate the same schema to PostgreSQL and add a
PostgreSQL driver; SQLite is intentionally single-writer.

## License

Amoja Desk is open-source software licensed under the [MIT License](LICENSE).
Third-party dependencies remain under their respective licenses.
