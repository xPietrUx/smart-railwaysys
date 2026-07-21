from pydantic import BaseModel

from app.schemas.network import StationNode


class FastestRouteResult(BaseModel):
	found: bool
	fromStation: str
	toStation: str
	trainType: str
	path: list[StationNode]
	segmentIds: list[str]
	totalTravelMin: float
	totalDistKm: float
	algorithm: str = "A*"
	exploredNodesCount: int
	message: str | None = None
