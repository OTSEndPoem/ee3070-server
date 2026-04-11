"""
新的事件 API
用于替代 ThingSpeak 风格的写入路径，统一承载设备指令、商品、优惠券和交易事件。
"""
import json
from collections import Counter
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import desc
from sqlalchemy.orm import Session

from config import WRITE_API_KEY, READ_API_KEY
from database import get_db
from database.models import Coupon, EventLog, Product


router = APIRouter(prefix="/api", tags=["Events API"])


class EventCreateRequest(BaseModel):
    event_type: str = Field(..., min_length=1)
    command_group: Optional[str] = None
    device_id: Optional[str] = None
    peer_device_id: Optional[str] = None
    entity_type: Optional[str] = None
    entity_id: Optional[str] = None
    sku: Optional[int] = None
    name: Optional[str] = None
    price: Optional[float] = None
    discount: Optional[float] = None
    quantity: Optional[int] = None
    coupon_code: Optional[str] = None
    tx_id: Optional[int] = None
    request_id: Optional[str] = None
    trace_id: Optional[str] = None
    status: Optional[str] = "ok"
    error_code: Optional[str] = None
    error_message: Optional[str] = None
    latency_ms: Optional[int] = None
    payload: Optional[Dict[str, Any]] = None


class ProductUpsertRequest(BaseModel):
    sku: int
    name: str
    price: float
    discount: float = 1.0
    device_id: Optional[str] = None
    request_id: Optional[str] = None
    trace_id: Optional[str] = None


class CouponUpsertRequest(BaseModel):
    code: str
    discount_rate: float
    valid: bool = True
    device_id: Optional[str] = None
    request_id: Optional[str] = None
    trace_id: Optional[str] = None


class CouponUpdateRequest(BaseModel):
    discount_rate: Optional[float] = None
    valid: Optional[bool] = None
    device_id: Optional[str] = None
    request_id: Optional[str] = None
    trace_id: Optional[str] = None


class StockInRequest(BaseModel):
    sku: int
    quantity: int = Field(..., gt=0)
    unit_cost: Optional[float] = None
    name: Optional[str] = None
    device_id: Optional[str] = None
    warehouse_id: Optional[str] = None
    request_id: Optional[str] = None
    trace_id: Optional[str] = None


class CouponIssueRequest(BaseModel):
    code: str
    discount_rate: float = Field(..., gt=0)
    issued_to_device_id: Optional[str] = None
    expires_at: Optional[str] = None
    note: Optional[str] = None
    device_id: Optional[str] = None
    request_id: Optional[str] = None
    trace_id: Optional[str] = None


class CouponRedeemRequest(BaseModel):
    tx_id: int
    amount_before: Optional[float] = None
    amount_after: Optional[float] = None
    device_id: Optional[str] = None
    request_id: Optional[str] = None
    trace_id: Optional[str] = None


class CouponInvalidateRequest(BaseModel):
    reason: Optional[str] = None
    device_id: Optional[str] = None
    request_id: Optional[str] = None
    trace_id: Optional[str] = None


class CheckoutItem(BaseModel):
    sku: int
    quantity: int = Field(..., gt=0)
    price: float = Field(..., ge=0)
    discount: float = 1.0
    name: Optional[str] = None


class CheckoutRequest(BaseModel):
    tx_id: int
    items: List[CheckoutItem] = Field(..., min_length=1)
    coupon_code: Optional[str] = None
    device_id: Optional[str] = None
    request_id: Optional[str] = None
    trace_id: Optional[str] = None


class PaymentRequest(BaseModel):
    tx_id: int
    amount: float = Field(..., ge=0)
    payment_method: str = "unknown"
    status: str = "paid"
    device_id: Optional[str] = None
    request_id: Optional[str] = None
    trace_id: Optional[str] = None
    note: Optional[str] = None


def _require_write_key(write_key: Optional[str]) -> None:
    if write_key != WRITE_API_KEY:
        raise HTTPException(status_code=401, detail="Invalid write key")


def _require_read_key(read_key: Optional[str]) -> None:
    if read_key != READ_API_KEY:
        raise HTTPException(status_code=401, detail="Invalid read key")


def _serialize_payload(payload: Optional[Dict[str, Any]]) -> Optional[str]:
    if payload is None:
        return None
    return json.dumps(payload, ensure_ascii=False)


