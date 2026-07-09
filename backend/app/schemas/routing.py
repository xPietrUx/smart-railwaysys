from pydantic import BaseModel
from app.schemas.network import StationNode, TrackSegment


class FastestRouteResponse(BaseModel):
	found: bool
	fromStation: str
	toStation: str
	trainType: str
	path: list[StationNode]
	segments: list[TrackSegment]
	totalTravelMin: float
	totalDistKm: float
	algorithm: str = "A*"
	exploredNodesCount: int
	message: str | None = None
