from fastapi import APIRouter, Depends, Query
from neo4j import Driver

from app.api.dependencies import get_driver
from app.schemas.routing import FastestRouteResponse
from app.services.routing_service import find_fastest_route_astar

router = APIRouter(tags=["routing"])


@router.get("/api/route/fastest", response_model=FastestRouteResponse)
def get_fastest_route(
	from_station: str = Query(..., description="ID stacji początkowej, np. KAT"),
	to_station: str = Query(..., description="ID stacji docelowej, np. GLI"),
	train_type: str = Query("IC", description="Typ pociągu: IC, REGIONAL, FREIGHT"),
	custom_vmax: int | None = Query(None, description="Opcjonalna niestandardowa prędkość maksymalna pociągu (km/h)"),
	driver: Driver = Depends(get_driver),
):
	with driver.session() as session:
		return find_fastest_route_astar(
			session=session,
			from_station_id=from_station,
			to_station_id=to_station,
			train_type=train_type,
			custom_vmax=custom_vmax,
		)
