# Amoja Desk - Agent Guidelines

Amoja Desk is a self-hosted trade journaling system with a Flask backend, SQLite
database, JWT API and a web dashboard. The dashboard uses a **v2 sidebar design
with HTMX for SPA-like navigation**.

## Brand & Naming

- **Amoja** is the master personal brand; it means **A1** / top-tier.
- **Amoja Desk** is the application name (display with a space).
- Slugs, package name and database use `amoja-desk`
  (`instance/amoja-desk.db`, `pyproject.toml` name `amoja-desk`).
- Planned modules: **Amoja Replay** (backtesting/replay),
  **Amoja Playbook** (strategies and rule adherence),
  **Amoja Journal** (daily journal), **Amoja Kipimo** (analytics).
- Avoid standalone descriptive trading names; they collide with existing
  products (TraderMate, TradeMate, Edgebook, TradeTally, TradeFrame, EdgeLog,
  TradeLore, Tradeprint, Pipfolio).
- Before a public launch, check trademark classes 9 (software), 36 (finance)
  and 42 (SaaS); existing Amoja marks and a UK software company exist.

See `docs/BRANDING.md` for the full naming record.

## Build & Development

```bash
# Setup (see `make help` for all tasks)
cd ~/PROJECTS/amoja-desk
make init                          # uv sync + apply migrations
# or: uv sync && uv run alembic upgrade head

# Run Flask server
uv run python -m src.app           # or: make run -> http://localhost:5000

# Run all tests
uv run pytest tests/ -v            # or: make test

# Run single test
uv run pytest tests/trades/test_add_trade.py::TestCreateTrade::test_create_trade_success -v

# Run tests by class
uv run pytest tests/trades/test_add_trade.py::TestGetTrades -v

# Run tests by keyword
uv run pytest tests/ -k "create_trade" -v
```

The database is a single SQLite file at `instance/amoja-desk.db`, created by
Alembic. Run `make db-backup` before schema changes. Do not add a database
server or Docker dependency; SQLite is intentional.

## Project Structure

```
src/
  app.py              # Flask app factory
  config.py           # Dev/Test/Prod configs (SQLite by default)
  models.py           # SQLAlchemy models (User, Account, Trade, ...)
  routes/             # API blueprints (auth, trades, metrics, ...)
  services/           # Business logic (TradeService, AnalyticsService)
web/
  templates/          # Jinja2 templates (dashboard, trades, analytics, ...)
  routes/             # Web page routes
  static/             # CSS/JS assets
tests/
  conftest.py         # Fixtures (app, client, sample_trade_data)
  trades/             # Trade API tests
  journal/            # Analytics and broker tests
  auth/               # Authentication tests
  accounts/           # Account API tests
  favorites/          # Favorites API tests
  e2e/                # Playwright end-to-end tests
migrations/
  versions/           # Alembic migrations (SQLite)
plans/
  features/           # Feature/testing plan files (FEA-*.md)
  fixes/              # Bug fix plan files (FIX-*.md)
  debugs/             # Debug investigation plans (DBG-*.md)
```

## HTMX Navigation

The dashboard uses HTMX for SPA-like navigation:

- Sidebar persists across page transitions (no full reloads)
- `hx-get` attributes on sidebar links trigger AJAX requests
- `hx-target="main"` swaps only the content area
- `hx-push-url="true"` updates browser URL
- `withCredentials: true` ensures authentication cookies are sent

### Template Structure

```html
<!-- base.html - Single content block definition -->
{% if not htmx_request %}
<!-- Sidebar, scripts, global handlers -->
{% endif %}
<main>{% block content %}{% endblock %}</main>
{% if not htmx_request %}
<!-- Footer scripts -->
{% endif %}
```

## Code Style

### Imports

- Standard library first, then third-party, then local
- Use absolute imports: `from src.models import Trade`
- Alphabetize within groups

### Naming

- **snake_case** for functions, variables, methods
- **PascalCase** for classes (e.g., `TradeService`, `TradeDirection`)
- **UPPER_SNAKE_CASE** for enum values and constants
- Blueprints named with `_bp` suffix: `trades_bp`

### Types & Documentation

- All public functions require docstrings (one-line `"""Summary."""`)
- Use `Decimal` for monetary values (never float in calculations)
- Convert Decimal to float only in `to_dict()` for JSON serialization

### Error Handling

- Return `(jsonify({"error": "message"}), 400)` for client errors
- Return `jsonify({"error": "Not found"}), 404` for missing resources
- Validate required fields at route level before calling services

### Models

- UUID primary keys: `db.Column(db.String(36), default=lambda: str(uuid.uuid4()))`
- Enum columns: `db.Column(db.Enum(TradeDirection))`
- JSON columns for arrays/objects: `db.Column(db.JSON)`
- Always implement `to_dict()` and `__repr__()`
- Keep schema changes in Alembic migrations, not `db.create_all()`

### Routes

- Use Blueprint pattern: `bp = Blueprint("name", __name__)`
- Services contain business logic, routes handle HTTP
- Accept both JSON (`request.get_json()`) and multipart (`request.form`)
- Swagger docstrings on route functions (YAML after `---`)

### Testing

- Use pytest fixtures defined in `conftest.py`
- Each test function gets a fresh database (function-scoped `app` fixture)
- Test class per endpoint: `TestCreateTrade`, `TestGetTrades`
- Use `client.post()` with `data=json.dumps(payload)`, `content_type="application/json"`
- Tests run on in-memory SQLite; no external services

## API Patterns

### Create resource

```python
@bp.route("/resources", methods=["POST"])
def create_resource():
    data = request.get_json()
    if not data or "required_field" not in data:
        return jsonify({"error": "Missing required_field"}), 400
    resource = Service.create(data)
    return jsonify(resource.to_dict()), 201
```

### List with filters

```python
filters = {k: v for k, v in request.args.items() if v is not None}
pagination = Service.get_all(filters, page, per_page)
return jsonify({"items": [i.to_dict() for i in pagination.items], "total": pagination.total})
```

## Key Business Rules

- P&L = `(price_diff × position_size × point_value) - fees`
- Point value and default fees come from `FavoriteProduct`
- `take_profit` field serves as the exit price for closed trades
- `exit_transactions` array tracks partial exits with qty, exit_price, fees
- Trade status: `CONFIRMED` (open) → `CLOSED` (has take_profit or exit_transactions)
- SQLite runs with foreign keys, WAL mode and a busy timeout enabled
