from typing import Optional
from pydantic import BaseModel
from app.schemas.routing import FastestRouteResponse


class TrainCreateRequest(BaseModel):
	trainId: str
	name: str
	trainType: str  # 'IC', 'REGIONAL', 'FREIGHT'
	fromStation: str
	toStation: str
	speedKmh: Optional[int] = None


class TrainState(BaseModel):
	trainId: str
	name: str
	trainType: str
	fromStation: str
	toStation: str
	currentStationId: str
	nextStationId: Optional[str] = None
	currentSegmentId: Optional[str] = None
	progress: float  # 0.0 do 1.0 wzdłuż bieżącego odcinka
	status: str  # 'running', 'rerouted', 'arrived', 'blocked'
	route: Optional[FastestRouteResponse] = None
	currentRouteIndex: int = 0
	speedKmh: int
	rerouteMessage: Optional[str] = None


class SimulationStateResponse(BaseModel):
	trains: list[TrainState]
	timestamp: float
