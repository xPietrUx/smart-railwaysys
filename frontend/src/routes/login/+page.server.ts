import { fail, redirect } from '@sveltejs/kit';
import { authApiUrl, setGuestSession, setSession } from '$lib/server/auth';

export const load = ({ cookies }) => {
	// Tylko realnie zalogowany użytkownik jest odsyłany do panelu. Gość musi móc
	// wejść na formularz logowania, żeby „awansować” na konto.
	if (cookies.get('srs_session')) redirect(303, '/panel');
};

export const actions = {
	login: async ({ request, cookies, url }) => {
		const form = await request.formData();
		const email = String(form.get('email') || '').trim();
		const password = String(form.get('password') || '');
		let response: Response;
		try {
			response = await fetch(`${authApiUrl()}/api/auth/login`, {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({ email, password })
			});
		} catch {
			return fail(503, { email, error: 'Nie udało się połączyć z systemem. Spróbuj ponownie.' });
		}
		const body = await response.json().catch(() => ({}));
		if (!response.ok)
			return fail(response.status, { email, error: body.detail || 'Logowanie nie powiodło się.' });
		setSession(cookies, body.access_token);
		const next = url.searchParams.get('next');
		redirect(303, next?.startsWith('/') && !next.startsWith('//') ? next : '/panel');
	},
	guest: ({ cookies }) => {
		setGuestSession(cookies);
		redirect(303, '/panel');
	}
};
