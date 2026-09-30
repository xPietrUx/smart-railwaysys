import { json } from '@sveltejs/kit';
import { env as privateEnv } from '$env/dynamic/private';
import { env as publicEnv } from '$env/dynamic/public';
import type { RequestHandler } from './$types';

export const POST: RequestHandler = async ({ params, cookies, fetch }) => {
	const token = cookies.get('srs_session');
	if (!token) {
		return json({ detail: 'Brak autoryzacji.' }, { status: 401 });
	}

	const ssrBaseUrl = privateEnv.API_INTERNAL_URL || publicEnv.PUBLIC_API_BASE_URL;

	let response: Response;
	try {
		response = await fetch(`${ssrBaseUrl}/api/scenarios/${encodeURIComponent(params.id)}/run`, {
			method: 'POST',
			headers: { Authorization: `Bearer ${token}` }
		});
	} catch {
		return json(
			{ detail: 'Nie udało się połączyć z backendem scenariuszy.' },
			{ status: 503 }
		);
	}

	const data = await response.text();
	return new Response(data, {
		status: response.status,
		headers: { 'Content-Type': 'application/json' }
	});
};
