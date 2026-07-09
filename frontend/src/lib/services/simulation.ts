import type { SimulationStateResponse, TrainCreateRequest, TrainState } from '$lib/types/simulation';

export async function fetchTrains(fetchFn: typeof fetch, baseUrl: string): Promise<SimulationStateResponse> {
	const res = await fetchFn(`${baseUrl}/api/simulation/trains`);
	if (!res.ok) throw new Error(`Błąd pobierania pociągów: ${res.status}`);
	return res.json();
}

export async function createTrain(
	fetchFn: typeof fetch,
	baseUrl: string,
	payload: TrainCreateRequest
): Promise<TrainState> {
	const res = await fetchFn(`${baseUrl}/api/simulation/trains`, {
		method: 'POST',
		headers: { 'Content-Type': 'application/json' },
		body: JSON.stringify(payload)
	});
	if (!res.ok) {
		const err = await res.json().catch(() => null);
		throw new Error(err?.detail || `Błąd tworzenia pociągu: ${res.status}`);
	}
	return res.json();
}

export async function spawnDemoTrains(
	fetchFn: typeof fetch,
	baseUrl: string
): Promise<SimulationStateResponse> {
	const res = await fetchFn(`${baseUrl}/api/simulation/trains/demo`, { method: 'POST' });
	if (!res.ok) throw new Error(`Błąd uruchamiania zestawu demonstracyjnego: ${res.status}`);
	return res.json();
}

export async function tickSimulation(
	fetchFn: typeof fetch,
	baseUrl: string,
	deltaSec = 1.0,
	timeScale = 60.0
): Promise<SimulationStateResponse> {
	const res = await fetchFn(
		`${baseUrl}/api/simulation/tick?deltaSec=${deltaSec}&timeScale=${timeScale}`,
		{ method: 'POST' }
	);
	if (!res.ok) throw new Error(`Błąd kroku symulacji: ${res.status}`);
	return res.json();
}

export async function clearAllTrains(
	fetchFn: typeof fetch,
	baseUrl: string
): Promise<{ success: boolean; clearedCount: number }> {
	const res = await fetchFn(`${baseUrl}/api/simulation/trains`, { method: 'DELETE' });
	if (!res.ok) throw new Error(`Błąd czyszczenia pociągów: ${res.status}`);
	return res.json();
}
