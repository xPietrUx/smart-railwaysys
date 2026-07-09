import type { FastestRouteResponse } from './routing';

export interface TrainCreateRequest {
	trainId: string;
	name: string;
	trainType: 'IC' | 'REGIONAL' | 'FREIGHT';
	fromStation: string;
	toStation: string;
	speedKmh?: number;
}

export interface TrainState {
	trainId: string;
	name: string;
	trainType: 'IC' | 'REGIONAL' | 'FREIGHT';
	fromStation: string;
	toStation: string;
	currentStationId: string;
	nextStationId?: string | null;
	currentSegmentId?: string | null;
	progress: number; // 0.0 do 1.0
	status: 'running' | 'rerouted' | 'arrived' | 'blocked';
	route?: FastestRouteResponse | null;
	currentRouteIndex: number;
	speedKmh: number;
	rerouteMessage?: string | null;
}

export interface SimulationStateResponse {
	trains: TrainState[];
	timestamp: number;
}
