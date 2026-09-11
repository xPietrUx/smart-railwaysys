<script lang="ts">
    import { enhance } from '$app/forms';
    import type { SubmitFunction } from '@sveltejs/kit';
    import type { ActionData, PageData } from './$types';
    import type { Role } from './+page.server';

    export let data: PageData;
    export let form: ActionData;

    // Wynik akcji ma różny kształt zależnie od formularza; czytamy wspólne pola luźno.
    $: fb = (form ?? {}) as {
        scope?: string;
        id?: string;
        name?: string;
        error?: string;
        message?: string;
        success?: boolean;
    };

    function formatDate(value: number | null): string {
        if (!value) return '—';
        return new Date(value * 1000).toLocaleDateString('pl-PL', {
            year: 'numeric',
            month: '2-digit',
            day: '2-digit'
        });
    }

    function sortRoles(roles: Role[]): Role[] {
        return [...roles].sort((a, b) =>
            a.is_system !== b.is_system ? (a.is_system ? -1 : 1) : a.name.localeCompare(b.name)
        );
    }

    const handleRoleForm: SubmitFunction = () => {
        return async ({ result, update }) => {
            await update({ invalidateAll: false });
            if (result.type !== 'success' || !result.data) return;
            const payload = result.data as { role?: Role; deleted?: boolean; name?: string };
            if (payload.deleted && payload.name) {
                const removedName = payload.name;
                data = { ...data, roles: data.roles.filter((r) => r.name !== removedName) };
            } else if (payload.role) {
                const updated = payload.role;
                const exists = data.roles.some((r) => r.name === updated.name);
                const roles = exists
                    ? data.roles.map((r) => (r.name === updated.name ? updated : r))
                    : sortRoles([...data.roles, updated]);
                data = { ...data, roles };
            }
        };
    };

    $: canManageRoles = data.canManageRoles;
</script>

<svelte:head>
    <link
        rel="stylesheet"
        href="https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined:opsz,wght,FILL,GRAD@20..48,100..700,0..1,-50..200"
    />
    <title>Panel administratora — Smart Railway System</title>
</svelte:head>

