# GridSense — AI-Based Energy Consumption Forecasting & Optimization System

A full-stack platform that forecasts energy consumption, detects anomalies, generates
optimization recommendations, and simulates "what-if" scenarios for buildings and their
devices.

**Stack:** FastAPI (Python) · React + Vite · SQLite/PostgreSQL · SQLAlchemy · JWT auth ·
Prophet + scikit-learn · Recharts

---

## 1. System architecture

```
energy-forecast-app/
├── backend/
│   ├── app/
│   │   ├── core/        # config, JWT auth, RBAC
│   │   ├── db/           # SQLAlchemy session/engine
│   │   ├── models/        # ORM models (User, Building, Device, EnergyReading,
│   │   │                   #  Forecast, Anomaly, Recommendation, SimulationScenario,
│   │   │                   #  Dataset, Alert)
│   │   ├── schemas/        # Pydantic request/response schemas
│   │   ├── ml/             # forecasting.py, anomaly.py, optimization.py, simulation.py
│   │   │                   #   (pure functions — no FastAPI/DB dependency, independently testable)
│   │   ├── services/       # alerts.py (alert creation helper), retraining.py (scheduler)
│   │   ├── api/routes/     # auth, assets, datasets, forecasts, anomalies,
│   │   │                   #   recommendations, simulations, analytics, alerts, reports
│   │   └── main.py         # app assembly, CORS, router registration, scheduler lifespan
│   ├── tests/              # pytest suite (32 tests)
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── api/client.js    # axios instance, JWT injection, 401 handling
│   │   ├── context/AuthContext.jsx
│   │   ├── components/      # Layout, StatCard, Panel, badges, ProtectedRoute,
│   │   │                     #   NotificationsBell
│   │   └── pages/            # Login, Register, Dashboard, Buildings, BuildingDetail,
│   │                          #   DeviceDetail, DatasetUpload
│   ├── Dockerfile
│   └── vite.config.js
└── docker-compose.yml
```

**Layering.** The ML layer (`app/ml/*`) is deliberately decoupled from FastAPI and the
database — each module is a set of pure functions operating on plain lists/dataframes.
This keeps forecasting, anomaly detection, optimization, and simulation independently
unit-testable and swappable without touching route code.

**Non-blocking ML execution.** Forecast generation is dispatched via FastAPI
`BackgroundTasks`: `POST /api/forecasts/generate` returns `202 Accepted` immediately, and
the actual Prophet/regression training runs in the background, writing results that the
client polls for via `GET /api/forecasts/latest/{device_id}`.

## 2. Dataset

Energy readings are modeled as one row per `(device_id, timestamp)`:

| column          | type            | notes                                   |
|-----------------|-----------------|------------------------------------------|
| `timestamp`     | ISO datetime    | required                                  |
| `device_id`     | int or string   | required; matched against device ID first, then device name (case-insensitive) if not numeric |
| `energy_kwh`    | float ≥ 0       | required                                  |
| `temperature_c` | float           | optional                                  |

CSV upload (`POST /api/datasets/upload`) validates and reports rather than silently
failing:
- missing required columns → rejected with a clear error
- unparsable timestamps / missing energy values → dropped, count reported
- negative energy values → dropped, count reported
- `device_id` values that are neither a known numeric ID nor a known device name →
  skipped, values reported (this previously crashed the endpoint with a raw
  `ValueError` on non-numeric IDs like `"HVAC_1"` — fixed to resolve by name first)
- very sparse uploads (<24 rows) → flagged as a warning, still processed

A synthetic generator (used for local development/demo) produces hourly readings with
daily/weekly seasonality, a temperature series, and injected anomalies (spikes and
night-time faults) so forecasting and anomaly detection have realistic signal to work
with out of the box.

## 3. Forecasting methodology

Three interchangeable backends, selected per-request:

- **Prophet** — handles daily + weekly seasonality natively, returns confidence
  intervals, and is the default choice for most devices. Requires ≥48 hourly points;
  falls back to regression automatically if training fails (e.g. sparse data).
- **ARIMA** (`statsmodels`, order `(2,1,2)`) — classic statistical time-series model,
  good at capturing autocorrelation/trend without assuming a fixed seasonal shape.
  Capped at a 7-day direct projection even when a 30-day horizon is requested —
  autoregressive error compounds too much beyond that to be meaningful at this order,
  and the response says so via a `note` field rather than silently returning
  garbage. Falls back to regression if fitting fails.
- **Regression baseline** — linear regression over a time index plus hour-of-day /
  day-of-week dummy variables. Faster, no external seasonality assumptions, used both as
  a fallback and as a comparison point.

