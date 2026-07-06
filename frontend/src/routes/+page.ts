import { env } from '$env/dynamic/public';
import { fetchNetworkGraph } from '$lib/services/network';

const apiBaseUrl = env.PUBLIC_API_BASE_URL || 'http://localhost:8000';

export const load = async ({ fetch }) => {
	const graph = await fetchNetworkGraph(fetch, apiBaseUrl);
	return { graph };
};
