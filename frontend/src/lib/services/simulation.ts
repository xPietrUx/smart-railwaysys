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

/** Ustawia mnożnik tempa symulacji (dozwolone: 0.5, 1, 1.5, 2). */
export async function setSimulationSpeed(
	fetchFn: typeof fetch,
	baseUrl: string,
	speed: number
): Promise<void> {
	const response = await fetchFn(`${baseUrl}/api/simulation/speed`, {
		method: 'POST',
		headers: { 'Content-Type': 'application/json' },
		body: JSON.stringify({ speed })
	});
	if (!response.ok) {
		throw new Error(await readApiError(response));
	}
}
