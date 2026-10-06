from pydantic import BaseModel, Field


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


class IncidentCreateRequest(BaseModel):
	type: str  # 'line_failure' | 'derailment' | 'speed_restriction' | 'signal_failure'
	# Zależnie od typu: id odcinka (line_failure/speed_restriction), pociągu
	# (derailment) albo stacji (signal_failure) — wskazany wprost przez użytkownika.
	targetId: str = Field(min_length=1, max_length=50)
	durationS: float | None = Field(default=None, gt=0.0, le=86400.0)