def _create_event(db: Session, request: EventCreateRequest) -> EventLog:
    event = EventLog(
        event_type=request.event_type.strip(),
        command_group=request.command_group,
        device_id=request.device_id,
        peer_device_id=request.peer_device_id,
        entity_type=request.entity_type,
        entity_id=request.entity_id,
        sku=request.sku,
        name=request.name,
        price=request.price,
        discount=request.discount,
        quantity=request.quantity,
        coupon_code=request.coupon_code,
        tx_id=request.tx_id,
        request_id=request.request_id,
        trace_id=request.trace_id,
        status=request.status,
        error_code=request.error_code,
        error_message=request.error_message,
        latency_ms=request.latency_ms,
        payload_json=_serialize_payload(request.payload),
    )
    db.add(event)
    return event


def _event_query(
    db: Session,
    event_type: Optional[str] = None,
    device_id: Optional[str] = None,
    peer_device_id: Optional[str] = None,
    entity_type: Optional[str] = None,
    entity_id: Optional[str] = None,
    status: Optional[str] = None,
    tx_id: Optional[int] = None,
    coupon_code: Optional[str] = None,
    request_id: Optional[str] = None,
    trace_id: Optional[str] = None,
    since: Optional[datetime] = None,
    until: Optional[datetime] = None,
):
    query = db.query(EventLog)
    if event_type:
        query = query.filter(EventLog.event_type == event_type)
    if device_id:
        query = query.filter(EventLog.device_id == device_id)
    if peer_device_id:
        query = query.filter(EventLog.peer_device_id == peer_device_id)
    if entity_type:
        query = query.filter(EventLog.entity_type == entity_type)
    if entity_id:
        query = query.filter(EventLog.entity_id == entity_id)
    if status:
        query = query.filter(EventLog.status == status)
    if tx_id is not None:
        query = query.filter(EventLog.tx_id == tx_id)
    if coupon_code:
        query = query.filter(EventLog.coupon_code == coupon_code)
    if request_id:
        query = query.filter(EventLog.request_id == request_id)
    if trace_id:
        query = query.filter(EventLog.trace_id == trace_id)
    if since is not None:
        query = query.filter(EventLog.created_at >= since)
    if until is not None:
        query = query.filter(EventLog.created_at <= until)
    return query


@router.post("/events")
async def create_event(
    event: EventCreateRequest,
    write_key: str = Query(..., alias="write_key"),
    db: Session = Depends(get_db),
):
    _require_write_key(write_key)
    try:
        created = _create_event(db, event)
        db.commit()
        db.refresh(created)
        return {"success": True, "event": created.to_dict()}
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/health")
async def health_check():
    return {"status": "ok", "timestamp": datetime.utcnow().isoformat()}


