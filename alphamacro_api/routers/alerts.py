"""Authenticated alert API and real-time WebSocket notifications."""
import asyncio
import json
from typing import Any
from fastapi import APIRouter, Depends, HTTPException, Query, WebSocket, WebSocketDisconnect, status
from sqlalchemy import select
from sqlalchemy.orm import Session
from ..core.events import publish_alert, subscribe_alerts, unsubscribe_alerts
from ..core.redis import redis_error
from ..core.security import get_current_user, user_from_token
from ..database import get_db, SessionLocal
from ..models import User, UserAlert
from ..schemas.user import AlertRequest, AlertResponse, AlertUpdateRequest

router = APIRouter()


@router.get("", response_model=list[AlertResponse])
def list_alerts(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return db.scalars(select(UserAlert).where(UserAlert.user_id == user.id).order_by(UserAlert.id.desc())).all()


@router.post("", response_model=AlertResponse, status_code=status.HTTP_201_CREATED)
async def create_alert(payload: AlertRequest, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    alert = UserAlert(user_id=user.id, **payload.model_dump())
    db.add(alert)
    db.commit()
    db.refresh(alert)
    await publish_alert({"type": "alert.created", "user_id": user.id, "alert": AlertResponse.model_validate(alert).model_dump()})
    return alert


@router.patch("/{alert_id}", response_model=AlertResponse)
async def update_alert(alert_id: int, payload: AlertUpdateRequest, db: Session = Depends(get_db),
                       user: User = Depends(get_current_user)):
    alert = db.scalar(select(UserAlert).where(UserAlert.id == alert_id, UserAlert.user_id == user.id))
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(alert, key, value)
    db.commit()
    db.refresh(alert)
    await publish_alert({"type": "alert.updated", "user_id": user.id, "alert": AlertResponse.model_validate(alert).model_dump()})
    return alert


@router.delete("/{alert_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_alert(alert_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    alert = db.scalar(select(UserAlert).where(UserAlert.id == alert_id, UserAlert.user_id == user.id))
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    db.delete(alert)
    db.commit()
    await publish_alert({"type": "alert.deleted", "user_id": user.id, "alert_id": alert_id})


async def _redis_message(pubsub: Any) -> dict[str, Any] | None:
    try:
        message = await asyncio.to_thread(pubsub.get_message, True, 1.0)
    except (redis_error, ValueError):
        return None
    if not message or message.get("type") != "message":
        return None
    try:
        return json.loads(message["data"])
    except (TypeError, json.JSONDecodeError):
        return None


async def _next_event(queue: asyncio.Queue, pubsub: Any | None) -> dict[str, Any] | None:
    if pubsub:
        while True:
            event = await _redis_message(pubsub)
            if event:
                return event
    return await queue.get()


@router.websocket("/ws")
async def alerts_websocket(websocket: WebSocket, token: str = Query(...)):
    """Stream alert changes for the authenticated user.

    Clients pass the same JWT returned by login as ``?token=...``. Events are
    filtered server-side so a connected client only receives its own alerts.
    """
    with SessionLocal() as db:
        user = user_from_token(token, db)
    if not user:
        await websocket.close(code=1008, reason="Authentication required")
        return
    await websocket.accept()
    queue, pubsub = await subscribe_alerts()
    receive_task = asyncio.create_task(websocket.receive_text())
    event_task = None
    try:
        while True:
            event_task = asyncio.create_task(_next_event(queue, pubsub))
            done, _ = await asyncio.wait(
                {receive_task, event_task}, return_when=asyncio.FIRST_COMPLETED
            )
            if receive_task in done:
                message = receive_task.result()
                if message == "ping":
                    await websocket.send_json({"type": "pong"})
                receive_task = asyncio.create_task(websocket.receive_text())
                event_task.cancel()
                event_task = None
                continue
            event = event_task.result()
            if event and event.get("user_id") == user.id:
                await websocket.send_json(event)
    except WebSocketDisconnect:
        pass
    finally:
        receive_task.cancel()
        if event_task:
            event_task.cancel()
        await unsubscribe_alerts(queue, pubsub)
