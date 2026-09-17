import { fail, redirect } from '@sveltejs/kit';
import { authApiUrl, setGuestSession, setSession } from '$lib/server/auth';

export const load = ({ cookies }) => {
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
        
        if (!response.ok) {
            let errorMessage = body.detail || 'Logowanie nie powiodło się.';
            
            if (response.status === 404 || response.status === 400 || response.status === 401) {
                errorMessage = 'Nie istnieje konto przypisane do podanego adresu e-mail lub podane hasło jest nieprawidłowe.';
            }

            return fail(400, { email, error: errorMessage });
        }
        
        setSession(cookies, body.access_token);
        const next = url.searchParams.get('next');
        redirect(303, next?.startsWith('/') && !next.startsWith('//') ? next : '/panel');
    },
    guest: ({ cookies }) => {
        setGuestSession(cookies);
        redirect(303, '/panel');
    }
};