import { env as privateEnv } from '$env/dynamic/private';
import type { Cookies } from '@sveltejs/kit';

export const authApiUrl = () => privateEnv.API_INTERNAL_URL || 'http://localhost:8000';

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
