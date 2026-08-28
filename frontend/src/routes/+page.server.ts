import { redirect } from '@sveltejs/kit';
import { setGuestSession } from '$lib/server/auth';

export const load = ({ cookies }) => ({

	authenticated: Boolean(cookies.get('srs_session'))
});

export const actions = {

	guest: ({ cookies }) => {
		setGuestSession(cookies);
		redirect(303, '/panel');
	}
};
