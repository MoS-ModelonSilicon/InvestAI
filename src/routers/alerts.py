from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from src.database import get_db
from src.models import Alert
from src.schemas.alerts import AlertCreate, AlertOut
from src.services.market_data import fetch_stock_info

router = APIRouter(prefix="/api/alerts", tags=["alerts"])


@router.get("")
def list_alerts(db: Session = Depends(get_db)):
    alerts = db.query(Alert).order_by(Alert.created_at.desc()).all()
    result = []
    for a in alerts:
        info = fetch_stock_info(a.symbol)
        current_price = info.get("price", 0) if info else 0

        if a.active and not a.triggered:
            hit = False
            if a.condition == "above" and current_price >= a.target_price:
                hit = True
            elif a.condition == "below" and current_price <= a.target_price:
                hit = True
            if hit:
                a.triggered = 1
                a.triggered_at = datetime.utcnow()
                db.commit()
                db.refresh(a)

        result.append({
            "id": a.id,
            "symbol": a.symbol,
            "name": a.name,
            "condition": a.condition,
            "target_price": a.target_price,
            "active": a.active,
            "triggered": a.triggered,
            "triggered_at": a.triggered_at,
            "created_at": a.created_at,
            "current_price": round(current_price, 2),
        })
    return result


@router.get("/triggered")
def triggered_alerts(db: Session = Depends(get_db)):
    alerts = db.query(Alert).filter(Alert.triggered == 1).order_by(Alert.triggered_at.desc()).all()
    return [{"id": a.id, "symbol": a.symbol, "name": a.name, "condition": a.condition,
             "target_price": a.target_price, "triggered_at": a.triggered_at} for a in alerts]


@router.post("")
def create_alert(payload: AlertCreate, db: Session = Depends(get_db)):
    alert = Alert(
        symbol=payload.symbol.upper(),
        name=payload.name,
        condition=payload.condition,
        target_price=payload.target_price,
    )
    db.add(alert)
    db.commit()
    db.refresh(alert)
    return alert


@router.delete("/{alert_id}")
def delete_alert(alert_id: int, db: Session = Depends(get_db)):
    a = db.query(Alert).filter(Alert.id == alert_id).first()
    if not a:
        raise HTTPException(404, "Alert not found")
    db.delete(a)
    db.commit()
    return {"ok": True}


@router.post("/{alert_id}/dismiss")
def dismiss_alert(alert_id: int, db: Session = Depends(get_db)):
    a = db.query(Alert).filter(Alert.id == alert_id).first()
    if not a:
        raise HTTPException(404, "Alert not found")
    a.active = 0
    db.commit()
    return {"ok": True}
