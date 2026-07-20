import { env } from '$env/dynamic/public';
import { fetchNetworkGraph } from '$lib/services/network';
import { fetchEventsSnapshot, fetchTrainsSnapshot } from '$lib/services/live';

const apiBaseUrl = env.PUBLIC_API_BASE_URL || 'http://localhost:8000';

export const load = async ({ fetch }) => {
	const [graph, trainsData, eventsData] = await Promise.all([
		fetchNetworkGraph(fetch, apiBaseUrl),
		fetchTrainsSnapshot(fetch, apiBaseUrl),
		fetchEventsSnapshot(fetch, apiBaseUrl)
	]);

	return {
		graph,
		apiBaseUrl,
		trains: trainsData.trains,
		events: eventsData.events,
		timestamp: trainsData.timestamp
	};
};
