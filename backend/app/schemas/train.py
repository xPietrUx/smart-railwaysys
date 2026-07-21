from pydantic import BaseModel


class TrainNode(BaseModel):
	id: str
	name: str
	type: str  # 'IC' | 'REGIONAL' | 'FREIGHT'
	originStationId: str
	destinationStationId: str
	direction: str  # 'outbound' | 'return'
	currentStationId: str
	nextStationId: str | None = None
	currentSegmentId: str | None = None
	progress: float
	status: str  # 'dwelling' | 'running' | 'waiting' | 'derailed'
	routeStationIds: list[str] = []
	routeSegmentIds: list[str] = []
	routeIndex: int = 0
	vmax: int
	priority: int
	massTonnes: float
	lengthM: int
	accel: float
	decel: float
	dwellUntil: float | None = None
	delayedByEventId: str | None = None
	updatedAt: float


class TrainsSnapshotResponse(BaseModel):
	trains: list[TrainNode]
	timestamp: float
