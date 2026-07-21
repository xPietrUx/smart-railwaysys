import { env as privateEnv } from '$env/dynamic/private';
import { env as publicEnv } from '$env/dynamic/public';
import { fetchNetworkGraph } from '$lib/services/network';
import { fetchEventsSnapshot, fetchTrainsSnapshot } from '$lib/services/live';

export const load = async ({ fetch }) => {
	// Adres backendu widziany przez przeglądarkę (WebSocket + polling fallback).
	const apiBaseUrl = publicEnv.PUBLIC_API_BASE_URL || 'http://localhost:8000';
	// Adres backendu widziany z serwera SSR. W Dockerze przeglądarka nie zna hosta
	// "backend", a kontener frontendu nie zawsze zna "localhost" hosta — dlatego
	// te dwa adresy muszą być rozdzielone.
	const ssrBaseUrl = privateEnv.API_INTERNAL_URL || apiBaseUrl;

	const [graph, trainsData, eventsData] = await Promise.all([
		fetchNetworkGraph(fetch, ssrBaseUrl),
		fetchTrainsSnapshot(fetch, ssrBaseUrl),
		fetchEventsSnapshot(fetch, ssrBaseUrl)
	]);

	return {
		graph,
		apiBaseUrl,
		trains: trainsData.trains,
		events: eventsData.events,
		timestamp: trainsData.timestamp
	};
};
