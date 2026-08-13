from datetime import datetime, timezone

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from .models import Alert, Device, Reading
from .schemas import DeviceCreate, DeviceUpdate, ReadingCreate


def validate_device_payload(payload: DeviceCreate) -> None:
    try:
        payload.validate_range()
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


def create_device(db: Session, payload: DeviceCreate) -> Device:
    validate_device_payload(payload)

    if db.get(Device, payload.id):
        raise HTTPException(status_code=409, detail="Device ID already exists")

    device = Device(**payload.model_dump())
    db.add(device)
    db.commit()
    db.refresh(device)
    return device


def update_device(db: Session, device: Device, payload: DeviceUpdate) -> Device:
    data = payload.model_dump(exclude_unset=True)
    for key, value in data.items():
        setattr(device, key, value)

    if device.status == "active":
        if device.normal_min is None or device.normal_max is None:
            raise HTTPException(
                status_code=422,
                detail="active devices require normal_min and normal_max",
            )
        if device.normal_min >= device.normal_max:
            raise HTTPException(
                status_code=422,
                detail="normal_min must be smaller than normal_max",
            )
    else:
        device.normal_min = None
        device.normal_max = None

    db.commit()
    db.refresh(device)
    return device


def create_reading(
    db: Session,
    device: Device,
    payload: ReadingCreate,
) -> tuple[Reading, Alert | None]:
    if device.status != "active":
        raise HTTPException(
            status_code=409,
            detail="Inactive devices cannot receive readings",
        )

    if payload.unit != device.unit:
        raise HTTPException(
            status_code=422,
            detail=f"Reading unit must be {device.unit}",
        )

    timestamp = payload.timestamp or datetime.now(timezone.utc)
    reading = Reading(
        device_id=device.id,
        value=payload.value,
        unit=payload.unit,
        timestamp=timestamp,
    )
    db.add(reading)
    db.flush()

    alert = None
    if device.normal_min is not None and device.normal_max is not None:
        outside_range = (
            payload.value < device.normal_min
            or payload.value > device.normal_max
        )
        if outside_range:
            direction = "below minimum" if payload.value < device.normal_min else "above maximum"
            alert = Alert(
                device_id=device.id,
                reading_id=reading.id,
                timestamp=timestamp,
                message=(
                    f"{device.name} reading {payload.value:g} {device.unit} "
                    f"is {direction} the configured normal range "
                    f"({device.normal_min:g}–{device.normal_max:g} {device.unit})."
                ),
            )
            db.add(alert)

    db.commit()
    db.refresh(reading)
    if alert:
        db.refresh(alert)
    return reading, alert


def get_readings(
    db: Session,
    device_id: str,
    start: datetime | None = None,
    end: datetime | None = None,
) -> list[Reading]:
    stmt = select(Reading).where(Reading.device_id == device_id)

    if start:
        stmt = stmt.where(Reading.timestamp >= start)
    if end:
        stmt = stmt.where(Reading.timestamp <= end)

    stmt = stmt.order_by(Reading.timestamp.desc())
    return list(db.scalars(stmt).all())
