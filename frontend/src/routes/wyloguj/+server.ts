import { redirect } from '@sveltejs/kit';

export const POST = ({ cookies }) => {
	cookies.delete('srs_session', { path: '/' });
	cookies.delete('srs_guest', { path: '/' });
	redirect(303, '/');
};

export const GET = () => {
	// Ochrona przed CSRF logout: GET nie usuwa sesji użytkownika
	redirect(303, '/');
};
