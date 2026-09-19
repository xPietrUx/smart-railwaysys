<script lang="ts">
    import { enhance } from '$app/forms';
    import type { SubmitFunction } from '@sveltejs/kit';
    import { locale, setLocale, t } from '$lib/i18n';
    import type { ActionData, PageData } from './$types';
    import type { Role } from './+page.server';

    export let data: PageData;
    export let form: ActionData;

    $: fb = (form ?? {}) as {
        scope?: string;
        id?: string;
        name?: string;
        error?: string;
        message?: string;
        success?: boolean;
    };

    let isLoadingData = false;
    let submittingUsers = new Set<string>();
    let resettingPw = new Set<string>();
    let deletingUsers = new Set<string>();
    let submittingRoles = new Set<string>();
    let isCreatingUser = false;
    let isCreatingRole = false;

    function toggleLanguage() {
        setLocale($locale === 'pl' ? 'en' : 'pl');
    }

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

    const handleUserUpdate: SubmitFunction = ({ formData }) => {
        const id = formData.get('id')?.toString();
        if (id) submittingUsers = new Set(submittingUsers.add(id));
        return async ({ update }) => {
            try {
                // reset: false — domyślny reset() enhance'a czyścił pole e-maila do jego
                // defaultValue (pustego dla wierszy zamontowanych po stronie klienta),
                // a Svelte potem pomijał ponowny zapis wartości, bo z jego punktu
                // widzenia się nie zmieniła — e-mail zostawał pusty mimo udanego zapisu.
                await update({ invalidateAll: true, reset: false });
            } finally {
                if (id) {
                    submittingUsers.delete(id);
                    submittingUsers = new Set(submittingUsers);
                }
            }
        };
    };

    const handlePwReset: SubmitFunction = ({ formData }) => {
        const id = formData.get('id')?.toString();
        if (id) resettingPw = new Set(resettingPw.add(id));
        return async ({ update }) => {
            try {
                await update({ invalidateAll: false });
            } finally {
                if (id) {
                    resettingPw.delete(id);
                    resettingPw = new Set(resettingPw);
                }
            }
        };
    };

    const handleUserDelete: SubmitFunction = ({ formData, cancel }) => {
        const id = formData.get('id')?.toString();
        if (!confirm($t('admin.users.confirmDelete'))) {
            cancel();
            return;
        }
        if (id) deletingUsers = new Set(deletingUsers.add(id));
        return async ({ update }) => {
            try {
                await update({ invalidateAll: true });
            } finally {
                if (id) {
                    deletingUsers.delete(id);
                    deletingUsers = new Set(deletingUsers);
                }
            }
        };
    };

    const handleCreateUser: SubmitFunction = () => {
        isCreatingUser = true;
        return async ({ update }) => {
            try {
                await update();
            } finally {
                isCreatingUser = false;
            }
        };
    };

    const handleRoleForm: SubmitFunction = ({ formData }) => {
        const name = formData.get('name')?.toString();
        if (name) submittingRoles = new Set(submittingRoles.add(name));
        return async ({ result, update }) => {
            try {
                // reset: false — ten sam powód co przy edycji użytkownika: to edycja
                // w miejscu (nazwa roli, checkboxy uprawnień), nie formularz dodawania.
                await update({ invalidateAll: false, reset: false });
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
            } finally {
                if (name) {
                    submittingRoles.delete(name);
                    submittingRoles = new Set(submittingRoles);
                }
            }
        };
    };

    const handleCreateRole: SubmitFunction = () => {
        isCreatingRole = true;
        return async ({ result, update }) => {
            try {
                await update({ invalidateAll: false });
                if (result.type === 'success' && result.data) {
                    const payload = result.data as { role?: Role };
                    if (payload.role) {
                        data = { ...data, roles: sortRoles([...data.roles, payload.role]) };
                    }
                }
            } finally {
                isCreatingRole = false;
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
    <title>{$t('admin.headTitle')}</title>
</svelte:head>

<div class="admin">
    <header class="topbar">
        <div>
            <p class="eyebrow">Smart Railway System</p>
            <h1>{$t('admin.title')}</h1>
        </div>
        <nav>
            <span class="who" title={data.me.email}>{data.me.email}</span>
            <button
                class="btn ghost"
                type="button"
                on:click={toggleLanguage}
                aria-label={$locale === 'pl' ? 'Zmień język na angielski' : 'Change language to Polish'}
                title={$locale === 'pl' ? 'English' : 'Polski'}
            >
                <span class="material-symbols-outlined" aria-hidden="true">language</span>
                {$locale.toUpperCase()}
            </button>
            <a class="btn ghost" data-sveltekit-preload-data="off" href="/panel" tabindex="0">
                <span class="material-symbols-outlined" aria-hidden="true">arrow_back</span>
                {$t('admin.nav.simulation')}
            </a>
            <form method="POST" action="/wyloguj">
                <button class="btn danger-ghost" type="submit" tabindex="0">
                    <span class="material-symbols-outlined" aria-hidden="true">logout</span>
                    {$t('header.logout')}
                </button>
            </form>
        </nav>
    </header>

    {#if fb.message && !fb.scope}
        <div class="banner ok" role="status" aria-live="polite">
            <span class="material-symbols-outlined" aria-hidden="true">check_circle</span>
            {fb.message}
        </div>
    {:else if fb.error && !fb.scope}
        <div class="banner err" role="alert" aria-live="assertive">
            <span class="material-symbols-outlined" aria-hidden="true">error</span>
            {fb.error}
        </div>
    {/if}

    <!-- ============================ UŻYTKOWNICY ============================ -->
    <section class="card">
        <h2>{$t('admin.users.heading')} <span class="count">{data.users.length}</span></h2>

        {#if isLoadingData}
            <div class="skeleton-table">
                <div class="skeleton-row header"></div>
                <div class="skeleton-row"></div>
                <div class="skeleton-row"></div>
                <div class="skeleton-row"></div>
            </div>
        {:else}
            <div class="table-scroll">
                <table>
                    <thead>
                        <tr>
                            <th>{$t('admin.field.email')}</th>
                            <th>{$t('admin.field.role')}</th>
                            <th>{$t('admin.field.status')}</th>
                            <th>{$t('admin.field.created')}</th>
                            <th class="actions-col">{$t('admin.field.actions')}</th>
                        </tr>
                    </thead>
                    <tbody>
                        {#each data.users as u (u.id)}
                            {@const isSaving = submittingUsers.has(u.id)}
                            {@const isResetting = resettingPw.has(u.id)}
                            {@const isDeleting = deletingUsers.has(u.id)}
                            <tr class:self={u.id === data.me.id} class:row-loading={isSaving || isDeleting}>
                                <td>
                                    <form
                                        id={`user-${u.id}`}
                                        method="POST"
                                        action="?/updateUser"
                                        use:enhance={handleUserUpdate}
                                        class="row-form"
                                    >
                                        <input type="hidden" name="id" value={u.id} />
                                        <input
                                            class="cell-input"
                                            name="email"
                                            type="email"
                                            value={u.email}
                                            required
                                            aria-label={$t('admin.users.emailAria')}
                                            disabled={isSaving || isDeleting}
                                        />
                                    </form>
                                </td>
                                <td>
                                    <select
                                        class="cell-input select-cell"
                                        name="role"
                                        form={`user-${u.id}`}
                                        disabled={isSaving || isDeleting}
                                    >
                                        {#each data.roles as r (r.name)}
                                            <option value={r.name} selected={r.name === u.role}>{r.label}</option>
                                        {/each}
                                    </select>
                                </td>
                                <td>
                                    <select
                                        class="cell-input select-cell"
                                        name="active"
                                        form={`user-${u.id}`}
                                        disabled={isSaving || isDeleting}
                                    >
                                        <option value="true" selected={u.active}>{$t('admin.users.active')}</option>
                                        <option value="false" selected={!u.active}>{$t('admin.users.blocked')}</option>
                                    </select>
                                </td>
                                <td class="muted">
                                    {formatDate(u.created_at)}
                                    {#if u.id === data.me.id}<span class="tag">{$t('admin.users.thatsYou')}</span>{/if}
                                </td>
                                <td class="actions-col">
                                    <div class="row-actions">
                                        <button
                                            class="btn small"
                                            type="submit"
                                            form={`user-${u.id}`}
                                            disabled={isSaving || isDeleting}
                                        >
                                            {#if isSaving}
                                                <span class="spinner-small" aria-hidden="true"></span>
                                            {/if}
                                            <span>{$t('admin.actions.save')}</span>
                                        </button>

                                        <form
                                            method="POST"
                                            action="?/resetPassword"
                                            use:enhance={handlePwReset}
                                            class="pw-form"
                                        >
                                            <input type="hidden" name="id" value={u.id} />
                                            <input
                                                class="cell-input pw"
                                                name="password"
                                                type="password"
                                                minlength="8"
                                                placeholder={$t('admin.users.newPasswordPlaceholder')}
                                                required
                                                aria-label={$t('admin.users.newPasswordPlaceholder')}
                                                disabled={isResetting || isDeleting}
                                            />
                                            <button
                                                class="btn small ghost"
                                                type="submit"
                                                disabled={isResetting || isDeleting}
                                            >
                                                {#if isResetting}
                                                    <span class="spinner-small" aria-hidden="true"></span>
                                                {/if}
                                                <span>{$t('admin.actions.reset')}</span>
                                            </button>
                                        </form>

                                        {#if u.id !== data.me.id}
                                            <form
                                                method="POST"
                                                action="?/deleteUser"
                                                use:enhance={handleUserDelete}
                                            >
                                                <input type="hidden" name="id" value={u.id} />
                                                <button
                                                    class="btn small danger"
                                                    type="submit"
                                                    disabled={isDeleting || isSaving}
                                                >
                                                    {#if isDeleting}
                                                        <span class="spinner-small" aria-hidden="true"></span>
                                                    {/if}
                                                    <span>{$t('admin.actions.delete')}</span>
                                                </button>
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
        {/if}

        <details class="adder">
            <summary>
                <span class="material-symbols-outlined" aria-hidden="true">add</span>
                {$t('admin.users.addSummary')}
            </summary>
            <form method="POST" action="?/createUser" use:enhance={handleCreateUser} class="add-user-form">
                <div class="add-user-fields">
                    <label class="add-field">
                        <span>{$t('admin.field.email')}</span>
                        <input
                            name="email"
                            type="email"
                            required
                            placeholder="nowy@smartrailway.pl"
                            disabled={isCreatingUser}
                        />
                    </label>
                    <label class="add-field">
                        <span>{$t('admin.field.password')}</span>
                        <input
                            name="password"
                            type="password"
                            minlength="8"
                            required
                            placeholder={$t('admin.users.minChars')}
                            disabled={isCreatingUser}
                        />
                    </label>
                    <label class="add-field">
                        <span>{$t('admin.field.role')}</span>
                        <select name="role" disabled={isCreatingUser}>
                            {#each data.roles as r (r.name)}
                                <option value={r.name} selected={r.name === 'user'}>{r.label}</option>
                            {/each}
                        </select>
                    </label>
                </div>
                <div class="action-with-feedback">
                    <button class="btn" type="submit" disabled={isCreatingUser}>
                        {#if isCreatingUser}
                            <span class="spinner-small" aria-hidden="true"></span>
                        {/if}
                        {$t('admin.actions.add')}
                    </button>
                    {#if fb.scope === 'createUser'}
                        {#if fb.error}
                            <span class="inline-error" role="alert">{fb.error}</span>
                        {:else if fb.message}
                            <span class="inline-success" role="status">{fb.message}</span>
                        {/if}
                    {/if}
                </div>
            </form>
        </details>
    </section>

    <!-- ============================ ROLE ============================ -->
    <section class="card">
        <h2>{$t('admin.roles.heading')} <span class="count">{data.roles.length}</span></h2>
        {#if !canManageRoles}
            <p class="muted note">
                {$t('admin.roles.readOnlyNotePrefix')} <code>roles.manage</code>
                {$t('admin.roles.readOnlyNoteSuffix')}
            </p>
        {/if}

        {#if isLoadingData}
            <div class="roles-grid">
                <div class="skeleton-card"></div>
                <div class="skeleton-card"></div>
                <div class="skeleton-card"></div>
            </div>
        {:else}
            <div class="roles-grid">
                {#each data.roles as r (r.name)}
                    {@const isRoleBusy = submittingRoles.has(r.name)}
                    <form method="POST" action="?/updateRole" use:enhance={handleRoleForm} class="role-card">
                        <input type="hidden" name="name" value={r.name} />
                        <div class="role-head">
                            <code class="role-name">{r.name}</code>
                            {#if r.is_system}<span class="tag">{$t('admin.roles.systemTag')}</span>{/if}
                        </div>
                        {#if r.is_system}
                            <p class="muted role-note">{$t('admin.roles.systemNote')}</p>
                        {/if}
                        <label class="role-label"
                            >{$t('admin.field.displayName')}
                            <input name="label" value={r.label} disabled={!canManageRoles || r.is_system || isRoleBusy} />
                        </label>
                        <fieldset class="perms">
                            <legend>{$t('admin.roles.permissionsLegend')}</legend>
                            {#each data.permissions as p (p.key)}
                                <label class="perm">
                                    <input
                                        type="checkbox"
                                        name="permissions"
                                        value={p.key}
                                        checked={r.permissions.includes(p.key)}
                                        disabled={!canManageRoles || r.is_system || isRoleBusy}
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
                                    <button class="btn small" type="submit" disabled={isRoleBusy}>
                                        {#if isRoleBusy}
                                            <span class="spinner-small" aria-hidden="true"></span>
                                        {/if}
                                        {$t('admin.actions.save')}
                                    </button>
                                    <button
                                        class="btn small danger"
                                        type="submit"
                                        formaction="?/deleteRole"
                                        disabled={isRoleBusy}
                                        on:click={(e) => {
                                            if (!confirm($t('admin.roles.confirmDelete', { role: r.label })))
                                                e.preventDefault();
                                        }}>{$t('admin.actions.delete')}</button
                                    >
                                </div>
                                {#if fb.scope === 'role' && fb.name === r.name}
                                    {#if fb.error}
                                        <span class="inline-error" role="alert">{fb.error}</span>
                                    {:else if fb.message}
                                        <span class="inline-success" role="status">{fb.message}</span>
                                    {/if}
                                {/if}
                            </div>
                        {/if}
                    </form>
                {/each}
            </div>
        {/if}

        {#if canManageRoles}
            <details class="adder">
                <summary>
                    <span class="material-symbols-outlined" aria-hidden="true">add</span>
                    {$t('admin.roles.addSummary')}
                </summary>
                <form method="POST" action="?/createRole" use:enhance={handleCreateRole} class="add-role">
                    <div class="add-role-top">
                        <label class="add-role-field"
                            >{$t('admin.roles.idLabel')}
                            <input
                                class="small-input"
                                name="name"
                                required
                                pattern={'[a-z][a-z0-9_]{1,30}'}
                                placeholder={$t('admin.roles.idPlaceholder')}
                                disabled={isCreatingRole}
                            />
                        </label>
                        <label class="add-role-field"
                            >{$t('admin.field.displayName')}
                            <input
                                class="small-input"
                                name="label"
                                placeholder={$t('admin.roles.labelPlaceholder')}
                                disabled={isCreatingRole}
                            />
                        </label>
                    </div>
                    <fieldset class="perms perms-create">
                        <legend>{$t('admin.roles.permissionsLegend')}</legend>
                        {#each data.permissions as p (p.key)}
                            <label class="perm perm-create">
                                <input type="checkbox" name="permissions" value={p.key} disabled={isCreatingRole} />
                                <span class="perm-content">
                                    <span>{p.label}</span>
                                    <code>{p.key}</code>
                                </span>
                            </label>
                        {/each}
                    </fieldset>
                    <div class="action-with-feedback">
                        <button class="btn" type="submit" disabled={isCreatingRole}>
                            {#if isCreatingRole}
                                <span class="spinner-small" aria-hidden="true"></span>
                            {/if}
                            {$t('admin.roles.create')}
                        </button>
                        {#if fb.scope === 'createRole'}
                            {#if fb.error}
                                <span class="inline-error" role="alert">{fb.error}</span>
                            {:else if fb.message}
                                <span class="inline-success" role="status">{fb.message}</span>
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
        transition: background-color 200ms ease, color 200ms ease;
    }

    :global(html.light-mode) :global(body),
    :global([data-theme='light']) :global(body),
    :global(.light) :global(body) {
        background: #f4f5f3;
        color: #111827;
    }

    button:focus,
    input:focus,
    select:focus,
    a:focus {
        outline: none;
    }

    button:focus-visible,
    input:focus-visible,
    select:focus-visible,
    a:focus-visible {
        outline: 2px solid rgba(255, 255, 255, 0.6);
        outline-offset: 2px;
    }

    :global(html.light-mode) button:focus-visible,
    :global(html.light-mode) input:focus-visible,
    :global(html.light-mode) select:focus-visible,
    :global(html.light-mode) a:focus-visible {
        outline-color: rgba(17, 24, 39, 0.6);
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
    :global(html.light-mode) .eyebrow {
        color: #64748b;
    }

    .topbar h1 {
        margin: 0;
        font-size: 1.25rem;
        font-weight: 400;
        letter-spacing: 0.04em;
        text-transform: uppercase;
        color: inherit;
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
    :global(html.light-mode) .who {
        color: #64748b;
    }

    .btn {
        border: 0;
        border-radius: 8px;
        background: #f4f1eb;
        color: #141414;
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
        transition: opacity 150ms ease, background-color 150ms ease, transform 120ms ease;
    }
    :global(html.light-mode) .btn {
        background: #111827;
        color: #ffffff;
    }
    .btn:hover:not(:disabled) {
        opacity: 0.85;
        transform: translateY(-1px);
    }
    .btn:active:not(:disabled) {
        transform: translateY(0);
    }
    .btn:disabled {
        opacity: 0.4;
        cursor: not-allowed;
    }
    .btn.small {
        padding: 6px 10px;
        font-size: 0.68rem;
    }
    .btn.ghost {
        background: rgba(255, 255, 255, 0.04);
        color: #97a5ad;
    }
    :global(html.light-mode) .btn.ghost {
        background: rgba(0, 0, 0, 0.04);
        color: #52606a;
    }
    .btn.ghost:hover:not(:disabled) {
        background: rgba(255, 255, 255, 0.08);
        color: #f5f7f8;
    }
    :global(html.light-mode) .btn.ghost:hover:not(:disabled) {
        background: rgba(0, 0, 0, 0.08);
        color: #111827;
    }
    .btn.danger-ghost {
        background: rgba(222, 132, 137, 0.1);
        color: #de8489;
    }
    :global(html.light-mode) .btn.danger-ghost {
        background: rgba(201, 81, 88, 0.1);
        color: #c95158;
    }
    .btn.danger-ghost:hover:not(:disabled) {
        background: rgba(222, 132, 137, 0.2);
    }
    :global(html.light-mode) .btn.danger-ghost:hover:not(:disabled) {
        background: rgba(201, 81, 88, 0.2);
    }
    .btn.danger {
        background: rgba(222, 132, 137, 0.15);
        color: #de8489;
    }
    :global(html.light-mode) .btn.danger {
        background: rgba(201, 81, 88, 0.15);
        color: #c95158;
    }
    .btn.danger:hover:not(:disabled) {
        background: rgba(222, 132, 137, 0.28);
    }
    :global(html.light-mode) .btn.danger:hover:not(:disabled) {
        background: rgba(201, 81, 88, 0.28);
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
        text-transform: uppercase;
    }
    .banner.ok {
        background: rgba(108, 176, 159, 0.15);
        color: #6cb09f;
    }
    :global(html.light-mode) .banner.ok {
        background: rgba(46, 133, 110, 0.12);
        color: #2e856e;
    }
    .banner.err {
        background: rgba(222, 132, 137, 0.15);
        color: #de8489;
    }
    :global(html.light-mode) .banner.err {
        background: rgba(201, 81, 88, 0.12);
        color: #c95158;
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
        transition: background-color 200ms ease, box-shadow 200ms ease;
    }
    :global(html.light-mode) .card {
        background: #ffffff;
        box-shadow: 0 20px 48px rgba(0, 0, 0, 0.07);
    }
    .card h2 {
        margin: 0 0 16px;
        font-size: 0.95rem;
        font-weight: 400;
        letter-spacing: 0.06em;
        text-transform: uppercase;
        color: inherit;
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
    :global(html.light-mode) .count {
        background: rgba(0, 0, 0, 0.05);
        color: #64748b;
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
    :global(html.light-mode) th {
        color: #64748b;
    }
    td {
        padding: 10px;
        border-top: 1px solid rgba(255, 255, 255, 0.04);
        vertical-align: middle;
    }
    :global(html.light-mode) td {
        border-top-color: rgba(0, 0, 0, 0.05);
    }
    tr.self td {
        background: rgba(255, 255, 255, 0.02);
    }
    :global(html.light-mode) tr.self td {
        background: rgba(0, 0, 0, 0.02);
    }
    tr.row-loading td {
        opacity: 0.6;
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
        color: inherit;
        padding: 8px 12px;
        font-family: inherit;
        font-size: 0.76rem;
        font-weight: 300;
        letter-spacing: 0.04em;
        outline: none;
        transition: background-color 150ms ease;
    }
    :global(html.light-mode) .cell-input {
        background: rgba(0, 0, 0, 0.04);
    }
    .cell-input:focus {
        background: rgba(255, 255, 255, 0.08);
    }
    :global(html.light-mode) .cell-input:focus {
        background: rgba(0, 0, 0, 0.07);
    }
    .cell-input:disabled {
        opacity: 0.5;
        cursor: not-allowed;
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
    :global(html.light-mode) .select-cell option {
        background: #ffffff;
        color: #111827;
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
        text-transform: uppercase;
        margin: 6px 0 0;
    }
    :global(html.light-mode) .row-error {
        color: #c95158;
    }
    .row-success {
        color: #6cb09f;
        font-size: 0.68rem;
        font-weight: 300;
        letter-spacing: 0.02em;
        text-transform: uppercase;
        margin: 6px 0 0;
    }
    :global(html.light-mode) .row-success {
        color: #2e856e;
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
        text-transform: uppercase;
    }
    :global(html.light-mode) .inline-error {
        color: #c95158;
    }
    .inline-success {
        color: #6cb09f;
        font-size: 0.68rem;
        font-weight: 300;
        text-transform: uppercase;
    }
    :global(html.light-mode) .inline-success {
        color: #2e856e;
    }
    .muted {
        color: #97a5ad;
        font-weight: 300;
    }
    :global(html.light-mode) .muted {
        color: #64748b;
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
    :global(html.light-mode) .tag {
        background: rgba(0, 0, 0, 0.05);
        color: #64748b;
    }

    .adder {
        margin-top: 18px;
        border-top: 1px solid rgba(255, 255, 255, 0.06);
        padding-top: 14px;
    }
    :global(html.light-mode) .adder {
        border-top-color: rgba(0, 0, 0, 0.06);
    }
    .adder summary {
        cursor: pointer;
        color: inherit;
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
    :global(html.light-mode) .add-field {
        color: #64748b;
    }
    .add-field input,
    .add-field select {
        background: rgba(255, 255, 255, 0.04);
        border: 0;
        border-radius: 8px;
        color: inherit;
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
    :global(html.light-mode) .add-field input,
    :global(html.light-mode) .add-field select {
        background: rgba(0, 0, 0, 0.04);
    }
    .add-field input::placeholder {
        color: #64748b;
        text-transform: uppercase;
        letter-spacing: 0.04em;
    }
    :global(html.light-mode) .add-field input::placeholder {
        color: #94a3b8;
    }
    .add-field input:focus,
    .add-field select:focus {
        background: rgba(255, 255, 255, 0.08);
    }
    :global(html.light-mode) .add-field input:focus,
    :global(html.light-mode) .add-field select:focus {
        background: rgba(0, 0, 0, 0.07);
    }
    .add-field select option {
        background: #1a1a1a;
        color: #f5f7f8;
    }
    :global(html.light-mode) .add-field select option {
        background: #ffffff;
        color: #111827;
    }

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
    :global(html.light-mode) .role-card {
        background: rgba(0, 0, 0, 0.02);
    }
    .role-head {
        display: flex;
        align-items: center;
        gap: 8px;
    }
    .role-name {
        font-size: 0.82rem;
        font-weight: 400;
        color: inherit;
    }
    code {
        font-family: 'Fira Mono', ui-monospace, monospace;
        font-size: 0.82em;
        color: #97a5ad;
    }
    :global(html.light-mode) code {
        color: #64748b;
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
    :global(html.light-mode) .role-label {
        color: #64748b;
    }
    .role-label input {
        background: rgba(255, 255, 255, 0.04);
        border: 0;
        border-radius: 8px;
        color: inherit;
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
    :global(html.light-mode) .role-label input {
        background: rgba(0, 0, 0, 0.04);
    }
    .role-label input:focus {
        background: rgba(255, 255, 255, 0.08);
    }
    :global(html.light-mode) .role-label input:focus {
        background: rgba(0, 0, 0, 0.07);
    }
    .role-label input:disabled {
        opacity: 0.5;
        cursor: not-allowed;
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
    :global(html.light-mode) .perms {
        background: rgba(0, 0, 0, 0.02);
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
    :global(html.light-mode) .perms legend {
        color: #64748b;
    }
    .perm {
        display: flex;
        align-items: center;
        gap: 10px;
        font-size: 0.74rem;
        color: inherit;
        font-weight: 300;
        cursor: pointer;
        user-select: none;
    }
    .perm input[type='checkbox'] {
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
    :global(html.light-mode) .perm input[type='checkbox'] {
        background: rgba(0, 0, 0, 0.04);
        border-color: rgba(0, 0, 0, 0.2);
    }
    .perm input[type='checkbox']:checked {
        background: #f5f7f8;
        border-color: #f5f7f8;
    }
    :global(html.light-mode) .perm input[type='checkbox']:checked {
        background: #111827;
        border-color: #111827;
    }
    .perm input[type='checkbox']:checked::before {
        content: '';
        width: 4px;
        height: 8px;
        border: solid #141414;
        border-width: 0 2px 2px 0;
        transform: rotate(45deg);
        margin-top: -1px;
    }
    :global(html.light-mode) .perm input[type='checkbox']:checked::before {
        border-color: #ffffff;
    }
    .perm input[type='checkbox']:disabled {
        opacity: 0.4;
        cursor: not-allowed;
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
    :global(html.light-mode) .perm code {
        background: rgba(0, 0, 0, 0.03);
    }

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
    :global(html.light-mode) .add-role-field {
        color: #64748b;
    }
    .small-input {
        background: rgba(255, 255, 255, 0.04);
        border: 0;
        border-radius: 8px;
        color: inherit;
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
    :global(html.light-mode) .small-input {
        background: rgba(0, 0, 0, 0.04);
    }
    .small-input::placeholder {
        color: #64748b;
        text-transform: uppercase;
        letter-spacing: 0.04em;
    }
    :global(html.light-mode) .small-input::placeholder {
        color: #94a3b8;
    }
    .small-input:focus {
        background: rgba(255, 255, 255, 0.08);
    }
    :global(html.light-mode) .small-input:focus {
        background: rgba(0, 0, 0, 0.07);
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

    /* Spinner */
    .spinner-small {
        width: 10px;
        height: 10px;
        border: 1.5px solid currentColor;
        border-right-color: transparent;
        border-radius: 50%;
        display: inline-block;
        animation: spin 550ms linear infinite;
    }

    @keyframes spin {
        to {
            transform: rotate(360deg);
        }
    }

    /* Skeleton Loading */
    .skeleton-table {
        display: flex;
        flex-direction: column;
        gap: 10px;
        padding: 6px 0;
    }
    .skeleton-row {
        height: 38px;
        background: rgba(255, 255, 255, 0.03);
        border-radius: 8px;
        animation: skeleton-pulse 1.4s ease-in-out infinite;
    }
    :global(html.light-mode) .skeleton-row {
        background: rgba(0, 0, 0, 0.03);
    }
    .skeleton-row.header {
        height: 24px;
        width: 70%;
    }
    .skeleton-card {
        height: 340px;
        background: rgba(255, 255, 255, 0.02);
        border-radius: 10px;
        animation: skeleton-pulse 1.4s ease-in-out infinite;
    }
    :global(html.light-mode) .skeleton-card {
        background: rgba(0, 0, 0, 0.02);
    }

    @keyframes skeleton-pulse {
        0%,
        100% {
            opacity: 0.5;
        }
        50% {
            opacity: 1;
        }
    }
</style>