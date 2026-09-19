import { redirect } from '@sveltejs/kit';
import { handleLogin, handleRegister, setGuestSession } from '$lib/server/auth';
import type { PageServerLoad, Actions } from './$types';

export const load: PageServerLoad = ({ cookies }) => {
	return {
		authenticated: Boolean(cookies.get('srs_session'))
	};
};

export const actions: Actions = {
	login: handleLogin,
	register: handleRegister,
	guest: ({ cookies }) => {
		setGuestSession(cookies);
		redirect(303, '/panel');
	}
};