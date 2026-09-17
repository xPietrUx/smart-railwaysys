import asyncio
import time

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from neo4j import Driver

from app.api.dependencies import get_driver, require_permission
from app.core import config
from app.schemas.event import EventsSnapshotResponse, IncidentCreateRequest, RailEventNode
from app.services import event_service, train_service

router = APIRouter(tags=["events"])

# Wykolejenie celowo pomijamy — to nie miejsce, które użytkownik "wskazuje", tylko
# konkretny jadący pociąg, więc nie pasuje do formularza zgłaszania incydentu.
_INCIDENT_TYPES = {"line_failure", "speed_restriction", "signal_failure"}


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
			event = event_service.create_event(session, event_type, now)
		else:
			event = event_service.maybe_create_random_event(session, now)
		if event and event.segmentId and event.type in train_service.BLOCKING_EVENT_TYPES:
			train_service.reroute_affected_trains_and_persist(session, event.segmentId, now)
		return event


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


def _create_incident_sync(driver: Driver, event_type: str, target_id: str) -> RailEventNode | None:
	now = time.time()
	with driver.session() as session:
		event = event_service.create_event(session, event_type, now, target_id=target_id)
		# line_failure faktycznie blokuje odcinek (status='blocked') — bez tego
		# pociągi już w drodze przez ten odcinek jechałyby dalej pełną prędkością,
		# bo advance_train nie sprawdza statusu odcinka, po którym się porusza.
		# speed_restriction/signal_failure tylko go spowalniają — te pociągi i tak
		# przeliczą prędkość na najbliższym ticku (edge_lookup ładowany na nowo).
		if event and event.segmentId and event.type in train_service.BLOCKING_EVENT_TYPES:
			train_service.reroute_affected_trains_and_persist(session, event.segmentId, now)
		return event


@router.post("/api/incidents", response_model=RailEventNode, status_code=201)
async def create_incident(
	request: Request,
	payload: IncidentCreateRequest,
	driver: Driver = Depends(get_driver),
	_user: dict = Depends(require_permission("simulation.control")),
):
	"""Ręczne zgłoszenie incydentu przez zalogowanego użytkownika — ta sama logika co
	losowy scheduler (event_service.create_event), tylko z celem wskazanym wprost
	zamiast losowania, więc nie ma drugiej, równoległej ścieżki mutującej stan torów."""
	if payload.type not in _INCIDENT_TYPES:
		raise HTTPException(status_code=422, detail="Nieznany typ incydentu.")

	async with request.app.state.sim_lock:
		event = await asyncio.to_thread(_create_incident_sync, driver, payload.type, payload.targetId)

	if event is None:
		raise HTTPException(
			status_code=409,
			detail="Wskazany cel jest niedostępny — sprawdź, czy nie jest już objęty innym incydentem.",
		)
	return event
