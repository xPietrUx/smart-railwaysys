import { readApiError } from '$lib/services/scenarios';

async function post(fetchFn: typeof fetch, url: string): Promise<void> {
	const response = await fetchFn(url, { method: 'POST' });
	if (!response.ok) {
		throw new Error(await readApiError(response));
	}
}

export function pauseSimulation(fetchFn: typeof fetch, baseUrl: string): Promise<void> {
	return post(fetchFn, `${baseUrl}/api/simulation/pause`);
}

export function resumeSimulation(fetchFn: typeof fetch, baseUrl: string): Promise<void> {
	return post(fetchFn, `${baseUrl}/api/simulation/resume`);
}

/** Usuwa z sieci wszystkie pociągi bieżącego scenariusza. */
export function clearTrains(fetchFn: typeof fetch, baseUrl: string): Promise<void> {
	return post(fetchFn, `${baseUrl}/api/simulation/trains/clear`);
}
