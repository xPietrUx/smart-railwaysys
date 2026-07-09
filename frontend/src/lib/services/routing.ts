import type { FastestRouteResponse } from '$lib/types/routing';

export async function fetchFastestRoute(
	fetchFn: typeof fetch,
	baseUrl: string,
	fromStation: string,
	toStation: string,
	trainType: string = 'IC',
	customVmax?: number
): Promise<FastestRouteResponse> {
	const params = new URLSearchParams({
		from_station: fromStation,
		to_station: toStation,
		train_type: trainType
	});
	if (customVmax) {
		params.set('custom_vmax', customVmax.toString());
	}

	const response = await fetchFn(`${baseUrl}/api/route/fastest?${params.toString()}`);
	if (!response.ok) {
		throw new Error(`API routingu zwróciło błąd ${response.status}`);
	}

	return response.json();
}
