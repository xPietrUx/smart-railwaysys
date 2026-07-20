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

export type DirectionalState = {
	status: string; // 'active' | 'blocked' | 'restricted'
	restrictedVmax: number | null;
	activeEventId: string | null;
};

export type TrackSegment = {
	segmentId: string;
	source: string;
	target: string;
	line: number;
	distKm: number;
	travelMin: number;
	vmax: number;
	railTracks: number;
	forward: DirectionalState; // stan relacji source -> target
	backward: DirectionalState; // stan relacji target -> source
};

export type NetworkGraph = {
	stations: StationNode[];
	segments: TrackSegment[];
	relationshipCount: number;
};
