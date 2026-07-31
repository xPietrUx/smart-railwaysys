import type {
	ActiveScenarioInfo,
	Scenario,
	ScenariosResponse,
	TrainPlan
} from '$lib/types/scenario';

export type ScenarioPayload = {
	name: string;
	description: string;
	trains: TrainPlan[];
};

/** Wyciąga czytelny komunikat z odpowiedzi FastAPI (detail: string | lista błędów). */
export async function readApiError(response: Response): Promise<string> {
	try {
		const data = await response.json();
		if (typeof data.detail === 'string') return data.detail;
		if (Array.isArray(data.detail)) {
			return data.detail
				.map((item: { msg?: string }) => item.msg)
				.filter(Boolean)
				.join('; ');
		}
	} catch {
		// odpowiedź bez JSON-a — zostaje komunikat ogólny
	}
	return `Błąd API (${response.status})`;
}

export async function fetchScenarios(fetchFn: typeof fetch, baseUrl: string): Promise<Scenario[]> {
	const response = await fetchFn(`${baseUrl}/api/scenarios`);
	if (!response.ok) {
		throw new Error(await readApiError(response));
	}
	const data: ScenariosResponse = await response.json();
	return data.scenarios;
}

export async function createScenario(
	fetchFn: typeof fetch,
	baseUrl: string,
	payload: ScenarioPayload
): Promise<Scenario> {
	const response = await fetchFn(`${baseUrl}/api/scenarios`, {
		method: 'POST',
		headers: { 'Content-Type': 'application/json' },
		body: JSON.stringify(payload)
	});
	if (!response.ok) {
		throw new Error(await readApiError(response));
	}
	return response.json();
}

export async function updateScenario(
	fetchFn: typeof fetch,
	baseUrl: string,
	scenarioId: string,
	payload: ScenarioPayload
): Promise<Scenario> {
	const response = await fetchFn(`${baseUrl}/api/scenarios/${encodeURIComponent(scenarioId)}`, {
		method: 'PUT',
		headers: { 'Content-Type': 'application/json' },
		body: JSON.stringify(payload)
	});
	if (!response.ok) {
		throw new Error(await readApiError(response));
	}
	return response.json();
}

export async function deleteScenario(
	fetchFn: typeof fetch,
	baseUrl: string,
	scenarioId: string
): Promise<void> {
	const response = await fetchFn(`${baseUrl}/api/scenarios/${encodeURIComponent(scenarioId)}`, {
		method: 'DELETE'
	});
	if (!response.ok) {
		throw new Error(await readApiError(response));
	}
}

export async function runScenario(
	fetchFn: typeof fetch,
	baseUrl: string,
	scenarioId: string
): Promise<ActiveScenarioInfo> {
	const response = await fetchFn(`${baseUrl}/api/scenarios/${encodeURIComponent(scenarioId)}/run`, {
		method: 'POST'
	});
	if (!response.ok) {
		throw new Error(await readApiError(response));
	}
	return response.json();
}