`GET /api/analytics/device/{id}/forecast-accuracy` returns MAE/RMSE/MAPE for every run,
by model type, and the dashboard's **model comparison** panel plots the latest run of
each model side-by-side as a bar chart plus a full run history table — so Prophet,
ARIMA, and regression can be compared directly rather than just inspected one at a time.

Both Prophet/ARIMA readings are resampled to an hourly grid with gap interpolation
before training, and evaluated on a held-out tail slice of the series (last ~15%) to
produce honest error metrics rather than in-sample-only numbers.

Horizons: `24h`, `7d`, `30d` (all expressed as hourly steps).

## 4. Anomaly detection & peak analysis

- **Z-score** — flags points where `|z| ≥ 3` (configurable), tags night-time occurrences
  as more likely faults, and assigns severity by z-magnitude.
- **Isolation Forest** — trained per-device on `(energy_kwh, hour, day_of_week)`, catches
  contextual anomalies the z-score method misses (e.g. normal-magnitude but
  wrong-time-of-day usage).
- **Peak analysis** — computes the historical load threshold at the 90th percentile and
  the hour-of-day band that consistently exceeds it, surfaced as a human-readable alert
  (e.g. *"Expected peak consumption between 11:00 and 13:00"*).
- **Visualization** — detected anomalies aren't just listed; they're plotted directly on
  the historical/forecast chart as colored markers (red/amber/gray by severity), using a
  numeric time axis so the overlay lines up exactly with the actual and predicted series
  regardless of any timestamp-formatting differences between them.

## 5. Optimization recommendations

Rule-based rather than a black-box model, so every recommendation is explainable and
auditable — it's driven directly by the peak-hour analysis and recent anomaly history:

- **Load balancing** — flagged when peak-hour average exceeds off-peak average by >20%.
- **Off-peak scheduling** — flagged when night-time baseline usage is disproportionately
  high (candidate for batch/background job scheduling).
- **Shutdown / inspection** — flagged when a device has recent high-severity anomalies.
- Each recommendation carries an estimated kWh savings figure and a priority.

## 6. Scenario simulation

Four scenario types, each a simple, explainable multiplier model against a building's
baseline daily consumption (not a black box — the assumptions are visible in
`app/ml/simulation.py`):

| scenario         | parameter                     | assumption                                  |
|------------------|--------------------------------|----------------------------------------------|
| `occupancy`      | `occupancy_change_percent`    | energy scales at ~0.6× occupancy change       |
| `temperature`     | `temperature_change_c`        | ~3%/°C (HVAC sensitivity)                     |
| `shutdown`        | `hours_shutdown_per_day`, `device_share_of_load` | proportional reduction over shutdown window |
| `peak_reduction`  | `peak_reduction_percent`      | peak hours ≈ 35% of daily load                |

Each run returns baseline/projected kWh, savings (kWh and %), and an estimated cost
impact.

## 7. Auth & RBAC

JWT bearer auth (`python-jose`), passwords hashed with `bcrypt` directly (not via
`passlib`, to sidestep a known passlib/bcrypt version-detection bug). Three roles:

- **admin** — full access, including creating buildings/devices and uploading datasets
- **analyst** — can generate forecasts/anomalies/recommendations/simulations
- **viewer** — read-only

## 8. Bonus features

All bonus features from the brief are implemented:

- **Automated retraining pipeline** — an APScheduler background job (`app/services/retraining.py`)
  re-runs forecast generation for every device with readings every 24h (configurable),
  reusing each device's last model/horizon. Also triggerable on demand via
  `POST /api/forecasts/retrain-all` (admin only) instead of waiting for the schedule.
- **Model comparison dashboard** — the device page's "Model comparison" panel plots the
  latest MAE/RMSE/MAPE of Prophet, ARIMA, and regression side-by-side as a bar chart,
  plus a full run-history table underneath.
- **Alert notification system** — a bell icon in the top nav (polls every 30s) shows
  unread alerts generated from high-severity anomalies, forecasts that cross the peak
  threshold, and retraining completions. Backed by an `Alert` table and
  `/api/alerts` (list/unread-count/mark-read/mark-all-read).
- **Export reports (CSV/PDF)** — `GET /api/reports/device/{id}/csv` streams raw readings
  as CSV; `GET /api/reports/device/{id}/pdf` generates a formatted PDF (via `reportlab`)
  with a summary, latest forecast accuracy, recent anomalies, and recommendations. Both
  have buttons on the device detail page.
- **Real-time monitoring** — implemented as short-interval polling (alerts every 30s)
  rather than WebSockets, to keep the transport layer simple; genuinely real-time push
  would be the natural next step if this needed to scale to many concurrent viewers.
- **Dockerized deployment** — `docker-compose.yml` builds and runs both services
  (backend on `:8000`, frontend served via nginx on `:3000`), with a named volume for
  the SQLite file. See §11.

