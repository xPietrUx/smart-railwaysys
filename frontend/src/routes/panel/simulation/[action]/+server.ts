import { json } from '@sveltejs/kit';
import { env as privateEnv } from '$env/dynamic/private';
import { env as publicEnv } from '$env/dynamic/public';
import type { RequestHandler } from './$types';

export const POST: RequestHandler = async ({ params, request, cookies, fetch }) => {
	const token = cookies.get('srs_session');
	if (!token) {
		return json({ detail: 'Brak autoryzacji.' }, { status: 401 });
	}

	const allowedActions = ['pause', 'resume', 'speed', 'clear'];
	const action = params.action;
	if (!allowedActions.includes(action)) {
		return json({ detail: 'Nieznana akcja symulacji.' }, { status: 404 });
	}

	const ssrBaseUrl = privateEnv.API_INTERNAL_URL || publicEnv.PUBLIC_API_BASE_URL;
	const backendPath = action === 'clear' ? '/api/simulation/trains/clear' : `/api/simulation/${action}`;

	const contentType = request.headers.get('content-type');
	const body = contentType?.includes('application/json') ? await request.text() : undefined;

	let response: Response;
	try {
		response = await fetch(`${ssrBaseUrl}${backendPath}`, {
			method: 'POST',
			headers: {
				...(body ? { 'Content-Type': 'application/json' } : {}),
				Authorization: `Bearer ${token}`
			},
			body
		});
	} catch {
		return json(
			{ detail: 'Nie udało się połączyć z backendem symulacji.' },
			{ status: 503 }
		);
	}

	const data = await response.text();
	return new Response(data, {
		status: response.status,
		headers: { 'Content-Type': 'application/json' }
	});
};
