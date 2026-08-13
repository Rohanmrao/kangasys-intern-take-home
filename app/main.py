import json
import sys
from datetime import datetime
from pathlib import Path

from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import select
from sqlalchemy.orm import Session

from .database import Base, SessionLocal, engine, get_db
from .models import Alert, Device, Reading
from .schemas import (
    AlertOut,
    DeviceCreate,
    DeviceOut,
    DeviceUpdate,
    ReadingCreate,
    ReadingOut,
)
from .services import create_device, create_reading, get_readings, update_device

BASE_DIR = Path(__file__).resolve().parent.parent
STATIC_DIR = Path(__file__).resolve().parent / "static"

@asynccontextmanager
async def lifespan(_app: FastAPI):
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(
    title="KangaSys Device Monitoring Service",
    version="1.0.0",
    description="Device, reading, and threshold-alert monitoring API.",
    lifespan=lifespan,
)

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/", include_in_schema=False)
def dashboard():
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.post("/api/devices", response_model=DeviceOut, status_code=201)
def add_device(payload: DeviceCreate, db: Session = Depends(get_db)):
    return create_device(db, payload)


@app.get("/api/devices", response_model=list[DeviceOut])
def list_devices(db: Session = Depends(get_db)):
    return list(db.scalars(select(Device).order_by(Device.name)).all())


@app.get("/api/devices/{device_id}", response_model=DeviceOut)
def get_device(device_id: str, db: Session = Depends(get_db)):
    device = db.get(Device, device_id)
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    return device


@app.put("/api/devices/{device_id}", response_model=DeviceOut)
def edit_device(
    device_id: str,
    payload: DeviceUpdate,
    db: Session = Depends(get_db),
):
    device = db.get(Device, device_id)
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    return update_device(db, device, payload)


@app.delete("/api/devices/{device_id}", status_code=204)
def remove_device(device_id: str, db: Session = Depends(get_db)):
    device = db.get(Device, device_id)
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")

    db.delete(device)
    db.commit()


@app.post(
    "/api/devices/{device_id}/readings",
    response_model=ReadingOut,
    status_code=201,
)
def add_reading(
    device_id: str,
    payload: ReadingCreate,
    db: Session = Depends(get_db),
):
    device = db.get(Device, device_id)
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")

    reading, _ = create_reading(db, device, payload)
    return reading


@app.get(
    "/api/devices/{device_id}/readings",
    response_model=list[ReadingOut],
)
def list_readings(
    device_id: str,
    start: datetime | None = Query(default=None),
    end: datetime | None = Query(default=None),
    db: Session = Depends(get_db),
):
    if not db.get(Device, device_id):
        raise HTTPException(status_code=404, detail="Device not found")
    if start and end and start > end:
        raise HTTPException(status_code=422, detail="start must be before end")
    return get_readings(db, device_id, start, end)


@app.get("/api/alerts", response_model=list[AlertOut])
def list_alerts(
    resolved: bool | None = Query(default=False),
    db: Session = Depends(get_db),
):
    stmt = select(Alert).order_by(Alert.timestamp.desc())
    if resolved is not None:
        stmt = stmt.where(Alert.resolved == resolved)
    return list(db.scalars(stmt).all())


@app.patch("/api/alerts/{alert_id}/resolve", response_model=AlertOut)
def resolve_alert(alert_id: int, db: Session = Depends(get_db)):
    alert = db.get(Alert, alert_id)
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")

    alert.resolved = True
    db.commit()
    db.refresh(alert)
    return alert


def seed_sample_data():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    try:
        if db.scalar(select(Device).limit(1)):
            print("Database already contains data; seed skipped.")
            return

        sample_dir = BASE_DIR / "sample-data"
        devices = json.loads((sample_dir / "devices.json").read_text(encoding="utf-8"))
        readings = json.loads((sample_dir / "readings.json").read_text(encoding="utf-8"))

        for item in devices:
            device = Device(
                id=item["id"],
                name=item["name"],
                type=item["type"],
                status=item["status"],
                unit=item["unit"],
                normal_min=(item["normalRange"] or {}).get("min") if item["normalRange"] else None,
                normal_max=(item["normalRange"] or {}).get("max") if item["normalRange"] else None,
            )
            db.add(device)

        db.commit()

        for item in readings:
            device = db.get(Device, item["deviceId"])
            if device and device.status == "active":
                payload = ReadingCreate(
                    value=item["value"],
                    unit=device.unit,
                    timestamp=datetime.fromisoformat(item["timestamp"].replace("Z", "+00:00")),
                )
                create_reading(db, device, payload)

        print("Sample data loaded successfully.")
    finally:
        db.close()


if __name__ == "__main__":
    if "--seed" in sys.argv:
        seed_sample_data()
