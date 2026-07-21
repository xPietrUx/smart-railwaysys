import type { RailEventNode } from '$lib/types/event';
import type { DirectionalState, TrackSegment } from '$lib/types/network';

// Musi odpowiadać SIM_SPEED_RESTRICTION_FACTOR w backend/app/core/config.py.
const RESTRICTION_FACTOR = 0.5;

type Direction = 'forward' | 'backward';

function freshState(): DirectionalState {
	return { status: 'active', restrictedVmax: null, activeEventId: null };
}

/** Kierunki odcinka dotknięte zdarzeniem — odwzorowanie _expand_for_track_count
 *  z backendu: jednotorowy odcinek blokuje oba kierunki, dwutorowy tylko ten
 *  wskazany przez fromStationId zdarzenia. */
function affectedDirections(segment: TrackSegment, event: RailEventNode): Direction[] {
	if (segment.railTracks <= 1) return ['forward', 'backward'];
	if (event.fromStationId === segment.source) return ['forward'];
	if (event.fromStationId === segment.target) return ['backward'];
	return ['forward', 'backward'];
}

/**
 * Wylicza bieżący stan kierunkowy każdego odcinka wyłącznie z listy aktywnych
 * zdarzeń. Graf sieci jest ładowany raz przy starcie strony, a jego stany
 * torów są migawkowe — dzięki temu przeliczeniu mapa reaguje na incydenty
 * na żywo, bez ponownego pobierania grafu.
 */
export function applyEventsToSegments(
	segments: TrackSegment[],
	events: RailEventNode[]
): TrackSegment[] {
	const stateBySegment = new Map<
		string,
		{ forward: DirectionalState; backward: DirectionalState }
	>();
	for (const segment of segments) {
		stateBySegment.set(segment.segmentId, { forward: freshState(), backward: freshState() });
	}

	const segmentById = new Map(segments.map((segment) => [segment.segmentId, segment]));
	const segmentsByStation = new Map<string, TrackSegment[]>();
	for (const segment of segments) {
		for (const stationId of [segment.source, segment.target]) {
			const list = segmentsByStation.get(stationId) ?? [];
			list.push(segment);
			segmentsByStation.set(stationId, list);
		}
	}

	function apply(
		segment: TrackSegment,
		directions: Direction[],
		next: DirectionalState,
		overrideRestricted: boolean
	) {
		const entry = stateBySegment.get(segment.segmentId);
		if (!entry) return;
		for (const direction of directions) {
			const current = entry[direction];
			if (current.status === 'blocked') continue;
			if (current.status === 'restricted' && !overrideRestricted) continue;
			entry[direction] = next;
		}
	}

	const active = events.filter((event) => event.status === 'active');
	// Najpierw restrykcje, potem blokady — blokada ma zawsze pierwszeństwo.
	for (const event of active) {
		if (event.type === 'speed_restriction' && event.segmentId) {
			const segment = segmentById.get(event.segmentId);
			if (!segment) continue;
			apply(
				segment,
				affectedDirections(segment, event),
				{
					status: 'restricted',
					restrictedVmax: event.restrictedVmax,
					activeEventId: event.id
				},
				false
			);
		} else if (event.type === 'signal_failure' && event.stationId) {
			for (const segment of segmentsByStation.get(event.stationId) ?? []) {
				apply(
					segment,
					['forward', 'backward'],
					{
						status: 'restricted',
						restrictedVmax: Math.max(20, Math.round(segment.vmax * RESTRICTION_FACTOR)),
						activeEventId: event.id
					},
					false
				);
			}
		}
	}
	for (const event of active) {
		if ((event.type !== 'line_failure' && event.type !== 'derailment') || !event.segmentId)
			continue;
		const segment = segmentById.get(event.segmentId);
		if (!segment) continue;
		apply(
			segment,
			affectedDirections(segment, event),
			{ status: 'blocked', restrictedVmax: null, activeEventId: event.id },
			true
		);
	}

	return segments.map((segment) => {
		const entry = stateBySegment.get(segment.segmentId);
		return entry ? { ...segment, forward: entry.forward, backward: entry.backward } : segment;
	});
}
