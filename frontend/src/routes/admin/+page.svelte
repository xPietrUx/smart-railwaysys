<script lang="ts">
	import { enhance } from '$app/forms';
	import type { ActionData, PageData } from './$types';

	export let data: PageData;
	export let form: ActionData;

	// Wynik akcji ma różny kształt zależnie od formularza; czytamy wspólne pola luźno.
	$: fb = (form ?? {}) as {
		scope?: string;
		id?: string;
		name?: string;
		error?: string;
		message?: string;
	};

	function formatDate(value: number | null): string {
		if (!value) return '—';
		return new Date(value * 1000).toLocaleDateString('pl-PL', {
			year: 'numeric',
			month: '2-digit',
			day: '2-digit'
		});
	}

	// Uprawnienia administracyjne roli „admin” są zablokowane — nie da się ich
	// odebrać, więc pokazujemy je jako zaznaczone i wyłączone.
	const ADMIN_LOCKED = ['users.manage', 'roles.manage'];
	const isLocked = (roleName: string, key: string) =>
		roleName === 'admin' && ADMIN_LOCKED.includes(key);

	$: canManageRoles = data.canManageRoles;
</script>

<svelte:head><title>Panel administratora — Smart Railway System</title></svelte:head>

<div class="admin">
	<header class="topbar">
		<div>
			<p class="eyebrow">Smart Railway System</p>
			<h1>Panel administratora</h1>
		</div>
		<nav>
			<span class="who" title={data.me.email}>{data.me.email}</span>
			<a class="btn" data-sveltekit-preload-data="off" href="/panel">← Symulacja</a>
			<form method="POST" action="/wyloguj">
				<button class="btn" type="submit">Wyloguj</button>
			</form>
		</nav>
	</header>

	{#if fb.message}
		<div class="banner ok" role="status">{fb.message}</div>
	{:else if fb.error && !fb.id && !fb.name}
		<div class="banner err" role="alert">{fb.error}</div>
	{/if}

	<!-- ============================ UŻYTKOWNICY ============================ -->
	<section class="card">
		<h2>Użytkownicy <span class="count">{data.users.length}</span></h2>

		<div class="table-scroll">
			<table>
				<thead>
					<tr>
						<th>E-mail</th>
						<th>Rola</th>
						<th>Status</th>
						<th>Utworzono</th>
						<th class="actions-col">Akcje</th>
					</tr>
				</thead>
				<tbody>
					{#each data.users as u (u.id)}
						<tr class:self={u.id === data.me.id}>
							<td>
								<form
									id={`user-${u.id}`}
									method="POST"
									action="?/updateUser"
									use:enhance
									class="row-form"
								>
									<input type="hidden" name="id" value={u.id} />
									<input
										class="cell-input"
										name="email"
										type="email"
										value={u.email}
										required
										aria-label="E-mail użytkownika"
									/>
								</form>
							</td>
							<td>
								<select class="cell-input" name="role" form={`user-${u.id}`}>
									{#each data.roles as r (r.name)}
										<option value={r.name} selected={r.name === u.role}>{r.label}</option>
									{/each}
								</select>
							</td>
							<td>
								<select class="cell-input" name="active" form={`user-${u.id}`}>
									<option value="true" selected={u.active}>Aktywny</option>
									<option value="false" selected={!u.active}>Zablokowany</option>
								</select>
							</td>
							<td class="muted">
								{formatDate(u.created_at)}
								{#if u.id === data.me.id}<span class="tag">to Ty</span>{/if}
							</td>
							<td class="actions-col">
								<div class="row-actions">
									<button class="btn small" type="submit" form={`user-${u.id}`}>Zapisz</button>

									<form method="POST" action="?/resetPassword" use:enhance class="pw-form">
										<input type="hidden" name="id" value={u.id} />
										<input
											class="cell-input pw"
											name="password"
											type="password"
											minlength="8"
											placeholder="Nowe hasło"
											required
											aria-label="Nowe hasło"
										/>
										<button class="btn small ghost" type="submit">Reset</button>
									</form>

									{#if u.id !== data.me.id}
										<form
											method="POST"
											action="?/deleteUser"
											use:enhance={({ cancel }) => {
												if (!confirm(`Usunąć użytkownika ${u.email}?`)) cancel();
											}}
										>
											<input type="hidden" name="id" value={u.id} />
											<button class="btn small danger" type="submit">Usuń</button>
										</form>
									{/if}
								</div>
								{#if fb.scope === 'user' && fb.id === u.id && fb.error}
									<p class="row-error" role="alert">{fb.error}</p>
								{/if}
							</td>
						</tr>
					{/each}
				</tbody>
			</table>
		</div>

		<details class="adder">
			<summary>+ Dodaj użytkownika</summary>
			<form method="POST" action="?/createUser" use:enhance class="add-form">
				<label
					>E-mail<input
						name="email"
						type="email"
						required
						placeholder="nowy@smartrailway.pl"
					/></label
				>
				<label
					>Hasło<input
						name="password"
						type="password"
						minlength="8"
						required
						placeholder="Min. 8 znaków"
					/></label
				>
				<label
					>Rola
					<select name="role">
						{#each data.roles as r (r.name)}
							<option value={r.name} selected={r.name === 'user'}>{r.label}</option>
						{/each}
					</select>
				</label>
				<button class="btn" type="submit">Dodaj</button>
			</form>
			{#if fb.scope === 'createUser' && fb.error}
				<p class="row-error" role="alert">{fb.error}</p>
			{/if}
		</details>
	</section>

	<!-- ============================ ROLE ============================ -->
	<section class="card">
		<h2>Role i uprawnienia <span class="count">{data.roles.length}</span></h2>
		{#if !canManageRoles}
			<p class="muted note">
				Masz podgląd ról, ale bez uprawnienia <code>roles.manage</code> nie możesz ich edytować.
			</p>
		{/if}

		<div class="roles-grid">
			{#each data.roles as r (r.name)}
				<form method="POST" action="?/updateRole" use:enhance class="role-card">
					<input type="hidden" name="name" value={r.name} />
					<div class="role-head">
						<code class="role-name">{r.name}</code>
						{#if r.is_system}<span class="tag">systemowa</span>{/if}
					</div>
					<label class="role-label"
						>Nazwa wyświetlana
						<input name="label" value={r.label} disabled={!canManageRoles} />
					</label>
					<fieldset class="perms">
						<legend>Uprawnienia</legend>
						{#each data.permissions as p (p.key)}
							<label class="perm">
								<input
									type="checkbox"
									name="permissions"
									value={p.key}
									checked={r.permissions.includes(p.key)}
									disabled={!canManageRoles || isLocked(r.name, p.key)}
								/>
								<span>{p.label} <code>{p.key}</code></span>
							</label>
						{/each}
					</fieldset>
					{#if fb.scope === 'role' && fb.name === r.name && fb.error}
						<p class="row-error" role="alert">{fb.error}</p>
					{/if}
					{#if canManageRoles}
						<div class="role-actions">
							<button class="btn small" type="submit">Zapisz</button>
							{#if !r.is_system}
								<button
									class="btn small danger"
									type="submit"
									formaction="?/deleteRole"
									on:click={(e) => {
										if (!confirm(`Usunąć rolę ${r.label}?`)) e.preventDefault();
									}}>Usuń</button
								>
							{/if}
						</div>
					{/if}
				</form>
			{/each}
		</div>

		{#if canManageRoles}
			<details class="adder">
				<summary>+ Dodaj rolę</summary>
				<form method="POST" action="?/createRole" use:enhance class="add-role">
					<div class="add-role-top">
						<label
							>Nazwa (identyfikator)
							<input
								name="name"
								required
								pattern={'[a-z][a-z0-9_]{1,30}'}
								placeholder="np. dyspozytor"
							/>
						</label>
						<label>Nazwa wyświetlana<input name="label" placeholder="np. Dyspozytor" /></label>
					</div>
					<fieldset class="perms">
						<legend>Uprawnienia</legend>
						{#each data.permissions as p (p.key)}
							<label class="perm">
								<input type="checkbox" name="permissions" value={p.key} />
								<span>{p.label} <code>{p.key}</code></span>
							</label>
						{/each}
					</fieldset>
					<button class="btn" type="submit">Utwórz rolę</button>
				</form>
				{#if fb.scope === 'createRole' && fb.error}
					<p class="row-error" role="alert">{fb.error}</p>
				{/if}
			</details>
		{/if}
	</section>
</div>

<style>
	:global(body) {
		margin: 0;
		font-family: 'Inter Variable', sans-serif;
		background: linear-gradient(180deg, #0f172a 0%, #111827 100%);
		color: #e5eefb;
	}

	.admin {
		max-width: 1100px;
		margin: 0 auto;
		padding: 28px clamp(16px, 4vw, 40px) 80px;
	}

	.topbar {
		display: flex;
		justify-content: space-between;
		align-items: flex-end;
		gap: 16px;
		flex-wrap: wrap;
		margin-bottom: 22px;
	}
	.eyebrow {
		margin: 0;
		text-transform: uppercase;
		letter-spacing: 0.14em;
		font-size: 0.62rem;
		color: #93c5fd;
	}
	.topbar h1 {
		margin: 4px 0 0;
		font-size: 1.6rem;
	}
	.topbar nav {
		display: flex;
		align-items: center;
		gap: 10px;
		flex-wrap: wrap;
	}
	.topbar form {
		margin: 0;
	}
	.who {
		max-width: 220px;
		overflow: hidden;
		text-overflow: ellipsis;
		white-space: nowrap;
		font-size: 0.78rem;
		color: #94a3b8;
	}

	.btn {
		border: 1px solid rgba(148, 163, 184, 0.3);
		border-radius: 9px;
		background: rgba(30, 41, 59, 0.72);
		color: #e2e8f0;
		padding: 8px 12px;
		font: inherit;
		font-size: 0.78rem;
		font-weight: 600;
		text-decoration: none;
		cursor: pointer;
		transition:
			border-color 0.2s,
			background 0.2s;
	}
	.btn:hover {
		border-color: rgba(96, 165, 250, 0.7);
	}
	.btn.small {
		padding: 6px 10px;
		font-size: 0.72rem;
	}
	.btn.ghost {
		background: transparent;
	}
	.btn.danger {
		border-color: rgba(239, 68, 68, 0.4);
		color: #fca5a5;
	}
	.btn.danger:hover {
		border-color: rgba(239, 68, 68, 0.8);
	}

	.banner {
		border-radius: 10px;
		padding: 11px 14px;
		margin-bottom: 18px;
		font-size: 0.82rem;
		border: 1px solid transparent;
	}
	.banner.ok {
		background: rgba(16, 185, 129, 0.14);
		border-color: rgba(16, 185, 129, 0.4);
		color: #6ee7b7;
	}
	.banner.err {
		background: rgba(239, 68, 68, 0.14);
		border-color: rgba(239, 68, 68, 0.4);
		color: #fca5a5;
	}

	.card {
		background: rgba(15, 23, 42, 0.72);
		border: 1px solid rgba(148, 163, 184, 0.18);
		border-radius: 16px;
		padding: 22px;
		margin-bottom: 22px;
	}
	.card h2 {
		margin: 0 0 16px;
		font-size: 1.05rem;
		display: flex;
		align-items: center;
		gap: 10px;
	}
	.count {
		font-size: 0.72rem;
		font-weight: 600;
		color: #93c5fd;
		background: rgba(37, 99, 235, 0.22);
		border-radius: 999px;
		padding: 2px 9px;
	}

	.table-scroll {
		overflow-x: auto;
	}
	table {
		width: 100%;
		border-collapse: collapse;
		font-size: 0.82rem;
	}
	th {
		text-align: left;
		font-weight: 600;
		color: #94a3b8;
		font-size: 0.68rem;
		text-transform: uppercase;
		letter-spacing: 0.06em;
		padding: 0 10px 10px;
		white-space: nowrap;
	}
	td {
		padding: 8px 10px;
		border-top: 1px solid rgba(148, 163, 184, 0.12);
		vertical-align: top;
	}
	tr.self td {
		background: rgba(37, 99, 235, 0.08);
	}
	.actions-col {
		width: 1%;
	}

	.cell-input {
		width: 100%;
		box-sizing: border-box;
		background: rgba(30, 41, 59, 0.7);
		border: 1px solid rgba(148, 163, 184, 0.25);
		border-radius: 7px;
		color: #e5eefb;
		padding: 7px 9px;
		font: inherit;
		font-size: 0.8rem;
	}
	.cell-input:focus {
		outline: none;
		border-color: #60a5fa;
	}
	.cell-input:disabled {
		opacity: 0.55;
	}
	.cell-input.pw {
		width: 130px;
	}

	.row-form {
		margin: 0;
	}
	.row-actions {
		display: flex;
		align-items: center;
		gap: 6px;
		flex-wrap: wrap;
	}
	.pw-form {
		display: flex;
		gap: 4px;
		margin: 0;
	}
	.row-error {
		color: #fca5a5;
		font-size: 0.72rem;
		margin: 6px 0 0;
	}
	.muted {
		color: #94a3b8;
	}
	.note {
		font-size: 0.8rem;
		margin: -6px 0 16px;
	}
	.tag {
		display: inline-block;
		margin-left: 6px;
		font-size: 0.6rem;
		text-transform: uppercase;
		letter-spacing: 0.05em;
		color: #cbd5e1;
		border: 1px solid rgba(148, 163, 184, 0.3);
		border-radius: 999px;
		padding: 1px 7px;
	}

	.adder {
		margin-top: 16px;
		border-top: 1px solid rgba(148, 163, 184, 0.14);
		padding-top: 14px;
	}
	.adder summary {
		cursor: pointer;
		color: #93c5fd;
		font-size: 0.82rem;
		font-weight: 600;
	}
	.add-form {
		display: flex;
		gap: 12px;
		flex-wrap: wrap;
		align-items: flex-end;
		margin-top: 14px;
	}
	.add-form label,
	.add-role label,
	.role-label {
		display: flex;
		flex-direction: column;
		gap: 5px;
		font-size: 0.68rem;
		text-transform: uppercase;
		letter-spacing: 0.06em;
		color: #94a3b8;
	}
	.add-form input,
	.add-form select,
	.add-role input,
	.role-label input {
		background: rgba(30, 41, 59, 0.7);
		border: 1px solid rgba(148, 163, 184, 0.25);
		border-radius: 7px;
		color: #e5eefb;
		padding: 8px 9px;
		font: inherit;
		font-size: 0.82rem;
		text-transform: none;
		letter-spacing: 0;
	}

	.roles-grid {
		display: grid;
		grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
		gap: 14px;
	}
	.role-card {
		background: rgba(30, 41, 59, 0.5);
		border: 1px solid rgba(148, 163, 184, 0.18);
		border-radius: 12px;
		padding: 14px;
		margin: 0;
		display: flex;
		flex-direction: column;
		gap: 12px;
	}
	.role-head {
		display: flex;
		align-items: center;
		gap: 8px;
	}
	.role-name {
		font-size: 0.9rem;
		color: #f8fafc;
	}
	code {
		font-family: 'Fira Mono', ui-monospace, monospace;
		font-size: 0.86em;
		color: #93c5fd;
	}
	.perms {
		border: 1px solid rgba(148, 163, 184, 0.18);
		border-radius: 9px;
		padding: 10px 12px;
		margin: 0;
		display: flex;
		flex-direction: column;
		gap: 7px;
	}
	.perms legend {
		font-size: 0.64rem;
		text-transform: uppercase;
		letter-spacing: 0.06em;
		color: #94a3b8;
		padding: 0 4px;
	}
	.perm {
		display: flex;
		align-items: flex-start;
		gap: 8px;
		font-size: 0.78rem;
		color: #e5eefb;
		cursor: pointer;
	}
	.perm input {
		margin-top: 2px;
		accent-color: #2563eb;
	}
	.perm code {
		font-size: 0.72em;
		color: #64748b;
	}
	.role-actions {
		display: flex;
		gap: 8px;
	}
	.add-role {
		margin-top: 14px;
		display: flex;
		flex-direction: column;
		gap: 14px;
	}
	.add-role-top {
		display: flex;
		gap: 14px;
		flex-wrap: wrap;
	}
	.add-role .perms {
		max-width: 520px;
	}
</style>
