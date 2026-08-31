import { redirect } from '@sveltejs/kit';
import { setGuestSession } from '$lib/server/auth';
import type { PageServerLoad, Actions } from './$types';

export const load: PageServerLoad = ({ cookies }) => {
	return {
		authenticated: Boolean(cookies.get('srs_session'))
	};
};

export const actions: Actions = {
	guest: ({ cookies }) => {
		setGuestSession(cookies);
		redirect(303, '/panel');
	}
};