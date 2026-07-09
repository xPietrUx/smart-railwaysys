import type { StationNode, TrackSegment } from './network';

export type FastestRouteResponse = {
	found: boolean;
	fromStation: string;
	toStation: string;
	trainType: string;
	path: StationNode[];
	segments: TrackSegment[];
	totalTravelMin: number;
	totalDistKm: number;
	algorithm: string;
	exploredNodesCount: number;
	message?: string | null;
};