<div class="admin">
    <header class="topbar">
        <div>
            <p class="eyebrow">Smart Railway System</p>
            <h1>Panel administratora</h1>
        </div>
        <nav>
            <span class="who" title={data.me.email}>{data.me.email}</span>
            <a class="btn ghost" data-sveltekit-preload-data="off" href="/panel">
                <span class="material-symbols-outlined" aria-hidden="true">arrow_back</span>
                Symulacja
            </a>
            <form method="POST" action="/wyloguj">
                <button class="btn danger-ghost" type="submit">
                    <span class="material-symbols-outlined" aria-hidden="true">logout</span>
                    Wyloguj
                </button>
            </form>
        </nav>
    </header>

    {#if fb.message && !fb.scope}
        <div class="banner ok" role="status">
            <span class="material-symbols-outlined" aria-hidden="true">check_circle</span>
            {fb.message}
        </div>
    {:else if fb.error && !fb.scope}
        <div class="banner err" role="alert">
            <span class="material-symbols-outlined" aria-hidden="true">error</span>
            {fb.error}
        </div>
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
                                <select class="cell-input select-cell" name="role" form={`user-${u.id}`}>
                                    {#each data.roles as r (r.name)}
                                        <option value={r.name} selected={r.name === u.role}>{r.label}</option>
                                    {/each}
                                </select>
                            </td>
                            <td>
                                <select class="cell-input select-cell" name="active" form={`user-${u.id}`}>
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
                                {#if fb.scope === 'user' && fb.id === u.id}
                                    {#if fb.error}
                                        <p class="row-error" role="alert">{fb.error}</p>
                                    {:else if fb.message}
                                        <p class="row-success" role="status">{fb.message}</p>
                                    {/if}
                                {/if}
                            </td>
                        </tr>
                    {/each}
                </tbody>
            </table>
        </div>

        <details class="adder">
            <summary>
                <span class="material-symbols-outlined" aria-hidden="true">add</span>
                Dodaj użytkownika
            </summary>
            <form method="POST" action="?/createUser" use:enhance class="add-user-form">
                <div class="add-user-fields">
                    <label class="add-field">
                        <span>E-mail</span>
                        <input
                            name="email"
                            type="email"
                            required
                            placeholder="nowy@smartrailway.pl"
                        />
                    </label>
                    <label class="add-field">
                        <span>Hasło</span>
                        <input
                            name="password"
                            type="password"
                            minlength="8"
                            required
                            placeholder="Min. 8 znaków"
                        />
                    </label>
                    <label class="add-field">
                        <span>Rola</span>
                        <select name="role">
                            {#each data.roles as r (r.name)}
                                <option value={r.name} selected={r.name === 'user'}>{r.label}</option>
                            {/each}
                        </select>
                    </label>
                </div>
                <div class="action-with-feedback">
                    <button class="btn" type="submit">Dodaj</button>
                    {#if fb.scope === 'createUser'}
                        {#if fb.error}
                            <span class="inline-error">{fb.error}</span>
                        {:else if fb.message}
                            <span class="inline-success">{fb.message}</span>
                        {/if}
                    {/if}
                </div>
            </form>
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
                <form method="POST" action="?/updateRole" use:enhance={handleRoleForm} class="role-card">
                    <input type="hidden" name="name" value={r.name} />
                    <div class="role-head">
                        <code class="role-name">{r.name}</code>
                        {#if r.is_system}<span class="tag">systemowa</span>{/if}
                    </div>
                    {#if r.is_system}
                        <p class="muted role-note">Rola systemowa — edycja zablokowana.</p>
                    {/if}
                    <label class="role-label"
                        >Nazwa wyświetlana
                        <input name="label" value={r.label} disabled={!canManageRoles || r.is_system} />
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
                                    disabled={!canManageRoles || r.is_system}
                                />
                                <span class="perm-content">
                                    <span>{p.label}</span>
                                    <code>{p.key}</code>
                                </span>
                            </label>
                        {/each}
                    </fieldset>
                    {#if canManageRoles && !r.is_system}
                        <div class="role-actions-wrapper">
                            <div class="role-actions">
                                <button class="btn small" type="submit">Zapisz</button>
                                <button
                                    class="btn small danger"
                                    type="submit"
                                    formaction="?/deleteRole"
                                    on:click={(e) => {
                                        if (!confirm(`Usunąć rolę ${r.label}?`)) e.preventDefault();
                                    }}>Usuń</button
                                >
                            </div>
                            {#if fb.scope === 'role' && fb.name === r.name}
                                {#if fb.error}
                                    <span class="inline-error">{fb.error}</span>
                                {:else if fb.message}
                                    <span class="inline-success">{fb.message}</span>
                                {/if}
                            {/if}
                        </div>
                    {/if}
                </form>
            {/each}
        </div>

        {#if canManageRoles}
            <details class="adder">
                <summary>
                    <span class="material-symbols-outlined" aria-hidden="true">add</span>
                    Dodaj rolę
                </summary>
                <form method="POST" action="?/createRole" use:enhance={handleRoleForm} class="add-role">
                    <div class="add-role-top">
                        <label class="add-role-field"
                            >ID (małe litery)
                            <input
                                class="small-input"
                                name="name"
                                required
                                pattern={'[a-z][a-z0-9_]{1,30}'}
                                placeholder="np. dyspozytor"
                            />
                        </label>
                        <label class="add-role-field"
                            >Nazwa wyświetlana
                            <input class="small-input" name="label" placeholder="np. Dyspozytor" />
                        </label>
                    </div>
                    <fieldset class="perms perms-create">
                        <legend>Uprawnienia</legend>
                        {#each data.permissions as p (p.key)}
                            <label class="perm perm-create">
                                <input type="checkbox" name="permissions" value={p.key} />
                                <span class="perm-content">
                                    <span>{p.label}</span>
                                    <code>{p.key}</code>
                                </span>
                            </label>
                        {/each}
                    </fieldset>
                    <div class="action-with-feedback">
                        <button class="btn" type="submit">Utwórz rolę</button>
                        {#if fb.scope === 'createRole'}
                            {#if fb.error}
                                <span class="inline-error">{fb.error}</span>
                            {:else if fb.message}
                                <span class="inline-success">{fb.message}</span>
                            {/if}
                        {/if}
                    </div>
                </form>
            </details>
        {/if}
    </section>
</div>

<style>
    .material-symbols-outlined {
        font-family: 'Material Symbols Outlined' !important;
        font-weight: normal;
        font-style: normal;
        font-size: 18px;
        line-height: 1;
        letter-spacing: normal;
        text-transform: none;
        display: inline-block;
        white-space: nowrap;
        word-wrap: normal;
        direction: ltr;
        -webkit-font-smoothing: antialiased;
        text-rendering: optimizeLegibility;
        -moz-osx-font-smoothing: grayscale;
        font-feature-settings: 'liga';
        font-variation-settings:
            'FILL' 0,
            'wght' 200,
            'GRAD' 0,
            'opsz' 24;
        user-select: none;
        vertical-align: middle;
    }

    :global(body) {
        margin: 0;
        font-family: 'Inter Variable', Inter, sans-serif;
        background: #141414;
        color: #f5f7f8;
        font-weight: 300;
    }

    .admin {
        max-width: 1400px;
        margin: 0 auto;
        padding: 32px clamp(16px, 4vw, 40px) 80px;
    }

    .topbar {
        display: flex;
        justify-content: space-between;
        align-items: flex-end;
        gap: 16px;
        flex-wrap: wrap;
        margin-bottom: 24px;
    }
    .eyebrow {
        margin: 0 0 4px;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        font-size: 0.66rem;
        font-weight: 300;
        color: #97a5ad;
    }
    .topbar h1 {
        margin: 0;
        font-size: 1.25rem;
        font-weight: 400;
        letter-spacing: 0.04em;
        text-transform: uppercase;
        color: #ffffff;
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
        font-size: 0.74rem;
        font-weight: 300;
        letter-spacing: 0.04em;
        color: #97a5ad;
    }

    .btn {
        border: 0;
        border-radius: 8px;
        background: rgba(255, 255, 255, 0.06);
        color: #f5f7f8;
        padding: 8px 14px;
        font-family: inherit;
        font-size: 0.72rem;
        font-weight: 400;
        letter-spacing: 0.06em;
        text-transform: uppercase;
        text-decoration: none;
        cursor: pointer;
        display: inline-flex;
        align-items: center;
        gap: 6px;
        transition: background-color 150ms ease, color 150ms ease;
    }
    .btn:hover {
        background: rgba(255, 255, 255, 0.1);
        color: #ffffff;
    }
    .btn.small {
        padding: 6px 10px;
        font-size: 0.68rem;
    }
    .btn.ghost {
        background: rgba(255, 255, 255, 0.04);
        color: #97a5ad;
    }
    .btn.ghost:hover {
        background: rgba(255, 255, 255, 0.08);
        color: #ffffff;
    }
    .btn.danger-ghost {
        background: rgba(222, 132, 137, 0.1);
        color: #de8489;
    }
    .btn.danger-ghost:hover {
        background: rgba(222, 132, 137, 0.2);
    }
    .btn.danger {
        background: rgba(222, 132, 137, 0.15);
        color: #de8489;
    }
    .btn.danger:hover {
        background: rgba(222, 132, 137, 0.28);
    }

    .banner {
        border-radius: 10px;
        padding: 10px 14px;
        margin-bottom: 18px;
        font-size: 0.74rem;
        font-weight: 300;
        letter-spacing: 0.02em;
        display: flex;
        align-items: center;
        gap: 8px;
    }
    .banner.ok {
        background: rgba(108, 176, 159, 0.15);
        color: #6cb09f;
    }
    .banner.err {
        background: rgba(222, 132, 137, 0.15);
        color: #de8489;
    }

    .card {
        background: rgba(20, 20, 20, 0.94);
        backdrop-filter: blur(16px);
        -webkit-backdrop-filter: blur(16px);
        border: 0;
        box-shadow: 0 20px 48px rgba(0, 0, 0, 0.6);
        border-radius: 14px;
        padding: 24px;
        margin-bottom: 24px;
    }
    .card h2 {
        margin: 0 0 16px;
        font-size: 0.95rem;
        font-weight: 400;
        letter-spacing: 0.06em;
        text-transform: uppercase;
        color: #ffffff;
        display: flex;
        align-items: center;
        gap: 10px;
    }
    .count {
        font-size: 0.66rem;
        font-weight: 400;
        letter-spacing: 0.06em;
        color: #97a5ad;
        background: rgba(255, 255, 255, 0.05);
        border-radius: 999px;
        padding: 2px 8px;
    }

    .table-scroll {
        overflow-x: auto;
    }
    table {
        width: 100%;
        border-collapse: collapse;
        font-size: 0.76rem;
    }
    th {
        text-align: left;
        font-weight: 400;
        color: #97a5ad;
        font-size: 0.66rem;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        padding: 0 10px 12px;
        white-space: nowrap;
    }
    td {
        padding: 10px;
        border-top: 1px solid rgba(255, 255, 255, 0.04);
        vertical-align: middle;
    }
    tr.self td {
        background: rgba(255, 255, 255, 0.02);
    }
    .actions-col {
        width: 1%;
    }

    .cell-input {
        width: 100%;
        box-sizing: border-box;
        background: rgba(255, 255, 255, 0.04);
        border: 0;
        border-radius: 8px;
        color: #f5f7f8;
        padding: 8px 12px;
        font-family: inherit;
        font-size: 0.76rem;
        font-weight: 300;
        letter-spacing: 0.04em;
        outline: none;
        transition: background-color 150ms ease;
    }
    .cell-input:focus {
        background: rgba(255, 255, 255, 0.08);
    }
    .cell-input:disabled {
        opacity: 0.4;
    }
    .cell-input.pw {
        width: 120px;
    }
    .select-cell {
        cursor: pointer;
    }
    .select-cell option {
        background: #1a1a1a;
        color: #f5f7f8;
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
        color: #de8489;
        font-size: 0.68rem;
        font-weight: 300;
        letter-spacing: 0.02em;
        margin: 6px 0 0;
    }
    .row-success {
        color: #6cb09f;
        font-size: 0.68rem;
        font-weight: 300;
        letter-spacing: 0.02em;
        margin: 6px 0 0;
    }
    .action-with-feedback {
        display: flex;
        align-items: center;
        gap: 12px;
        flex-wrap: wrap;
    }
    .inline-error {
        color: #de8489;
        font-size: 0.68rem;
        font-weight: 300;
    }
    .inline-success {
        color: #6cb09f;
        font-size: 0.68rem;
        font-weight: 300;
    }
    .muted {
        color: #97a5ad;
        font-weight: 300;
    }
    .note {
        font-size: 0.74rem;
        margin: -6px 0 16px;
    }
    .role-note {
        font-size: 0.66rem;
        margin: -2px 0 0;
    }
    .tag {
        display: inline-block;
        margin-left: 6px;
        font-size: 0.58rem;
        text-transform: uppercase;
        letter-spacing: 0.06em;
        color: #97a5ad;
        background: rgba(255, 255, 255, 0.05);
        border-radius: 999px;
        padding: 2px 6px;
    }

    .adder {
        margin-top: 18px;
        border-top: 1px solid rgba(255, 255, 255, 0.06);
        padding-top: 14px;
    }
    .adder summary {
        cursor: pointer;
        color: #f5f7f8;
        font-size: 0.74rem;
        font-weight: 400;
        letter-spacing: 0.06em;
        text-transform: uppercase;
        display: inline-flex;
        align-items: center;
        gap: 6px;
        transition: opacity 150ms ease;
    }
    .adder summary:hover {
        opacity: 0.8;
    }
    .adder summary .material-symbols-outlined {
        font-size: 16px;
        color: #97a5ad;
    }

    .add-user-form {
        margin-top: 14px;
        display: flex;
        flex-direction: column;
        gap: 14px;
    }
    .add-user-fields {
        display: flex;
        gap: 14px;
        flex-wrap: wrap;
        align-items: flex-end;
    }
    .add-field {
        display: flex;
        flex-direction: column;
        gap: 6px;
        font-size: 0.66rem;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        color: #97a5ad;
        font-weight: 300;
        flex: 1;
        min-width: 220px;
    }
    .add-field input,
    .add-field select {
        background: rgba(255, 255, 255, 0.04);
        border: 0;
        border-radius: 8px;
        color: #f5f7f8;
        padding: 8px 12px;
        font-family: inherit;
        font-size: 0.76rem;
        font-weight: 300;
        letter-spacing: 0.04em;
        text-transform: none;
        outline: none;
        width: 100%;
        box-sizing: border-box;
        transition: background-color 150ms ease;
    }
    .add-field input::placeholder {
        color: #64748b;
        text-transform: uppercase;
        letter-spacing: 0.04em;
    }
    .add-field input:focus,
    .add-field select:focus {
        background: rgba(255, 255, 255, 0.08);
    }
    .add-field select option {
        background: #1a1a1a;
        color: #f5f7f8;
    }

    /* Układ paneli ról: 3 obok siebie */
    .roles-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));
        gap: 20px;
    }
    .role-card {
        background: rgba(255, 255, 255, 0.02);
        border: 0;
        border-radius: 10px;
        padding: 18px;
        margin: 0;
        display: flex;
        flex-direction: column;
        gap: 14px;
    }
    .role-head {
        display: flex;
        align-items: center;
        gap: 8px;
    }
    .role-name {
        font-size: 0.82rem;
        font-weight: 400;
        color: #ffffff;
    }
    code {
        font-family: 'Fira Mono', ui-monospace, monospace;
        font-size: 0.82em;
        color: #97a5ad;
    }
    .role-label {
        display: flex;
        flex-direction: column;
        gap: 6px;
        font-size: 0.66rem;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        color: #97a5ad;
        font-weight: 300;
    }
    .role-label input {
        background: rgba(255, 255, 255, 0.04);
        border: 0;
        border-radius: 8px;
        color: #f5f7f8;
        padding: 8px 12px;
        font-family: inherit;
        font-size: 0.76rem;
        font-weight: 300;
        letter-spacing: 0.04em;
        text-transform: none;
        outline: none;
        width: 100%;
        box-sizing: border-box;
    }
    .role-label input:focus {
        background: rgba(255, 255, 255, 0.08);
    }
    .role-label input:disabled {
        opacity: 0.4;
    }

    .perms {
        border: 0;
        border-radius: 8px;
        background: rgba(255, 255, 255, 0.02);
        padding: 12px;
        margin: 0;
        display: flex;
        flex-direction: column;
        gap: 10px;
    }
    .perms legend {
        font-size: 0.62rem;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        color: #97a5ad;
        padding: 0 4px;
        font-weight: 300;
        margin-bottom: 4px;
    }
    .perm {
        display: flex;
        align-items: center;
        gap: 10px;
        font-size: 0.74rem;
        color: #f5f7f8;
        font-weight: 300;
        cursor: pointer;
        user-select: none;
    }
    .perm input[type="checkbox"] {
        appearance: none;
        -webkit-appearance: none;
        width: 16px;
        height: 16px;
        border-radius: 4px;
        background: rgba(255, 255, 255, 0.06);
        border: 1px solid rgba(255, 255, 255, 0.2);
        outline: none;
        cursor: pointer;
        display: grid;
        place-content: center;
        transition: background-color 150ms ease, border-color 150ms ease;
        flex-shrink: 0;
        margin: 0;
    }
    .perm input[type="checkbox"]:checked {
        background: #f5f7f8;
        border-color: #f5f7f8;
    }
    .perm input[type="checkbox"]:checked::before {
        content: "";
        width: 4px;
        height: 8px;
        border: solid #141414;
        border-width: 0 2px 2px 0;
        transform: rotate(45deg);
        margin-top: -1px;
    }
    .perm input[type="checkbox"]:disabled {
        opacity: 0.4;
        cursor: default;
    }
    .perm-content {
        display: flex;
        align-items: baseline;
        gap: 6px;
        flex-wrap: wrap;
    }
    .perm code {
        font-size: 0.68em;
        color: #64748b;
        background: rgba(255, 255, 255, 0.03);
        padding: 1px 4px;
        border-radius: 4px;
    }

    /* Styl formularza dodawania nowej roli z mniejszą czcionką i większym odstępem */
    .add-role {
        margin-top: 14px;
        display: flex;
        flex-direction: column;
        gap: 16px;
    }
    .add-role-top {
        display: flex;
        gap: 20px;
        flex-wrap: wrap;
    }
    .add-role-field {
        display: flex;
        flex-direction: column;
        gap: 8px;
        font-size: 0.6rem;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        color: #97a5ad;
        font-weight: 300;
        flex: 1;
        min-width: 240px;
    }
    .small-input {
        background: rgba(255, 255, 255, 0.04);
        border: 0;
        border-radius: 8px;
        color: #f5f7f8;
        padding: 9px 12px;
        font-family: inherit;
        font-size: 0.7rem;
        font-weight: 300;
        letter-spacing: 0.04em;
        text-transform: none;
        outline: none;
        width: 100%;
        box-sizing: border-box;
        transition: background-color 150ms ease;
    }
    .small-input::placeholder {
        color: #64748b;
        text-transform: uppercase;
        letter-spacing: 0.04em;
    }
    .small-input:focus {
        background: rgba(255, 255, 255, 0.08);
    }

    .perms-create {
        width: 100%;
        box-sizing: border-box;
    }
    .perm-create {
        display: flex;
        align-items: center;
        justify-content: flex-start;
        gap: 12px;
        text-align: left;
    }

    .role-actions-wrapper {
        display: flex;
        align-items: center;
        gap: 10px;
        flex-wrap: wrap;
    }
    .role-actions {
        display: flex;
        gap: 8px;
    }
</style>