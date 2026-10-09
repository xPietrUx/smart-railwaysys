import { readApiError } from '$lib/services/scenarios';

async function post(fetchFn: typeof fetch, url: string, body?: string): Promise<void> {
	const response = await fetchFn(url, {
		method: 'POST',
		headers: body ? { 'Content-Type': 'application/json' } : undefined,
		body
	});
	if (!response.ok) {
		throw new Error(await readApiError(response));
	}
}

export function pauseSimulation(fetchFn: typeof fetch, _baseUrl?: string): Promise<void> {
	return post(fetchFn, '/panel/simulation/pause');
}

export function resumeSimulation(fetchFn: typeof fetch, _baseUrl?: string): Promise<void> {
	return post(fetchFn, '/panel/simulation/resume');
}

/** Usuwa z sieci wszystkie pociągi bieżącego scenariusza. */
export function clearTrains(fetchFn: typeof fetch, _baseUrl?: string): Promise<void> {
	return post(fetchFn, '/panel/simulation/clear');
}

/** Ustawia mnożnik tempa symulacji (dozwolone: 0.5, 1, 1.5, 2). */
export async function setSimulationSpeed(
	fetchFn: typeof fetch,
	_baseUrl: string,
	speed: number
): Promise<void> {
	await post(fetchFn, '/panel/simulation/speed', JSON.stringify({ speed }));
}
