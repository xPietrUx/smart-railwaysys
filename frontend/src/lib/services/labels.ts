import type { RailEventType } from '$lib/types/event';
import type { TrainNode } from '$lib/types/train';

export const EVENT_ICON: Record<RailEventType, string> = {
	line_failure: '⚡',
	derailment: '🚨',
	speed_restriction: '🐢',
	signal_failure: '🚦'
};

export const EVENT_LABEL: Record<RailEventType, string> = {
	line_failure: 'Awaria linii',
	derailment: 'Wykolejenie',
	speed_restriction: 'Ograniczenie prędkości',
	signal_failure: 'Awaria sterowania ruchem'
};

export function trainStatusLabel(status: string) {
	if (status === 'running') return 'w drodze';
	if (status === 'dwelling') return 'na przerwie';
	if (status === 'waiting') return 'zatrzymany';
	if (status === 'derailed') return 'wykolejony';
	return status;
}

export function trainTypeLabel(type: string) {
	if (type === 'IC') return 'InterCity';
	if (type === 'REGIONAL') return 'Regionalny';
	if (type === 'FREIGHT') return 'Towarowy';
	return type;
}

export function directionStatusLabel(status: string) {
	if (status === 'blocked') return 'Zablokowany';
	if (status === 'restricted') return 'Ograniczenie prędkości';
	return 'Aktywny';
}

export function formatStationType(type: string) {
	return type.charAt(0).toUpperCase() + type.slice(1);
}

/** Początek i koniec bieżącego kursu (uwzględnia kierunek tam/powrót). */
export function trainEndpoints(train: TrainNode): { fromId: string; toId: string } {
	return train.direction === 'outbound'
		? { fromId: train.originStationId, toId: train.destinationStationId }
		: { fromId: train.destinationStationId, toId: train.originStationId };
}

export function trainTargetId(train: TrainNode): string {
	return trainEndpoints(train).toId;
}
