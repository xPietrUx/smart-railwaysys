from pydantic import BaseModel


class RailEventNode(BaseModel):
	id: str
	type: str  # 'line_failure' | 'derailment' | 'speed_restriction' | 'signal_failure'
	severity: str  # 'minor' | 'major'
	status: str  # 'active' | 'resolved'
	segmentId: str | None = None
	fromStationId: str | None = None
	toStationId: str | None = None
	stationId: str | None = None
	trainId: str | None = None
	restrictedVmax: int | None = None
	message: str
	startedAt: float
	resolvesAt: float
	resolvedAt: float | None = None


class EventsSnapshotResponse(BaseModel):
	events: list[RailEventNode]
	timestamp: float
