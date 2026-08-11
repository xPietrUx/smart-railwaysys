import asyncio
import time

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.core.config import ALLOWED_ORIGINS
from app.services import event_service, scenario_service, train_service

router = APIRouter(tags=["live"])


def _origin_allowed(websocket: WebSocket) -> bool:
	# CORSMiddleware nie obejmuje scope 'websocket' — Origin trzeba sprawdzić ręcznie.
	origin = websocket.headers.get("origin")
	if origin is None:
		return True
	return origin in ALLOWED_ORIGINS


def _load_snapshot_sync(driver) -> dict:
	trains = train_service.load_trains_snapshot(driver)
	with driver.session() as session:
		events = event_service.load_events(session)
	return {
		"type": "snapshot",
		"trains": [train.model_dump() for train in trains],
		"events": [event.model_dump() for event in events],
		"timestamp": time.time(),
	}


@router.websocket("/ws/live")
async def live(websocket: WebSocket):
	if not _origin_allowed(websocket):
		await websocket.close(code=4403)
		return

	manager = websocket.app.state.ws_manager
	await manager.connect(websocket)
	try:
		snapshot = await asyncio.to_thread(_load_snapshot_sync, websocket.app.state.driver)
		info = scenario_service.active_info(websocket.app.state)
		snapshot["scenario"] = info.model_dump() if info is not None else None
		snapshot["paused"] = getattr(websocket.app.state, "sim_paused", False)
		snapshot["speed"] = getattr(websocket.app.state, "sim_speed", 1.0)
		snapshot["elapsedRealS"] = getattr(websocket.app.state, "sim_elapsed_real_s", 0.0)
		await websocket.send_json(snapshot)
		while True:
			# Klient nic nie musi wysyłać — jedyny cel to wykrycie rozłączenia.
			await websocket.receive_text()
	except WebSocketDisconnect:
		pass
	finally:
		manager.disconnect(websocket)
