import { env as privateEnv } from '$env/dynamic/private';
import { error, redirect } from '@sveltejs/kit';
import { env as publicEnv } from '$env/dynamic/public';
import { fetchNetworkGraph } from '$lib/services/network';
import { fetchEventsSnapshot, fetchTrainsSnapshot } from '$lib/services/live';

export const load = async ({ fetch, cookies }) => {
	const token = cookies.get('srs_session');
	const isGuest = cookies.get('srs_guest') === '1';
	if (!token && !isGuest) redirect(303, '/login?next=/panel');

	const apiBaseUrl = publicEnv.PUBLIC_API_BASE_URL || 'http://localhost:8000';

	const ssrBaseUrl = privateEnv.API_INTERNAL_URL || apiBaseUrl;
	let user = { id: 'guest', email: 'Gość', role: 'guest' };
	if (!isGuest) {
		const authResponse = await fetch(`${ssrBaseUrl}/api/auth/me`, {
			headers: { Authorization: `Bearer ${token}` }
		}).catch(() => null);
		if (!authResponse?.ok) {
			cookies.delete('srs_session', { path: '/' });
			redirect(303, '/login?next=/panel');
		}
		user = { ...(await authResponse.json()), role: 'admin' };
	}

	let initialData;
	try {
		initialData = await Promise.all([
			fetchNetworkGraph(fetch, ssrBaseUrl),
			fetchTrainsSnapshot(fetch, ssrBaseUrl),
			fetchEventsSnapshot(fetch, ssrBaseUrl)
		]);
	} catch (cause) {
		console.error('Nie udało się załadować danych panelu:', cause);
		error(503, 'Backend lub baza danych są chwilowo niedostępne.');
	}
	const [graph, trainsData, eventsData] = initialData;

	return {
		graph,
		user,
		apiBaseUrl,
		trains: trainsData.trains,
		events: eventsData.events,
		timestamp: trainsData.timestamp
	};
};
