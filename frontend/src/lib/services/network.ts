import type { NetworkGraph } from '$lib/types/network';

export async function fetchNetworkGraph(fetchFn: typeof fetch, baseUrl: string): Promise<NetworkGraph> {
	const response = await fetchFn(`${baseUrl}/api/network`);
	if (!response.ok) {
		throw new Error(`API zwróciło ${response.status}`);
	}

	return response.json();
}
