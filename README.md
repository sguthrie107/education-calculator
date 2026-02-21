# 529 Education Calculator

Standalone 529 education savings projection dashboard. Tracks account growth from child age 0 to 20, supports up to 3 children with 3-year offsets, and provides actual-vs-projected performance comparison.

Built to mirror the architecture, dashboard behavior, and execution style of the sibling `retirement-calculator` project.

## Quick Start

```powershell
cd education-calculator
.\start_web.ps1
# Opens at http://localhost:8001
```

Or manually:

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8001
```

## Architecture

```
education-calculator/
├── app/
│   ├── main.py              # FastAPI app factory
│   ├── config.py            # Env config & 529 defaults
│   ├── database.py          # SQLAlchemy engine + session + seeding
│   ├── models.py            # ORM: Child, Account529, ActualBalance
│   ├── schemas.py           # Pydantic request/response models
│   ├── routes/
│   │   ├── dashboard.py     # GET / — serves Jinja2 dashboard
│   │   ├── projections.py   # GET /api/comparison/{child}, /api/comparison-all
│   │   └── balances.py      # CRUD /api/balances/{child}
│   ├── services/
│   │   ├── projection.py    # Wraps lib/calculator for web layer
│   │   └── comparison.py    # Merges projected + actual + deltas
│   ├── static/
│   │   ├── css/dashboard.css
│   │   ├── js/chart.js
│   │   ├── fonts/
│   │   └── favicon.ico
│   └── templates/
│       ├── base.html
│       └── dashboard.html
├── lib/
│   └── calculator.py        # Pure financial engine — no DB/HTTP/UI
├── data/
│   └── children.json        # Child configs (birth years, allocations)
├── requirements.txt
├── pyproject.toml
└── start_web.ps1
```

### Layer Separation

| Layer | Purpose | Files |
|-------|---------|-------|
| **Calculation Engine** | Pure math: phase allocation, blended returns, monthly compounding | `lib/calculator.py` |
| **Data Storage** | SQLAlchemy ORM + SQLite, JSON seed data | `app/models.py`, `app/database.py`, `data/children.json` |
| **Service Layer** | Bridges engine → web | `app/services/projection.py`, `app/services/comparison.py` |
| **UI / Dashboard** | FastAPI + Jinja2 + Chart.js | `app/routes/`, `app/templates/`, `app/static/` |

## Investment Phases

Each 529 account uses age-based allocation switching:

| Phase | Ages | US Stock | Intl Stock | US Bond | Blended Return |
|-------|------|----------|------------|---------|----------------|
| Aggressive Growth | 0–12 | 70% VTSAX | 30% VTIAX | — | ~9.4% |
| Moderate Growth | 13–17 | 60% VTSAX | 20% VTIAX | 20% VBTLX | ~8.4% |
| Conservative | 18–20 | 40% VTSAX | 20% VTIAX | 40% VBTLX | ~7.2% |

## Simulation Loop

For each child, for each year (age 0 → 20):

1. Determine phase by age → select allocation
2. Compute blended annual return from weighted fund returns
3. Convert to monthly rate: `(1 + annual)^(1/12) - 1`
4. For each of 12 months: `balance = balance × (1 + monthly_rate) + $200`
5. Record yearly snapshot: beginning balance, contributions, growth, ending balance

Initial investment of $2,500 is deposited at age 0 before month 1.

## Children Configuration

Defined in `data/children.json`:

- **Child 1**: Born 2026 (projects 2026–2046)
- **Child 2**: Born 2029 (projects 2029–2049)  
- **Child 3**: Born 2032 (projects 2032–2052)

Each child: $2,500 initial investment + $200/month contributions.

## Dashboard Features

- **Multi-child chart**: All 3 children plotted with distinct colors
- **Single child view**: Dropdown to isolate one child
- **Phase allocation cards**: Visual breakdown of each investment phase
- **Performance comparison table**: Year-by-year projected vs actual with delta %
- **Actual balance entry**: Modal form to record yearly snapshots
- **Edit/delete**: Inline actions on recorded balances

## Design

- **Primary**: Burnt Red (#8B2500)
- **Background**: Off White (#FAF8F5)
- **Accents**: Gold trim (#C8A44D)
- **Font**: Montserrat
- **Favicon**: Shared husky image from retirement-calculator

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/` | Dashboard HTML |
| GET | `/api/comparison/{child_name}` | Single child projection + actuals |
| GET | `/api/comparison-all` | All children projections |
| POST | `/api/balances/{child_name}` | Create actual balance |
| PUT | `/api/balances/{balance_id}` | Update balance |
| DELETE | `/api/balances/{balance_id}` | Delete balance |

## Example Projection Output (Child 1, Age 20)

```json
{
  "child_name": "Child 1",
  "birth_year": 2026,
  "projected": [
    {"year": 2026, "age": 0, "balance": 5236.72, "phase": "Aggressive Growth (Age 0-12)", "contributions_ytd": 4900.00},
    {"year": 2038, "age": 12, "balance": 66997.20, "phase": "Aggressive Growth (Age 0-12)", "contributions_ytd": 33700.00},
    {"year": 2039, "age": 13, "balance": 75116.02, "phase": "Moderate Growth (Age 13-17)", "contributions_ytd": 36100.00},
    {"year": 2043, "age": 17, "balance": 115008.44, "phase": "Moderate Growth (Age 13-17)", "contributions_ytd": 45700.00},
    {"year": 2044, "age": 18, "balance": 125767.25, "phase": "Conservative (Age 18+)", "contributions_ytd": 48100.00},
    {"year": 2046, "age": 20, "balance": 149664.55, "phase": "Conservative (Age 18+)", "contributions_ytd": 52900.00}
  ]
}
```

## Future Integration

The project is structured for embedding into a larger family dashboard website:
- Clean service abstraction (no UI in the engine)
- Standalone SQLite database (`education.db`)
- Runs on port 8001 to avoid conflicts with retirement-calculator (port 8000)
- Router-based routes ready to mount under a sub-path
