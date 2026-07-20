from pydantic import BaseModel


class StationNode(BaseModel):
	id: str
	code: str
	name: str
	type: str
	lat: float
	lon: float
	platforms: int
	tracks: int
	dailyTrains: int


class DirectionalState(BaseModel):
	status: str  # 'active' | 'blocked' | 'restricted'
	restrictedVmax: int | None = None
	activeEventId: str | None = None


class TrackSegment(BaseModel):
	segmentId: str
	source: str
	target: str
	line: int
	distKm: float
	travelMin: int
	vmax: int
	railTracks: int
	forward: DirectionalState  # stan relacji source -> target
	backward: DirectionalState  # stan relacji target -> source


class NetworkGraphResponse(BaseModel):
	stations: list[StationNode]
	segments: list[TrackSegment]
	relationshipCount: int
