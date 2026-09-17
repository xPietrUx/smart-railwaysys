import type { RailEventNode, RailEventType } from '$lib/types/event';
import { readApiError } from './scenarios';

export type IncidentCreatePayload = {
	type: RailEventType;
	targetId: string;
};

// Woła własny endpoint SSR (/panel/incidents), nie backend bezpośrednio —
// backend wymaga Bearer tokenu z ciasteczka httpOnly, którego przeglądarka
// nie może odczytać ani wysłać do innego originu (patrz +server.ts obok).
export async function createIncident(
	fetchFn: typeof fetch,
	payload: IncidentCreatePayload
): Promise<RailEventNode> {
	const response = await fetchFn('/panel/incidents', {
		method: 'POST',
		headers: { 'Content-Type': 'application/json' },
		body: JSON.stringify(payload)
	});
	if (!response.ok) {
		throw new Error(await readApiError(response));
	}
	return response.json();
}
