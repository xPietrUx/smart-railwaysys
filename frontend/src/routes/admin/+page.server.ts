import { fail, redirect } from '@sveltejs/kit';
import type { Cookies } from '@sveltejs/kit';
import { authApiUrl } from '$lib/server/auth';

export type AdminUser = {
	id: string;
	email: string;
	role: string;
	active: boolean;
	created_at: number | null;
};
export type Role = { name: string; label: string; permissions: string[]; is_system: boolean };
export type Permission = { key: string; label: string };

const jsonHeaders = (token: string) => ({
	Authorization: `Bearer ${token}`,
	'Content-Type': 'application/json'
});

/** Wyciąga czytelny komunikat błędu z odpowiedzi FastAPI. */
async function readError(response: Response, fallback: string): Promise<string> {
	const body = await response.json().catch(() => ({}));
	if (typeof body.detail === 'string') return body.detail;
	if (Array.isArray(body.detail))
		return (
			body.detail
				.map((item: { msg?: string }) => item.msg)
				.filter(Boolean)
				.join('; ') || fallback
		);
	return fallback;
}

function requireToken(cookies: Cookies): string {
	const token = cookies.get('srs_session');
	if (!token) redirect(303, '/login?next=/admin');
	return token;
}

export const load = async ({ fetch, cookies }) => {
	const token = requireToken(cookies);
	const base = authApiUrl();

	const meResponse = await fetch(`${base}/api/auth/me`, {
		headers: { Authorization: `Bearer ${token}` }
	}).catch(() => null);
	if (!meResponse?.ok) {
		cookies.delete('srs_session', { path: '/' });
		redirect(303, '/login?next=/admin');
	}
	const me = await meResponse.json();
	// Bez uprawnienia zarządzania użytkownikami panel jest niedostępny.
	if (!me.permissions?.includes('users.manage')) redirect(303, '/panel');

	const [usersResponse, rolesResponse, permsResponse] = await Promise.all([
		fetch(`${base}/api/admin/users`, { headers: { Authorization: `Bearer ${token}` } }),
		fetch(`${base}/api/admin/roles`, { headers: { Authorization: `Bearer ${token}` } }),
		fetch(`${base}/api/admin/permissions`, { headers: { Authorization: `Bearer ${token}` } })
	]);

	const users: AdminUser[] = usersResponse.ok ? await usersResponse.json() : [];
	const roles: Role[] = rolesResponse.ok ? await rolesResponse.json() : [];
	const permissions: Permission[] = permsResponse.ok ? await permsResponse.json() : [];

	return {
		me,
		users,
		roles,
		permissions,
		canManageRoles: Boolean(me.permissions?.includes('roles.manage'))
	};
};

export const actions = {
	createUser: async ({ request, cookies, fetch }) => {
		const token = requireToken(cookies);
		const form = await request.formData();
		const email = String(form.get('email') || '').trim();
		const password = String(form.get('password') || '');
		const role = String(form.get('role') || 'user');
		const response = await fetch(`${authApiUrl()}/api/admin/users`, {
			method: 'POST',
			headers: jsonHeaders(token),
			body: JSON.stringify({ email, password, role })
		});
		if (!response.ok)
			return fail(response.status, {
				scope: 'createUser',
				error: await readError(response, 'Nie udało się dodać użytkownika.')
			});
		return { scope: 'createUser', message: `Dodano użytkownika ${email}.` };
	},

	updateUser: async ({ request, cookies, fetch }) => {
		const token = requireToken(cookies);
		const form = await request.formData();
		const id = String(form.get('id') || '');
		const email = String(form.get('email') || '').trim();
		const role = String(form.get('role') || '');
		const active = form.get('active') === 'true';
		const response = await fetch(`${authApiUrl()}/api/admin/users/${encodeURIComponent(id)}`, {
			method: 'PATCH',
			headers: jsonHeaders(token),
			body: JSON.stringify({ email, role, active })
		});
		if (!response.ok)
			return fail(response.status, {
				scope: 'user',
				id,
				error: await readError(response, 'Nie udało się zapisać użytkownika.')
			});
		return { scope: 'user', id, message: 'Zapisano zmiany.' };
	},

	resetPassword: async ({ request, cookies, fetch }) => {
		const token = requireToken(cookies);
		const form = await request.formData();
		const id = String(form.get('id') || '');
		const password = String(form.get('password') || '');
		const response = await fetch(
			`${authApiUrl()}/api/admin/users/${encodeURIComponent(id)}/password`,
			{ method: 'POST', headers: jsonHeaders(token), body: JSON.stringify({ password }) }
		);
		if (!response.ok)
			return fail(response.status, {
				scope: 'user',
				id,
				error: await readError(response, 'Nie udało się zmienić hasła.')
			});
		return { scope: 'user', id, message: 'Hasło zmienione.' };
	},

	deleteUser: async ({ request, cookies, fetch }) => {
		const token = requireToken(cookies);
		const form = await request.formData();
		const id = String(form.get('id') || '');
		const response = await fetch(`${authApiUrl()}/api/admin/users/${encodeURIComponent(id)}`, {
			method: 'DELETE',
			headers: { Authorization: `Bearer ${token}` }
		});
		if (!response.ok)
			return fail(response.status, {
				scope: 'user',
				id,
				error: await readError(response, 'Nie udało się usunąć użytkownika.')
			});
		return { scope: 'user', message: 'Użytkownik usunięty.' };
	},

	createRole: async ({ request, cookies, fetch }) => {
		const token = requireToken(cookies);
		const form = await request.formData();
		const name = String(form.get('name') || '').trim();
		const label = String(form.get('label') || '').trim();
		const permissions = form.getAll('permissions').map(String);
		const response = await fetch(`${authApiUrl()}/api/admin/roles`, {
			method: 'POST',
			headers: jsonHeaders(token),
			body: JSON.stringify({ name, label, permissions })
		});
		if (!response.ok)
			return fail(response.status, {
				scope: 'createRole',
				error: await readError(response, 'Nie udało się dodać roli.')
			});
		const role: Role = await response.json();
		return { scope: 'createRole', message: `Dodano rolę ${label || name}.`, role };
	},

	updateRole: async ({ request, cookies, fetch }) => {
		const token = requireToken(cookies);
		const form = await request.formData();
		const name = String(form.get('name') || '');
		const label = String(form.get('label') || '').trim();
		const permissions = form.getAll('permissions').map(String);
		const response = await fetch(`${authApiUrl()}/api/admin/roles/${encodeURIComponent(name)}`, {
			method: 'PATCH',
			headers: jsonHeaders(token),
			body: JSON.stringify({ label, permissions })
		});
		if (!response.ok)
			return fail(response.status, {
				scope: 'role',
				name,
				error: await readError(response, 'Nie udało się zapisać roli.')
			});
		const role: Role = await response.json();
		return { scope: 'role', name, message: 'Zapisano rolę.', role };
	},

	deleteRole: async ({ request, cookies, fetch }) => {
		const token = requireToken(cookies);
		const form = await request.formData();
		const name = String(form.get('name') || '');
		const response = await fetch(`${authApiUrl()}/api/admin/roles/${encodeURIComponent(name)}`, {
			method: 'DELETE',
			headers: { Authorization: `Bearer ${token}` }
		});
		if (!response.ok)
			return fail(response.status, {
				scope: 'role',
				name,
				error: await readError(response, 'Nie udało się usunąć roli.')
			});
		return { scope: 'role', name, deleted: true, message: 'Rola usunięta.' };
	}
};
