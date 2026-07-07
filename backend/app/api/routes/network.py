from fastapi import APIRouter, Depends
from neo4j import Driver

from app.api.dependencies import get_driver
from app.schemas.network import NetworkGraphResponse
from app.services.network_service import fetch_network_graph

router = APIRouter(tags=["network"])


@router.get("/api/network", response_model=NetworkGraphResponse)
def get_network(driver: Driver = Depends(get_driver)):
	with driver.session() as session:
		return fetch_network_graph(session)
