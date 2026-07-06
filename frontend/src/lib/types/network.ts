export type StationNode = {
	id: string;
	code: string;
	name: string;
	type: string;
	lat: number;
	lon: number;
	platforms: number;
	tracks: number;
	dailyTrains: number;
};

export type TrackSegment = {
	id: string;
	source: string;
	target: string;
	segmentId: string;
	line: number;
	distKm: number;
	travelMin: number;
	vmax: number;
	railTracks: number;
	status: string;
};

export type NetworkGraph = {
	stations: StationNode[];
	segments: TrackSegment[];
	relationshipCount: number;
};
