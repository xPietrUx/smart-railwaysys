import type { NetworkGraph } from '$lib/types/network';

export async function fetchNetworkGraph(fetchFn: typeof fetch, baseUrl: string): Promise<NetworkGraph> {
	const response = await fetchFn(`${baseUrl}/api/network`);
	if (!response.ok) {
		throw new Error(`API zwróciło ${response.status}`);
	}

	return response.json();
}

export async function updateSegmentStatus(
	fetchFn: typeof fetch,
	baseUrl: string,
	segmentId: string,
	status: 'active' | 'blocked'
): Promise<{ segmentId: string; status: string; success: boolean }> {
	const response = await fetchFn(`${baseUrl}/api/network/segments/${segmentId}/status`, {
		method: 'PATCH',
		headers: { 'Content-Type': 'application/json' },
		body: JSON.stringify({ status })
	});
	if (!response.ok) {
		throw new Error(`Błąd aktualizacji statusu toru: ${response.status}`);
	}
	return response.json();
}

export async function resetAllSegmentsStatus(
	fetchFn: typeof fetch,
	baseUrl: string
): Promise<{ success: boolean; resetCount: number }> {
	const response = await fetchFn(`${baseUrl}/api/network/segments/reset-status`, {
		method: 'POST'
	});
	if (!response.ok) {
		throw new Error(`Błąd resetowania statusu torów: ${response.status}`);
	}
	return response.json();
}


