import { redirect } from '@sveltejs/kit';
import { setGuestSession } from '$lib/server/auth';

export const load = ({ cookies }) => ({

	authenticated: Boolean(cookies.get('srs_session'))
});

export const actions = {

	// „Zalogowany” = realna sesja. Gość (samo srs_guest) nadal widzi na stronie
	// głównej przycisk logowania, żeby móc założyć/wejść na konto.
	authenticated: Boolean(cookies.get('srs_session'))
});

export const actions = {
	// Wejście gościa prosto ze strony głównej — ustawia sesję gościa i otwiera
	// symulację w trybie tylko do podglądu.
	guest: ({ cookies }) => {
		setGuestSession(cookies);
		redirect(303, '/panel');
	}
};