@router.get("/products")
async def list_products(
    read_key: str = Query(..., alias="read_key"),
    db: Session = Depends(get_db),
):
    _require_read_key(read_key)
    try:
        products = db.query(Product).order_by(Product.sku).all()
        return {
            "success": True,
            "count": len(products),
            "products": [product.to_dict() for product in products],
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/products/{sku}")
async def get_product(
    sku: int,
    read_key: str = Query(..., alias="read_key"),
    db: Session = Depends(get_db),
):
    _require_read_key(read_key)
    try:
        product = db.query(Product).filter(Product.sku == sku).first()
        if product is None:
            raise HTTPException(status_code=404, detail="Product not found")
        return {"success": True, "product": product.to_dict()}
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/coupons")
async def list_coupons(
    read_key: str = Query(..., alias="read_key"),
    valid_only: bool = Query(False),
    db: Session = Depends(get_db),
):
    _require_read_key(read_key)
    try:
        query = db.query(Coupon)
        if valid_only:
            query = query.filter(Coupon.valid == 1)

        coupons = query.order_by(Coupon.code).all()
        return {
            "success": True,
            "count": len(coupons),
            "coupons": [coupon.to_dict() for coupon in coupons],
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/events/batch")
async def create_events_batch(
    payload: Dict[str, Any],
    write_key: str = Query(..., alias="write_key"),
    db: Session = Depends(get_db),
):
    _require_write_key(write_key)
    raw_events = payload.get("events", [])
    if not isinstance(raw_events, list) or not raw_events:
        raise HTTPException(status_code=400, detail="events must be a non-empty list")

    created_events: List[EventLog] = []
    try:
        for raw_event in raw_events:
            created_events.append(_create_event(db, EventCreateRequest(**raw_event)))
        db.commit()
        for event in created_events:
            db.refresh(event)
        return {"success": True, "count": len(created_events), "events": [event.to_dict() for event in created_events]}
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/events")
async def list_events(
    limit: int = Query(100, le=1000),
    offset: int = Query(0, ge=0),
    read_key: str = Query(..., alias="read_key"),
    event_type: Optional[str] = Query(None),
    device_id: Optional[str] = Query(None),
    peer_device_id: Optional[str] = Query(None),
    entity_type: Optional[str] = Query(None),
    entity_id: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    tx_id: Optional[int] = Query(None),
    coupon_code: Optional[str] = Query(None),
    request_id: Optional[str] = Query(None),
    trace_id: Optional[str] = Query(None),
    since: Optional[str] = Query(None),
    until: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    try:
        _require_read_key(read_key)
        since_dt = datetime.fromisoformat(since) if since else None
        until_dt = datetime.fromisoformat(until) if until else None
        query = _event_query(
            db,
            event_type=event_type,
            device_id=device_id,
            peer_device_id=peer_device_id,
            entity_type=entity_type,
            entity_id=entity_id,
            status=status,
            tx_id=tx_id,
            coupon_code=coupon_code,
            request_id=request_id,
            trace_id=trace_id,
            since=since_dt,
            until=until_dt,
        )
        total = query.count()
        items = query.order_by(desc(EventLog.created_at)).offset(offset).limit(limit).all()
        return {
            "success": True,
            "total": total,
            "count": len(items),
            "offset": offset,
            "limit": limit,
            "events": [item.to_dict() for item in items],
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/events/latest")
async def get_latest_event(
    read_key: str = Query(..., alias="read_key"),
    event_type: Optional[str] = Query(None),
    device_id: Optional[str] = Query(None),
    peer_device_id: Optional[str] = Query(None),
    entity_type: Optional[str] = Query(None),
    entity_id: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    tx_id: Optional[int] = Query(None),
    coupon_code: Optional[str] = Query(None),
    request_id: Optional[str] = Query(None),
    trace_id: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    try:
        _require_read_key(read_key)
        query = _event_query(
            db,
            event_type=event_type,
            device_id=device_id,
            peer_device_id=peer_device_id,
            entity_type=entity_type,
            entity_id=entity_id,
            status=status,
            tx_id=tx_id,
            coupon_code=coupon_code,
            request_id=request_id,
            trace_id=trace_id,
        )
        latest = query.order_by(desc(EventLog.created_at)).first()
        return {"success": True, "event": latest.to_dict() if latest else None}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/events/summary")
async def events_summary(
    read_key: str = Query(..., alias="read_key"),
    since: Optional[str] = Query(None),
    until: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    try:
        _require_read_key(read_key)
        since_dt = datetime.fromisoformat(since) if since else None
        until_dt = datetime.fromisoformat(until) if until else None
        rows = _event_query(db, since=since_dt, until=until_dt).all()

        by_type = Counter()
        by_status = Counter()
        by_device = Counter()
        by_entity = Counter()
        latest = None

        for row in rows:
            by_type[row.event_type or "unknown"] += 1
            by_status[row.status or "unknown"] += 1
            by_device[row.device_id or "unknown"] += 1
            by_entity[row.entity_type or "unknown"] += 1
            if latest is None or (row.created_at and row.created_at > latest.created_at):
                latest = row

        return {
            "success": True,
            "count": len(rows),
            "by_event_type": dict(by_type),
            "by_status": dict(by_status),
            "by_device": dict(by_device),
            "by_entity_type": dict(by_entity),
            "latest_event": latest.to_dict() if latest else None,
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/products")
async def upsert_product(
    request: ProductUpsertRequest,
    write_key: str = Query(..., alias="write_key"),
    db: Session = Depends(get_db),
):
    _require_write_key(write_key)
    try:
        product = db.query(Product).filter(Product.sku == request.sku).first()
        if product is None:
            product = Product(sku=request.sku, name=request.name, price=request.price, discount=request.discount)
            db.add(product)
        else:
            product.name = request.name
            product.price = request.price
            product.discount = request.discount

        event = _create_event(
            db,
            EventCreateRequest(
                event_type="product_upsert",
                device_id=request.device_id,
                trace_id=request.trace_id,
                request_id=request.request_id,
                entity_type="product",
                entity_id=str(request.sku),
                sku=request.sku,
                name=request.name,
                price=request.price,
                discount=request.discount,
                payload={"sku": request.sku, "name": request.name, "price": request.price, "discount": request.discount},
            ),
        )
        db.commit()
        db.refresh(product)
        db.refresh(event)
        return {"success": True, "product": product.to_dict(), "event": event.to_dict()}
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/coupons")
async def upsert_coupon(
    request: CouponUpsertRequest,
    write_key: str = Query(..., alias="write_key"),
    db: Session = Depends(get_db),
):
    _require_write_key(write_key)
    try:
        coupon = db.query(Coupon).filter(Coupon.code == request.code).first()
        if coupon is None:
            coupon = Coupon(code=request.code, discount_rate=request.discount_rate, valid=1 if request.valid else 0)
            db.add(coupon)
        else:
            coupon.discount_rate = request.discount_rate
            coupon.valid = 1 if request.valid else 0

        event = _create_event(
            db,
            EventCreateRequest(
                event_type="coupon_upsert",
                device_id=request.device_id,
                trace_id=request.trace_id,
                request_id=request.request_id,
                entity_type="coupon",
                entity_id=request.code,
                coupon_code=request.code,
                discount=request.discount_rate,
                status="valid" if request.valid else "invalid",
                payload={"code": request.code, "discount_rate": request.discount_rate, "valid": request.valid},
            ),
        )
        db.commit()
        db.refresh(coupon)
        db.refresh(event)
        return {"success": True, "coupon": coupon.to_dict(), "event": event.to_dict()}
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(exc))


@router.patch("/coupons/{code}")
async def update_coupon(
    code: str,
    request: CouponUpdateRequest,
    write_key: str = Query(..., alias="write_key"),
    db: Session = Depends(get_db),
):
    _require_write_key(write_key)
    try:
        coupon = db.query(Coupon).filter(Coupon.code == code).first()
        if coupon is None:
            raise HTTPException(status_code=404, detail="Coupon not found")

        if request.discount_rate is not None:
            coupon.discount_rate = request.discount_rate
        if request.valid is not None:
            coupon.valid = 1 if request.valid else 0

        event = _create_event(
            db,
            EventCreateRequest(
                event_type="coupon_update",
                device_id=request.device_id,
                trace_id=request.trace_id,
                request_id=request.request_id,
                entity_type="coupon",
                entity_id=code,
                coupon_code=code,
                discount=request.discount_rate if request.discount_rate is not None else coupon.discount_rate,
                status="valid" if coupon.valid else "invalid",
                payload={"code": code, "discount_rate": request.discount_rate, "valid": request.valid},
            ),
        )
        db.commit()
        db.refresh(coupon)
        db.refresh(event)
        return {"success": True, "coupon": coupon.to_dict(), "event": event.to_dict()}
    except HTTPException:
        raise
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/inventory/stock-in")
async def stock_in_product(
    request: StockInRequest,
    write_key: str = Query(..., alias="write_key"),
    db: Session = Depends(get_db),
):
    _require_write_key(write_key)
    try:
        product = db.query(Product).filter(Product.sku == request.sku).first()
        if product is None:
            product = Product(
                sku=request.sku,
                name=request.name or f"SKU-{request.sku}",
                price=request.unit_cost or 0.0,
                discount=1.0,
            )
            db.add(product)
        elif request.name:
            product.name = request.name

        event = _create_event(
            db,
            EventCreateRequest(
                event_type="inventory_stock_in",
                command_group="inventory",
                device_id=request.device_id,
                entity_type="product",
                entity_id=str(request.sku),
                sku=request.sku,
                name=product.name,
                price=request.unit_cost,
                quantity=request.quantity,
                request_id=request.request_id,
                trace_id=request.trace_id,
                status="ok",
                payload={
                    "warehouse_id": request.warehouse_id,
                    "unit_cost": request.unit_cost,
                    "quantity": request.quantity,
                },
            ),
        )
        db.commit()
        db.refresh(product)
        db.refresh(event)
        return {"success": True, "product": product.to_dict(), "event": event.to_dict()}
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/coupons/issue")
async def issue_coupon(
    request: CouponIssueRequest,
    write_key: str = Query(..., alias="write_key"),
    db: Session = Depends(get_db),
):
    _require_write_key(write_key)
    try:
        coupon = db.query(Coupon).filter(Coupon.code == request.code).first()
        if coupon is None:
            coupon = Coupon(code=request.code, discount_rate=request.discount_rate, valid=1)
            db.add(coupon)
        else:
            coupon.discount_rate = request.discount_rate
            coupon.valid = 1

        event = _create_event(
            db,
            EventCreateRequest(
                event_type="coupon_issue",
                command_group="coupon",
                device_id=request.device_id,
                peer_device_id=request.issued_to_device_id,
                entity_type="coupon",
                entity_id=request.code,
                coupon_code=request.code,
                discount=request.discount_rate,
                request_id=request.request_id,
                trace_id=request.trace_id,
                status="issued",
                payload={
                    "issued_to_device_id": request.issued_to_device_id,
                    "expires_at": request.expires_at,
                    "note": request.note,
                },
            ),
        )
        db.commit()
        db.refresh(coupon)
        db.refresh(event)
        return {"success": True, "coupon": coupon.to_dict(), "event": event.to_dict()}
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/coupons/{code}/redeem")
async def redeem_coupon(
    code: str,
    request: CouponRedeemRequest,
    write_key: str = Query(..., alias="write_key"),
    db: Session = Depends(get_db),
):
    _require_write_key(write_key)
    try:
        coupon = db.query(Coupon).filter(Coupon.code == code).first()
        if coupon is None:
            raise HTTPException(status_code=404, detail="Coupon not found")
        if coupon.valid != 1:
            raise HTTPException(status_code=400, detail="Coupon is invalid")

        coupon.valid = 0
        event = _create_event(
            db,
            EventCreateRequest(
                event_type="coupon_redeem",
                command_group="coupon",
                device_id=request.device_id,
                entity_type="coupon",
                entity_id=code,
                coupon_code=code,
                tx_id=request.tx_id,
                discount=coupon.discount_rate,
                request_id=request.request_id,
                trace_id=request.trace_id,
                status="redeemed",
                payload={
                    "amount_before": request.amount_before,
                    "amount_after": request.amount_after,
                },
            ),
        )
        db.commit()
        db.refresh(coupon)
        db.refresh(event)
        return {"success": True, "coupon": coupon.to_dict(), "event": event.to_dict()}
    except HTTPException:
        raise
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/coupons/{code}/invalidate")
async def invalidate_coupon(
    code: str,
    request: CouponInvalidateRequest,
    write_key: str = Query(..., alias="write_key"),
    db: Session = Depends(get_db),
):
    _require_write_key(write_key)
    try:
        coupon = db.query(Coupon).filter(Coupon.code == code).first()
        if coupon is None:
            raise HTTPException(status_code=404, detail="Coupon not found")

        coupon.valid = 0
        event = _create_event(
            db,
            EventCreateRequest(
                event_type="coupon_invalidate",
                command_group="coupon",
                device_id=request.device_id,
                entity_type="coupon",
                entity_id=code,
                coupon_code=code,
                discount=coupon.discount_rate,
                request_id=request.request_id,
                trace_id=request.trace_id,
                status="invalid",
                payload={"reason": request.reason},
            ),
        )
        db.commit()
        db.refresh(coupon)
        db.refresh(event)
        return {"success": True, "coupon": coupon.to_dict(), "event": event.to_dict()}
    except HTTPException:
        raise
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/checkout")
async def checkout_cart(
    request: CheckoutRequest,
    write_key: str = Query(..., alias="write_key"),
    db: Session = Depends(get_db),
):
    _require_write_key(write_key)
    try:
        subtotal = 0.0
        items_payload = []
        for item in request.items:
            line_total = item.price * item.quantity * item.discount
            subtotal += line_total
            items_payload.append(
                {
                    "sku": item.sku,
                    "name": item.name,
                    "quantity": item.quantity,
                    "price": item.price,
                    "discount": item.discount,
                    "line_total": line_total,
                }
            )

        event = _create_event(
            db,
            EventCreateRequest(
                event_type="checkout_complete",
                command_group="checkout",
                device_id=request.device_id,
                entity_type="checkout",
                entity_id=str(request.tx_id),
                tx_id=request.tx_id,
                coupon_code=request.coupon_code,
                price=subtotal,
                quantity=sum(item.quantity for item in request.items),
                request_id=request.request_id,
                trace_id=request.trace_id,
                status="completed",
                payload={"items": items_payload, "subtotal": subtotal, "coupon_code": request.coupon_code},
            ),
        )
        db.commit()
        db.refresh(event)
        return {"success": True, "tx_id": request.tx_id, "subtotal": subtotal, "event": event.to_dict()}
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/payments")
async def record_payment(
    request: PaymentRequest,
    write_key: str = Query(..., alias="write_key"),
    db: Session = Depends(get_db),
):
    _require_write_key(write_key)
    try:
        normalized_status = request.status.strip().lower()
        if normalized_status not in {"paid", "failed", "pending"}:
            raise HTTPException(status_code=400, detail="status must be paid, failed or pending")

        event = _create_event(
            db,
            EventCreateRequest(
                event_type="payment_recorded",
                command_group="payment",
                device_id=request.device_id,
                entity_type="payment",
                entity_id=str(request.tx_id),
                tx_id=request.tx_id,
                price=request.amount,
                request_id=request.request_id,
                trace_id=request.trace_id,
                status=normalized_status,
                payload={
                    "payment_method": request.payment_method,
                    "note": request.note,
                },
            ),
        )
        db.commit()
        db.refresh(event)
        return {"success": True, "tx_id": request.tx_id, "event": event.to_dict()}
    except HTTPException:
        raise
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(exc))
