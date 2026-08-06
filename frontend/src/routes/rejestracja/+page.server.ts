import { fail, redirect } from '@sveltejs/kit';
import { authApiUrl, setGuestSession, setSession } from '$lib/server/auth';

export const load = ({ cookies }) => {
	if (cookies.get('srs_session') || cookies.get('srs_guest')) redirect(303, '/panel');
};

export const actions = {
	register: async ({ request, cookies }) => {
		const form = await request.formData();
		const email = String(form.get('email') || '').trim();
		const password = String(form.get('password') || '');
		if (password !== String(form.get('passwordConfirm') || ''))
			return fail(400, { email, error: 'Hasła nie są takie same.' });
		let response: Response;
		try {
			response = await fetch(`${authApiUrl()}/api/auth/register`, {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({ email, password })
			});
		} catch {
			return fail(503, { email, error: 'Nie udało się połączyć z systemem. Spróbuj ponownie.' });
		}
		const body = await response.json().catch(() => ({}));
		if (!response.ok)
			return fail(response.status, {
				email,
				error: body.detail || 'Nie udało się utworzyć konta.'
			});
		setSession(cookies, body.access_token);
		redirect(303, '/panel');
	},
	guest: ({ cookies }) => {
		setGuestSession(cookies);
		redirect(303, '/panel');
	}
};
