import { env as privateEnv } from '$env/dynamic/private';
import { error, redirect } from '@sveltejs/kit';
import { env as publicEnv } from '$env/dynamic/public';
import { fetchNetworkGraph } from '$lib/services/network';
import { fetchEventsSnapshot, fetchTrainsSnapshot } from '$lib/services/live';

export const load = async ({ fetch, cookies }) => {
	const token = cookies.get('srs_session');
	const isGuest = cookies.get('srs_guest') === '1';
	if (!token && !isGuest) redirect(303, '/login?next=/panel');
	// Adres backendu widziany przez przeglądarkę (WebSocket + polling fallback).
	const apiBaseUrl = publicEnv.PUBLIC_API_BASE_URL || 'http://localhost:8000';
	// Adres backendu widziany z serwera SSR. W Dockerze przeglądarka nie zna hosta
	// "backend", a kontener frontendu nie zawsze zna "localhost" hosta — dlatego
	// te dwa adresy muszą być rozdzielone.
	const ssrBaseUrl = privateEnv.API_INTERNAL_URL || apiBaseUrl;

	let user: { id: string; email: string; role: string; permissions: string[] } | undefined;

	// Prawdziwa sesja ma pierwszeństwo nad trybem gościa — inaczej zalogowany
	// admin z zalegającym ciasteczkiem gościa byłby traktowany jak gość.
	if (token) {
		const authResponse = await fetch(`${ssrBaseUrl}/api/auth/me`, {
			headers: { Authorization: `Bearer ${token}` }
		}).catch(() => null);
		if (authResponse?.ok) {
			user = await authResponse.json();
			cookies.delete('srs_guest', { path: '/' }); // sprzątamy zalegające ciasteczko gościa
		} else {
			cookies.delete('srs_session', { path: '/' });
			if (!isGuest) redirect(303, '/login?next=/panel');
		}
	}

	if (!user) {
		// Gość (albo sesja wygasła, ale zostało ważne ciasteczko gościa). Uprawnienia
		// gościa pobieramy z backendu, więc edycja roli „gość” w panelu administratora
		// od razu zmienia to, co gość widzi (fallback: sam podgląd).
		let permissions = ['simulation.view'];
		const guestResponse = await fetch(`${ssrBaseUrl}/api/auth/guest`).catch(() => null);
		if (guestResponse?.ok) {
			const body = await guestResponse.json();
			if (Array.isArray(body.permissions)) permissions = body.permissions;
		}
		user = { id: 'guest', email: 'Gość', role: 'guest', permissions };
	}

	let initialData;
	try {
		initialData = await Promise.all([
			fetchNetworkGraph(fetch, ssrBaseUrl),
			fetchTrainsSnapshot(fetch, ssrBaseUrl),
			fetchEventsSnapshot(fetch, ssrBaseUrl)
		]);
	} catch (cause) {
		console.error('Nie udało się załadować danych panelu:', cause);
		error(503, 'Backend lub baza danych są chwilowo niedostępne.');
	}
	const [graph, trainsData, eventsData] = initialData;

	return {
		graph,
		user,
		apiBaseUrl,
		trains: trainsData.trains,
		events: eventsData.events,
		timestamp: trainsData.timestamp
	};
};
