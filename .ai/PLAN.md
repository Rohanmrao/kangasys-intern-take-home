# AI-assisted development plan

The assignment explicitly encourages AI tools but says the important thing is the engineering process. This file records a practical breakdown used during development.

## Phase 1 — Understand

1. Extract mandatory requirements from the problem statement.
2. Inspect sample devices and readings.
3. Identify ambiguities:
   - range per type vs per device
   - whether every anomaly creates an alert
   - how inactive devices behave
4. Write down assumptions before implementation.

## Phase 2 — Design

1. Choose Python + FastAPI because Python is familiar and FastAPI provides a small, typed API.
2. Choose SQLite for a self-contained take-home project.
3. Separate:
   - models/persistence
   - request/response schemas
   - business logic
   - HTTP routes
   - frontend
4. Define the three-table data model: devices, readings, alerts.

## Phase 3 — Implement incrementally

1. Database and models.
2. Device CRUD.
3. Reading ingestion.
4. Threshold detection.
5. Alert resolution.
6. Frontend.
7. Tests.
8. README.

## Phase 4 — Verify

1. Test normal readings.
2. Test values below minimum.
3. Test values above maximum.
4. Test inactive device behavior.
5. Test invalid units.
6. Test time filtering.
7. Test alert resolution.
8. Manually use the dashboard.

## Phase 5 — Review

Ask:
- Can a new device type be added without changing the alert algorithm?
- Is threshold logic isolated?
- Are API validation and business validation understandable?
- Does the README explain assumptions?
- Are commits meaningful?
