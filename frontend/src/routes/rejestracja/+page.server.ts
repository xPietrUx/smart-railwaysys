import { redirect } from '@sveltejs/kit';
import { handleLogin, handleRegister, setGuestSession } from '$lib/server/auth';

export const load = ({ cookies }) => {
    // Gość (tylko ciasteczko srs_guest) musi móc wejść na rejestrację, żeby założyć
    // konto — odsyłamy do panelu wyłącznie realnie zalogowanego użytkownika.
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
