from fastapi import APIRouter, Depends, HTTPException
from neo4j import Driver

from app.api.dependencies import get_driver
from app.schemas.network import (
	NetworkGraphResponse,
	SegmentStatusResponse,
	SegmentStatusUpdate,
)
from app.services.network_service import (
	fetch_network_graph,
	reset_all_segments_status,
	update_segment_status,
)
from app.services.simulation_service import check_and_reroute_trains_on_blockade

router = APIRouter(tags=["network"])


@router.get("/api/network", response_model=NetworkGraphResponse)
def get_network(driver: Driver = Depends(get_driver)):
	with driver.session() as session:
		return fetch_network_graph(session)


@router.patch(
	"/api/network/segments/{segment_id}/status",
	response_model=SegmentStatusResponse,
)
def patch_segment_status(
	segment_id: str,
	payload: SegmentStatusUpdate,
	driver: Driver = Depends(get_driver),
):
	if payload.status not in ("active", "blocked"):
		raise HTTPException(
			status_code=400, detail="Status musi mieć wartość 'active' lub 'blocked'"
		)
	with driver.session() as session:
		success = update_segment_status(session, segment_id, payload.status)
		if not success:
			raise HTTPException(status_code=404, detail=f"Odcinek {segment_id} nie został znaleziony")
		if payload.status == "blocked":
			check_and_reroute_trains_on_blockade(driver, segment_id)
		return SegmentStatusResponse(
			segmentId=segment_id, status=payload.status, success=True
		)



@router.post("/api/network/segments/reset-status")
def reset_segments_status(driver: Driver = Depends(get_driver)):
	with driver.session() as session:
		count = reset_all_segments_status(session)
		return {"success": True, "resetCount": count}


