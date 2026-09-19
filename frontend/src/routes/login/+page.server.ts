import { redirect } from '@sveltejs/kit';
import { handleLogin, handleRegister, setGuestSession } from '$lib/server/auth';

export const load = ({ cookies }) => {
    if (cookies.get('srs_session')) redirect(303, '/panel');
};

export const actions = {
    login: handleLogin,
    register: handleRegister,
    guest: ({ cookies }) => {
        setGuestSession(cookies);
        redirect(303, '/panel');
    }
};
