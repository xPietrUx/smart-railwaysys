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


class TrackSegment(BaseModel):
	id: str
	source: str
	target: str
	segmentId: str
	line: int
	distKm: float
	travelMin: int
	vmax: int
	railTracks: int
	status: str


class NetworkGraphResponse(BaseModel):
	stations: list[StationNode]
	segments: list[TrackSegment]
	relationshipCount: int
