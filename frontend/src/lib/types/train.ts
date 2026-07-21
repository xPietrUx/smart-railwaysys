export type TrainType = 'IC' | 'REGIONAL' | 'FREIGHT';
export type TrainDirection = 'outbound' | 'return';
export type TrainStatus = 'dwelling' | 'running' | 'waiting' | 'derailed';

export type TrainNode = {
	id: string;
	name: string;
	type: TrainType;
	originStationId: string;
	destinationStationId: string;
	direction: TrainDirection;
	currentStationId: string;
	nextStationId: string | null;
	currentSegmentId: string | null;
	progress: number;
	status: TrainStatus;
	routeStationIds: string[];
	routeSegmentIds: string[];
	routeIndex: number;
	vmax: number;
	priority: number;
	massTonnes: number;
	lengthM: number;
	accel: number;
	decel: number;
	dwellUntil: number | null;
	delayedByEventId: string | null;
	updatedAt: number;
};

export type TrainsSnapshotResponse = {
	trains: TrainNode[];
	timestamp: number;
};
