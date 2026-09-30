import { json } from '@sveltejs/kit';
import { env as privateEnv } from '$env/dynamic/private';
import { env as publicEnv } from '$env/dynamic/public';
import type { RequestHandler } from './$types';

export const POST: RequestHandler = async ({ request, cookies, fetch }) => {
	const token = cookies.get('srs_session');
	if (!token) {
		return json({ detail: 'Brak autoryzacji.' }, { status: 401 });
	}

	const ssrBaseUrl = privateEnv.API_INTERNAL_URL || publicEnv.PUBLIC_API_BASE_URL;
	const body = await request.text();

	let response: Response;
	try {
		response = await fetch(`${ssrBaseUrl}/api/scenarios`, {
			method: 'POST',
			headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
			body
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