## 9. Auth & RBAC

JWT bearer auth (`python-jose`), passwords hashed with `bcrypt` directly (not via
`passlib`, to sidestep a known passlib/bcrypt version-detection bug). Three roles:

- **admin** — full access, including creating buildings/devices, uploading datasets, and
  manually triggering retraining
- **analyst** — can generate forecasts/anomalies/recommendations/simulations
- **viewer** — read-only

## 10. API reference (selected endpoints)

| Method | Path                                        | Auth        | Purpose                          |
|--------|---------------------------------------------|-------------|-----------------------------------|
| POST   | `/api/auth/register`                        | —           | create user                        |
| POST   | `/api/auth/login`                           | —           | get JWT                            |
| POST   | `/api/buildings`                            | admin       | create building                    |
| POST   | `/api/devices`                              | admin       | create device                      |
| POST   | `/api/datasets/upload`                      | admin/analyst | upload + validate CSV             |
| POST   | `/api/forecasts/generate`                   | admin/analyst | 202, runs in background            |
| GET    | `/api/forecasts/latest/{device_id}`         | any         | latest forecast + accuracy metrics |
| POST   | `/api/forecasts/retrain-all`                | admin       | trigger retraining pipeline now    |
| POST   | `/api/anomalies/detect/{device_id}?method=` | admin/analyst | `z_score` \| `isolation_forest`   |
| GET    | `/api/anomalies/peaks/{device_id}`          | any         | peak-hour threshold + alerts       |
| POST   | `/api/recommendations/generate/{device_id}` | admin/analyst | rule-based recommendations        |
| POST   | `/api/simulations/run`                      | admin/analyst | run a what-if scenario            |
| GET    | `/api/analytics/building/{id}/summary`      | any         | dashboard summary                  |
| GET    | `/api/alerts`                               | any         | list alerts (`?unread_only=true`)  |
| POST   | `/api/alerts/{id}/read`                     | any         | mark one alert read                |
| GET    | `/api/reports/device/{id}/csv`              | any         | export readings as CSV             |
| GET    | `/api/reports/device/{id}/pdf`              | any         | export a formatted PDF report      |

Full interactive docs are available at `/docs` (Swagger UI) once the backend is running.
Note: the padlock "Authorize" button there expects a raw bearer token pasted in (not a
username/password form) — call `/api/auth/login`, copy `access_token`, paste it in.

## 11. Running locally

```bash
# Backend
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000

# Frontend (in a second terminal)
cd frontend
npm install
npm run dev
```

Frontend expects the API at `http://localhost:8000` (see `frontend/.env`).

### Or with Docker Compose

```bash
docker compose up --build
```

Backend at `http://localhost:8000`, frontend at `http://localhost:3000`. Uses a named
volume for the SQLite file so data survives container restarts; see the commented-out
Postgres service in `docker-compose.yml` for a production-grade swap.

## 12. Tests

```bash
cd backend
pytest tests/ -v
```

32 tests covering auth/RBAC, dataset validation edge cases (including the
device-id-by-name fix), forecasting (Prophet/ARIMA/regression), manual + automated
retraining, anomaly detection, alerts, CSV/PDF export, recommendations, simulation, and
analytics.

## 13. Known trade-offs / next steps

- SQLite is used by default; swap `DATABASE_URL` for Postgres in production (models are
  DB-agnostic, and `docker-compose.yml` has a commented-out Postgres service ready to
  uncomment).
- Alembic is included in requirements but migrations aren't set up yet — `create_all` is
  used for simplicity; would add proper migrations before a production deploy.
- Real-time monitoring is polling-based (30s interval), not WebSocket push — fine at
  small scale, would need revisiting for many concurrent dashboard viewers.
- LSTM wasn't implemented alongside Prophet/ARIMA/regression — the brief listed it as
  optional ("you may use"), and three models already give a meaningful comparison story;
  could be added as a fourth if deep-learning-based forecasting specifically needs to be
  demonstrated.

## 14. Troubleshooting

**Windows + Python 3.13/3.14:** `numpy`, `pandas`, and `scikit-learn` at these pinned
versions don't yet publish prebuilt Windows wheels for the newest Python releases, so
`pip` falls back to compiling from source — which can fail with MSVC/ninja build errors
that have nothing to do with this codebase. Use **Python 3.11 or 3.12** for the backend
venv instead:

```powershell
py -3.11 -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

**`ModuleNotFoundError: No module named 'jose'` with a `print x` syntax error inside
it:** this means `pip install jose` was run instead of `pip install "python-jose[cryptography]"`
— there's an old, unrelated PyPI package literally named `jose`. Run
`pip uninstall jose -y` then `pip install -r requirements.txt` to get the right one.

