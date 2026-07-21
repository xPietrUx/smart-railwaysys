export type RailEventType = 'line_failure' | 'derailment' | 'speed_restriction' | 'signal_failure';
export type RailEventSeverity = 'minor' | 'major';
export type RailEventStatus = 'active' | 'resolved';

export type RailEventNode = {
	id: string;
	type: RailEventType;
	severity: RailEventSeverity;
	status: RailEventStatus;
	segmentId: string | null;
	fromStationId: string | null;
	toStationId: string | null;
	stationId: string | null;
	trainId: string | null;
	restrictedVmax: number | null;
	message: string;
	startedAt: number;
	resolvesAt: number;
	resolvedAt: number | null;
};

export type EventsSnapshotResponse = {
	events: RailEventNode[];
	timestamp: number;
};
