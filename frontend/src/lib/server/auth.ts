import { env as privateEnv } from '$env/dynamic/private';
import { fail, redirect } from '@sveltejs/kit';
import type { Cookies, RequestEvent } from '@sveltejs/kit';

export const authApiUrl = () => privateEnv.API_INTERNAL_URL || 'http://localhost:8000';

// Backend (FastAPI/Pydantic) na błąd walidacji (422) odpowiada `detail` jako
// tablicą obiektów {loc, msg}, nie stringiem — bez tego mapowania użytkownik
// dostawał ogólne "nie udało się", nie wiedząc np. że hasło jest za krótkie.
function friendlyValidationMessage(detail: unknown, fallback: string): string {
	if (typeof detail === 'string') return detail;
	if (!Array.isArray(detail) || detail.length === 0) return fallback;

	const fieldMessages: Record<string, string> = {
		email: 'Podaj poprawny adres e-mail (min. 3 znaki).',
		password: 'Hasło musi mieć od 8 do 128 znaków.'
	};

	const messages = detail
		.map((item) => (item && Array.isArray(item.loc) ? item.loc[item.loc.length - 1] : undefined))
		.filter((field): field is string => typeof field === 'string')
		.map((field) => fieldMessages[field])
		.filter((message): message is string => Boolean(message));

	return messages.length ? [...new Set(messages)].join(' ') : fallback;
}

export function setSession(cookies: Cookies, token: string) {
	cookies.delete('srs_guest', { path: '/' });
	cookies.set('srs_session', token, {
		path: '/',
		httpOnly: true,
		sameSite: 'lax',
		secure: process.env.NODE_ENV === 'production',
		maxAge: 60 * 60 * 24 * 7
	});
}

export function setGuestSession(cookies: Cookies) {
	cookies.delete('srs_session', { path: '/' });
	cookies.set('srs_guest', '1', {
		path: '/',
		httpOnly: true,
		sameSite: 'lax',
		secure: process.env.NODE_ENV === 'production',
		maxAge: 60 * 60 * 8
	});
}

// AuthCard.svelte pozwala przełączać tryb logowanie/rejestracja bez zmiany
// adresu, więc każda strona, na której się pojawia (/, /login, /rejestracja),
// musi obsługiwać obie akcje — inaczej przełączenie trybu kończy się 404.
export async function handleLogin({ request, cookies, url }: RequestEvent) {
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

	if (!response.ok) {
		let errorMessage = typeof body.detail === 'string' ? body.detail : 'Logowanie nie powiodło się.';

		if ([400, 401, 404, 422].includes(response.status)) {
			errorMessage = 'Nie istnieje konto przypisane do podanego adresu e-mail lub podane hasło jest nieprawidłowe.';
		}

		return fail(400, { email, error: errorMessage });
	}

	setSession(cookies, body.access_token);
	const next = url.searchParams.get('next');
	redirect(303, next?.startsWith('/') && !next.startsWith('//') ? next : '/panel');
}

export async function handleRegister({ request, cookies }: RequestEvent) {
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
	if (!response.ok) {
		const errorMessage =
			response.status === 409
				? 'Konto z tym adresem e-mail już istnieje.'
				: friendlyValidationMessage(body.detail, 'Nie udało się utworzyć konta.');

		return fail(response.status, { email, error: errorMessage });
	}

	setSession(cookies, body.access_token);
	redirect(303, '/panel');
}
