import asyncio
import time

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from neo4j import Driver

from app.api.dependencies import get_driver
from app.core import config
from app.schemas.event import EventsSnapshotResponse, RailEventNode
from app.services import event_service

router = APIRouter(tags=["events"])


@router.get("/api/events", response_model=EventsSnapshotResponse)
def get_events(
	status: str | None = Query(None, description="Filtr: 'active' lub 'resolved'"),
	driver: Driver = Depends(get_driver),
):
	with driver.session() as session:
		events = event_service.load_events(session, status=status)
	return EventsSnapshotResponse(events=events, timestamp=time.time())


def _trigger_event_sync(driver: Driver, event_type: str | None) -> RailEventNode | None:
	now = time.time()
	with driver.session() as session:
		if event_type:
			return event_service.create_event(session, event_type, now)
		return event_service.maybe_create_random_event(session, now)


@router.post("/api/simulation/events/trigger", response_model=RailEventNode)
async def trigger_event(
	request: Request,
	eventType: str | None = Query(None, description="Wymuś konkretny typ, np. 'line_failure'"),
	driver: Driver = Depends(get_driver),
):
	# Debugowy/demonstracyjny wyjątek od "system jest domyślnie autonomiczny" —
	# idzie przez ten sam event_service.create_event co losowy scheduler, więc
	# nie ma drugiej, równoległej ścieżki mutującej stan torów.
	if not config.SIM_DEBUG_ENDPOINTS_ENABLED:
		raise HTTPException(status_code=403, detail="Debugowe wyzwalanie zdarzeń jest wyłączone")

	async with request.app.state.sim_lock:
		event = await asyncio.to_thread(_trigger_event_sync, driver, eventType)

	if event is None:
		raise HTTPException(status_code=409, detail="Brak dostępnego celu dla tego typu zdarzenia")
	return event
