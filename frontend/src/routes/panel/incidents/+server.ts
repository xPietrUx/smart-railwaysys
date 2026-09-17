import { json } from '@sveltejs/kit';
import { env as privateEnv } from '$env/dynamic/private';
import { env as publicEnv } from '$env/dynamic/public';

// Token sesji leży w ciasteczku httpOnly, więc niedostępnym dla fetchy z
// przeglądarki — ten endpoint po stronie SSR doczytuje go z ciasteczka i
// dokleja jako Bearer, zanim przekaże żądanie do backendu (który wymaga
// autoryzacji dla tworzenia incydentów).
export const POST = async ({ request, cookies, fetch }) => {
	const token = cookies.get('srs_session');
	if (!token) {
		return json({ detail: 'Brak autoryzacji.' }, { status: 401 });
	}

	const ssrBaseUrl = privateEnv.API_INTERNAL_URL || publicEnv.PUBLIC_API_BASE_URL || 'http://localhost:8000';
	const body = await request.text();

	let response: Response;
	try {
		response = await fetch(`${ssrBaseUrl}/api/incidents`, {
			method: 'POST',
			headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
			body
		});
	} catch {
		return json({ detail: 'Nie udało się połączyć z systemem. Spróbuj ponownie.' }, { status: 503 });
	}

	const data = await response.text();
	return new Response(data, {
		status: response.status,
		headers: { 'Content-Type': 'application/json' }
	});
};
