import type { RailEventType } from '$lib/types/event';
import type { RailEventNode } from '$lib/types/event';
import type { TranslationKey, Translator } from '$lib/i18n';
import type { TrainNode } from '$lib/types/train';

export const EVENT_ICON: Record<RailEventType, string> = {
	line_failure: '⚡',
	derailment: '🚨',
	speed_restriction: '🐢',
	signal_failure: '🚦'
};

export const EVENT_LABEL_KEY: Record<RailEventType, TranslationKey> = {
	line_failure: 'label.event.line_failure',
	derailment: 'label.event.derailment',
	speed_restriction: 'label.event.speed_restriction',
	signal_failure: 'label.event.signal_failure'
};

export function trainStatusLabel(status: string, t: Translator) {
	if (status === 'running') return t('label.trainStatus.running');
	if (status === 'dwelling') return t('label.trainStatus.dwelling');
	if (status === 'waiting') return t('label.trainStatus.waiting');
	if (status === 'derailed') return t('label.trainStatus.derailed');
	return status;
}

export function trainTypeLabel(type: string, t: Translator) {
	if (type === 'IC') return t('label.trainType.IC');
	if (type === 'REGIONAL') return t('label.trainType.REGIONAL');
	if (type === 'FREIGHT') return t('label.trainType.FREIGHT');
	return type;
}

export function directionStatusLabel(status: string, t: Translator) {
	if (status === 'blocked') return t('label.direction.blocked');
	if (status === 'restricted') return t('label.direction.restricted');
	return t('label.direction.active');
}

export function formatStationType(type: string, t: Translator) {
	if (type === 'węzeł') return t('label.stationType.hub');
	if (type === 'końcowa') return t('label.stationType.terminus');
	if (type === 'przelotowa') return t('label.stationType.through');
	return type.charAt(0).toUpperCase() + type.slice(1);
}

export function eventLabel(type: RailEventType, t: Translator): string {
	return t(EVENT_LABEL_KEY[type]);
}

export function formatEventMessage(
	event: RailEventNode,
	t: Translator,
	stationName: (id: string | null) => string
): string {
	if (event.type === 'line_failure') {
		return t('event.message.line_failure', {
			from: stationName(event.fromStationId),
			to: stationName(event.toStationId)
		});
	}
	if (event.type === 'derailment') {
		return t('event.message.derailment', {
			train: event.trainId ?? '—',
			from: stationName(event.fromStationId),
			to: stationName(event.toStationId)
		});
	}
	if (event.type === 'speed_restriction') {
		return t('event.message.speed_restriction', {
			speed: event.restrictedVmax ?? '—',
			from: stationName(event.fromStationId),
			to: stationName(event.toStationId)
		});
	}
	return t('event.message.signal_failure', { station: stationName(event.stationId) });
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
