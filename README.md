# KangaSys Device Monitoring Service

A small end-to-end device monitoring application built for the KangaSys Software Engineering Intern take-home assignment.

## What it does

- Device CRUD: create, list, update, delete
- Stores readings for each device
- Filters readings by time range
- Configurable normal range for each active device
- Automatically creates an alert for every out-of-range reading
- Lists unresolved alerts and resolves them
- Simple browser dashboard for devices, readings, and alerts
- Unit/API tests for important business rules
- Seed command for the supplied sample data

## Why this design?

### Stack

- Python + FastAPI for the HTTP API
- SQLAlchemy + SQLite for persistence
- Pydantic for request/response validation
- Vanilla HTML/CSS/JavaScript for the frontend
- pytest for tests

FastAPI was chosen because it keeps the API small and gives automatic interactive API documentation at `/docs`.

### Data model

The application has three main tables:

1. `devices`
   - id
   - name
   - type
   - status
   - unit
   - normal_min
   - normal_max

2. `readings`
   - id
   - device_id
   - value
   - unit
   - timestamp

3. `alerts`
   - id
   - device_id
   - reading_id
   - timestamp
   - message
   - resolved

### Important assumption: normal range is stored per device

The assignment says each *device type* should have a configurable normal range, but the supplied sample contains two temperature sensors with different ranges:

- Chiller Room Temp Sensor: 2–8 °C
- Server Room Temp Sensor: 18–27 °C

Therefore a single range per type would not be enough for the supplied example. I store the configured range on each device. This still supports type-based defaults later if KangaSys wants them.

### Important assumption: every anomalous reading creates an alert

If a reading is outside its configured range, one alert is created for that reading. This preserves the event history and makes every alert traceable to the exact reading that caused it.

A production system could additionally group repeated alerts into incidents, suppress duplicates, or require multiple consecutive anomalies. Those are deliberately left as future extensions.

### Inactive devices

Inactive devices do not accept new readings and do not have a normal range. This follows the supplied sample where the inactive loading-bay sensor has no range.

## Project structure

```text
kangasys-device-monitor/
├── app/
│   ├── __init__.py
│   ├── main.py
│   ├── database.py
│   ├── models.py
│   ├── schemas.py
│   ├── services.py
│   └── static/
│       ├── index.html
│       ├── app.js
│       └── styles.css
├── tests/
│   ├── __init__.py
│   └── test_api.py
├── sample-data/
│   ├── devices.json
│   └── readings.json
├── .ai/
│   ├── PLAN.md
│   └── PROMPTS.md
├── .gitignore
├── requirements.txt
└── README.md
```

## Run locally

### 1. Create a virtual environment

Windows:

```bash
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

macOS/Linux:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Start the application

```bash
uvicorn app.main:app --reload
```

Open:

- Dashboard: http://127.0.0.1:8000
- API docs: http://127.0.0.1:8000/docs

### 4. Seed the supplied sample data

Run this once from the project root:

```bash
python -m app.main --seed
```

If you want to start completely fresh, delete `device_monitor.db` and run the seed command again.

The supplied sample contains:
- `dev-001`: temperature range 2–8 °C; readings 11.6 and 12.0 are anomalous
- `dev-002`: pressure range 1.5–6 bar; reading 0.6 is anomalous
- `dev-003`: all readings are normal
- `dev-004`: inactive, with no normal range

## Run tests

```bash
.\.venv\Scripts\python.exe -m pytest -q
```

The tests use a separate SQLite database so running the test suite does not alter your local development database.

The tests focus on the rules that are most important to the application:

- device creation
- inactive device rejection
- normal readings not creating alerts
- out-of-range readings creating alerts
- alert resolution
- reading time-range filtering
- device deletion cascading to its readings/alerts

## API overview

### Devices

- `POST /api/devices`
- `GET /api/devices`
- `GET /api/devices/{device_id}`
- `PUT /api/devices/{device_id}`
- `DELETE /api/devices/{device_id}`

### Readings

- `POST /api/devices/{device_id}/readings`
- `GET /api/devices/{device_id}/readings?start=...&end=...`

### Alerts

- `GET /api/alerts?resolved=false`
- `PATCH /api/alerts/{alert_id}/resolve`

## Example reading

```json
{
  "value": 11.6,
  "unit": "°C",
  "timestamp": "2026-08-10T08:45:00Z"
}
```

For a device whose range is 2–8 °C, this creates an alert because `11.6 > 8`.

## What I would improve with more time

- PostgreSQL for production-scale persistence
- database migrations with Alembic
- authentication/authorization
- pagination on all list endpoints
- structured logging and metrics
- background ingestion/queue processing for very high device volume
- alert acknowledgement history and incident grouping
- configurable alert rules beyond simple thresholds
- a richer frontend chart
- Docker and CI
- deployment to a cloud host

## AI usage

AI coding assistance was used as a development aid, not as a one-shot replacement for engineering decisions. The `.ai/` directory records the planned breakdown and representative prompts. The important decisions were reviewed against the assignment and the sample data.

## Submission checklist

Before submitting:

- [ ] Run `pytest -q` and confirm all tests pass.
- [ ] Start the app and manually test the dashboard.
- [ ] Test the API from `/docs`.
- [ ] Review the README and assumptions.
- [ ] Make several meaningful Git commits instead of one giant final commit.
- [ ] Make sure no secrets or local database files are committed.
