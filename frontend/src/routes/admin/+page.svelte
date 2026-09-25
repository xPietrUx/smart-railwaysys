<script lang="ts">
    import { enhance } from '$app/forms';
    import { goto } from '$app/navigation';
    import { onMount } from 'svelte';
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

    let lightMode = false;

    // Walidacja - Dodawanie użytkownika
    let newUserEmail = '';
    let newUserPassword = '';
    let newUserTouched = false;
    $: newUserEmailValid = /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(newUserEmail);
    $: newUserPasswordValid = newUserPassword.length >= 8;

    // Walidacja - Dodawanie roli
    let newRoleName = '';
    let newRoleLabel = '';
    let newRoleTouched = false;
    $: newRoleNameValid = /^[a-z][a-z0-9_]{1,30}$/.test(newRoleName);
    $: newRoleLabelValid = newRoleLabel.trim().length > 0;

    // Modal usuwania roli
    let roleToDelete: Role | null = null;
    let isDeletingRole = false;

    onMount(() => {
        lightMode = localStorage.getItem('smart-railway.theme') === 'light';
        document.documentElement.classList.toggle('light-mode', lightMode);
    });

    function toggleLightMode() {
        lightMode = !lightMode;
        document.documentElement.classList.toggle('light-mode', lightMode);
        localStorage.setItem('smart-railway.theme', lightMode ? 'light' : 'dark');
    }

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

    const handleCreateUser: SubmitFunction = ({ cancel }) => {
        newUserTouched = true;
        if (!newUserEmailValid || !newUserPasswordValid) {
            cancel();
            return;
        }
        isCreatingUser = true;
        return async ({ update }) => {
            try {
                await update();
            } finally {
                isCreatingUser = false;
                newUserTouched = false;
                newUserEmail = '';
                newUserPassword = '';
            }
        };
    };

    const handleRoleForm: SubmitFunction = ({ formData }) => {
        const name = formData.get('name')?.toString();
        if (name) submittingRoles = new Set(submittingRoles.add(name));
        return async ({ result, update }) => {
            try {
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

const handleRoleDeleteForm: SubmitFunction = (params) => {
        isDeletingRole = true;
        const nextPromise = handleRoleForm(params);
        
        return async (updateParams) => {
            try {
                const next = await nextPromise;
                
                if (typeof next === 'function') {
                    await next(updateParams);
                }
            } finally {
                isDeletingRole = false;
                roleToDelete = null;
            }
        };
    };

    const handleCreateRole: SubmitFunction = ({ cancel }) => {
        newRoleTouched = true;
        if (!newRoleNameValid || !newRoleLabelValid) {
            cancel();
            return;
        }
        isCreatingRole = true;
        return async ({ result, update }) => {
            try {
                await update({ invalidateAll: false });
                if (result.type === 'success' && result.data) {
                    const payload = result.data as { role?: Role };
                    if (payload.role) {
                        data = { ...data, roles: sortRoles([...data.roles, payload.role]) };
                        newRoleName = '';
                        newRoleLabel = '';
                        newRoleTouched = false;
                    }
                }
            } finally {
                isCreatingRole = false;
            }
        };
    };

    function handleBackdropClick(event: MouseEvent) {
        if (event.target === event.currentTarget) {
            goto('/panel');
        }
    }

    function handleKeydown(event: KeyboardEvent) {
        if (event.key === 'Escape') {
            if (roleToDelete) {
                roleToDelete = null;
            } else {
                goto('/panel');
            }
        }
    }

    $: canManageRoles = data.canManageRoles;
</script>

<svelte:head>
    <link
        rel="stylesheet"
        href="https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined:opsz,wght,FILL,GRAD@20..48,100..700,0..1,-50..200"
    />
    <title>{$t('admin.headTitle')}</title>
</svelte:head>

<svelte:window on:keydown={handleKeydown} />

<!-- svelte-ignore a11y_click_events_have_key_events a11y_no_static_element_interactions -->
<div class="overlay" on:click={handleBackdropClick}>
    <div class="modal admin-modal" role="dialog" aria-modal="true" aria-label={$t('admin.title')}>
        
        <header class="modal-header">
            <div>
                <p class="modal-label">Smart Railway System</p>
                <h2>{$t('admin.title')}</h2>
            </div>
            
            <div class="top-nav">
                <span class="who" title={data.me.email}>{data.me.email}</span>
                <button
                    class="btn ghost small icon-btn"
                    type="button"
                    on:click={toggleLanguage}
                    aria-label={$locale === 'pl' ? 'Zmień język na angielski' : 'Change language to Polish'}
                    title={$locale === 'pl' ? 'English' : 'Polski'}
                >
                    <span class="material-symbols-outlined" aria-hidden="true">language</span>
                </button>
                <button
                    class="btn ghost small icon-btn"
                    type="button"
                    on:click={toggleLightMode}
                    aria-label={lightMode ? 'Włącz tryb ciemny' : 'Włącz tryb jasny'}
                    title={lightMode ? 'Tryb ciemny' : 'Tryb jasny'}
                >
                    <span class="material-symbols-outlined" class:is-light={lightMode} aria-hidden="true">
                        {lightMode ? 'dark_mode' : 'light_mode'}
                    </span>
                </button>
                <form method="POST" action="/wyloguj">
                    <button class="btn danger-ghost small" type="submit" tabindex="0">
                        <span class="material-symbols-outlined" aria-hidden="true">logout</span>
                        {$t('header.logout')}
                    </button>
                </form>
                <a
                    class="close-btn"
                    data-sveltekit-preload-data="off"
                    href="/panel"
                    title={$t('admin.nav.simulation')}
                    aria-label={$t('admin.nav.simulation')}
                >
                    <span class="material-symbols-outlined" aria-hidden="true">close</span>
                </a>
            </div>
        </header>

        <div class="modal-body">
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

            <div class="admin-content">
                <div class="top-split">
                    <!-- ============================ UŻYTKOWNICY ============================ -->
                    <section class="admin-section users-section">
                        <h3>{$t('admin.users.heading')} <span class="count">{data.users.length}</span></h3>

                        {#if isLoadingData}
                            <div class="skeleton-table">
                                <div class="skeleton-row header"></div>
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
                                                <td class="muted date-cell">
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
                            <form method="POST" action="?/createUser" use:enhance={handleCreateUser} class="add-user-form" novalidate>
                                <div class="add-user-fields">
                                    <label class="add-field">
                                        <span>{$t('admin.field.email')}</span>
                                        <input
                                            name="email"
                                            type="email"
                                            bind:value={newUserEmail}
                                            class:is-invalid={newUserTouched && !newUserEmailValid}
                                            placeholder="nowy@smartrailway.pl"
                                            disabled={isCreatingUser}
                                        />
                                        {#if newUserTouched && !newUserEmailValid}
                                            <span class="field-error-msg">{$locale === 'pl' ? 'Wymagany poprawny adres e-mail.' : 'Valid email is required.'}</span>
                                        {/if}
                                    </label>
                                    <label class="add-field">
                                        <span>{$t('admin.field.password')}</span>
                                        <input
                                            name="password"
                                            type="password"
                                            bind:value={newUserPassword}
                                            class:is-invalid={newUserTouched && !newUserPasswordValid}
                                            placeholder={$t('admin.users.minChars')}
                                            disabled={isCreatingUser}
                                        />
                                        {#if newUserTouched && !newUserPasswordValid}
                                            <span class="field-error-msg">{$locale === 'pl' ? 'Wymagane min. 8 znaków.' : 'Min. 8 characters required.'}</span>
                                        {/if}
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

                    {#if canManageRoles}
                        <section class="admin-section create-role-section">
                            <h3>{$t('admin.roles.addSummary')}</h3>
                            <form method="POST" action="?/createRole" use:enhance={handleCreateRole} class="add-role" novalidate>
                                <div class="add-role-top">
                                    <label class="add-role-field">
                                        {$t('admin.roles.idLabel')}
                                        <input
                                            class="small-input"
                                            class:is-invalid={newRoleTouched && !newRoleNameValid}
                                            name="name"
                                            bind:value={newRoleName}
                                            placeholder={$t('admin.roles.idPlaceholder')}
                                            disabled={isCreatingRole}
                                        />
                                        {#if newRoleTouched && !newRoleNameValid}
                                            <span class="field-error-msg">{$locale === 'pl' ? 'Tylko małe litery, cyfry i znak "_".' : 'Lowercase letters, numbers, and "_" only.'}</span>
                                        {/if}
                                    </label>
                                    <label class="add-role-field">
                                        {$t('admin.field.displayName')}
                                        <input
                                            class="small-input"
                                            class:is-invalid={newRoleTouched && !newRoleLabelValid}
                                            name="label"
                                            bind:value={newRoleLabel}
                                            placeholder={$t('admin.roles.labelPlaceholder')}
                                            disabled={isCreatingRole}
                                        />
                                        {#if newRoleTouched && !newRoleLabelValid}
                                            <span class="field-error-msg">{$locale === 'pl' ? 'To pole jest wymagane.' : 'This field is required.'}</span>
                                        {/if}
                                    </label>
                                </div>
                                <fieldset class="perms perms-create">
                                    <legend>{$t('admin.roles.permissionsLegend')}</legend>
                                    <div class="perms-grid">
                                        {#each data.permissions as p (p.key)}
                                            <label class="perm perm-create">
                                                <input type="checkbox" name="permissions" value={p.key} disabled={isCreatingRole} />
                                                <span class="perm-content">
                                                    <span>{p.label}</span>
                                                    <code>{p.key}</code>
                                                </span>
                                            </label>
                                        {/each}
                                    </div>
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
                        </section>
                    {/if}
                </div>

                <div class="divider"></div>

                <!-- ============================ ROLE ============================ -->
                <section class="admin-section">
                    <h3>{$t('admin.roles.heading')} <span class="count">{data.roles.length}</span></h3>
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
                        </div>
                    {:else}
                        <div class="roles-grid">
                            {#each data.roles as r (r.name)}
                                {@const isRoleBusy = submittingRoles.has(r.name) || (roleToDelete?.name === r.name && isDeletingRole)}
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
                                        <input name="label" value={r.label} required disabled={!canManageRoles || r.is_system || isRoleBusy} />
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
                                                    {#if submittingRoles.has(r.name)}
                                                        <span class="spinner-small" aria-hidden="true"></span>
                                                    {/if}
                                                    {$t('admin.actions.save')}
                                                </button>
                                                <button
                                                    class="btn small danger"
                                                    type="button"
                                                    disabled={isRoleBusy}
                                                    on:click={(e) => {
                                                        e.preventDefault();
                                                        roleToDelete = r;
                                                    }}>{$t('admin.actions.delete')}</button>
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
                </section>
            </div>
        </div>
    </div>
</div>

{#if roleToDelete}
    <!-- svelte-ignore a11y_click_events_have_key_events a11y_no_static_element_interactions -->
    <div class="overlay confirm-overlay" on:click={() => (roleToDelete = null)}>
        <div class="modal confirm-modal" role="dialog" aria-modal="true" on:click|stopPropagation>
            <header class="modal-header">
                <h2>{$locale === 'pl' ? 'Potwierdź usunięcie' : 'Confirm deletion'}</h2>
                <button class="close-btn" type="button" on:click={() => (roleToDelete = null)}>
                    <span class="material-symbols-outlined" aria-hidden="true">close</span>
                </button>
            </header>
            <div class="modal-body confirm-body">
                <p>{$t('admin.roles.confirmDelete', { role: roleToDelete.label })}</p>
                
                <form method="POST" action="?/deleteRole" use:enhance={handleRoleDeleteForm} class="confirm-actions">
                    <input type="hidden" name="name" value={roleToDelete.name} />
                    <button type="button" class="btn ghost" on:click={() => (roleToDelete = null)} disabled={isDeletingRole}>
                        {$locale === 'pl' ? 'Anuluj' : 'Cancel'}
                    </button>
                    <button type="submit" class="btn danger" disabled={isDeletingRole}>
                        {#if isDeletingRole}
                            <span class="spinner-small" aria-hidden="true"></span>
                        {/if}
                        {$t('admin.actions.delete')}
                    </button>
                </form>
            </div>
        </div>
    </div>
{/if}

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
    }

    .overlay {
        position: fixed;
        inset: 0;
        z-index: 200;
        background: rgba(0, 0, 0, 0.7);
        backdrop-filter: blur(8px);
        -webkit-backdrop-filter: blur(8px);
        display: flex;
        align-items: center;
        justify-content: center;
        padding: 20px;
        box-sizing: border-box;
    }

    .modal {
        --modal-bg: rgba(20, 20, 20, 0.96);
        --modal-shadow: 0 24px 60px rgba(0, 0, 0, 0.7);
        --modal-title: #ffffff;
        --modal-text: #f5f7f8;
        --modal-muted: #97a5ad;
        --modal-submuted: #64748b;
        --input-bg: rgba(255, 255, 255, 0.04);
        --input-bg-focus: rgba(255, 255, 255, 0.08);
        --option-bg: #1a1a1a;
        --option-color: #f5f7f8;
        
        width: 1400px;
        height: 90vh;
        max-width: calc(100vw - 32px);
        max-height: calc(100vh - 32px);

        display: flex;
        flex-direction: column;
        background: var(--modal-bg);
        border-radius: 14px;
        box-shadow: var(--modal-shadow);
        font-family: 'Inter Variable', Inter, sans-serif;
        font-weight: 300;
        color: var(--modal-text);
        box-sizing: border-box;
        position: relative;
        overflow: hidden;
        transition: background-color 200ms ease, color 200ms ease;
    }

    :global(html.light-mode) .modal,
    :global([data-theme='light']) .modal,
    :global(.light) .modal {
        --modal-bg: rgba(244, 245, 243, 0.98);
        --modal-shadow: 0 24px 60px rgba(0, 0, 0, 0.12);
        --modal-title: #111827;
        --modal-text: #1f2933;
        --modal-muted: #52606a;
        --modal-submuted: #8c9ba5;
        --input-bg: rgba(0, 0, 0, 0.04);
        --input-bg-focus: rgba(0, 0, 0, 0.07);
        --option-bg: #ffffff;
        --option-color: #1f2937;
    }

    .modal-header {
        display: flex;
        justify-content: space-between;
        align-items: flex-start;
        gap: 12px;
        padding: 24px 28px 20px;
        flex-shrink: 0;
    }

  

    .modal-label {
        margin: 0 0 6px;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        font-size: 0.66rem;
        font-weight: 300;
        color: var(--modal-muted);
    }

    .modal-header h2 {
        margin: 0;
        font-size: 1.15rem;
        font-weight: 400;
        letter-spacing: 0.04em;
        text-transform: uppercase;
        color: var(--modal-title);
    }

    .top-nav {
        display: flex;
        align-items: center;
        gap: 12px;
        flex-wrap: wrap;
    }
    
    .top-nav form {
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
        color: var(--modal-muted);
        margin-right: 8px;
    }

    .icon-btn {
        padding: 6px 10px;
    }

    .close-btn {
        border: 0;
        background: transparent !important;
        color: var(--modal-muted);
        width: 32px;
        height: 32px;
        border-radius: 8px;
        padding: 0;
        display: flex;
        align-items: center;
        justify-content: center;
        cursor: pointer;
        flex-shrink: 0;
        transition: color 150ms ease, opacity 150ms ease;
        margin-left: 6px;
        text-decoration: none;
        opacity: 0.4;
    }

    .close-btn:hover {
        color: var(--modal-title);
        opacity: 1;
    }

    .close-btn .material-symbols-outlined {
        font-size: 24px;
    }

    .modal-body {
        padding: 24px 28px;
        overflow-y: auto;
        flex: 1;
        display: flex;
        flex-direction: column;
        scrollbar-width: thin;
        scrollbar-color: rgba(255, 255, 255, 0.15) transparent;
    }

    :global(html.light-mode) .modal-body {
        scrollbar-color: rgba(0, 0, 0, 0.15) transparent;
    }

    .modal-body::-webkit-scrollbar {
        width: 6px;
    }

    .modal-body::-webkit-scrollbar-thumb {
        background: rgba(255, 255, 255, 0.15);
        border-radius: 999px;
    }

    :global(html.light-mode) .modal-body::-webkit-scrollbar-thumb {
        background: rgba(0, 0, 0, 0.15);
    }

    .admin-content {
        display: flex;
        flex-direction: column;
        gap: 32px;
    }

    .top-split {
        display: grid;
        grid-template-columns: 2fr 1fr;
        gap: 32px;
        align-items: start;
    }

    @media (max-width: 1024px) {
        .top-split {
            grid-template-columns: 1fr;
        }
    }

    .admin-section h3 {
        margin: 0 0 16px;
        font-size: 0.9rem;
        font-weight: 400;
        letter-spacing: 0.06em;
        text-transform: uppercase;
        color: var(--modal-title);
        display: flex;
        align-items: center;
        gap: 10px;
    }

    .create-role-section {
        background: rgba(255, 255, 255, 0.02);
        padding: 16px;
        border-radius: 12px;
    }

    :global(html.light-mode) .create-role-section {
        background: rgba(0, 0, 0, 0.02);
    }

    .divider {
        width: 100%;
        height: 1px;
        background: rgba(255, 255, 255, 0.06);
        margin: 10px 0;
    }

    :global(html.light-mode) .divider {
        background: rgba(0, 0, 0, 0.06);
    }

    /* Guziki */
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
        opacity: 1;
        transition: opacity 150ms ease, background-color 150ms ease;
    }
    :global(html.light-mode) .btn {
        background: #111827;
        color: #ffffff;
    }
    .btn:hover:not(:disabled) {
        opacity: 0.85;
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
        color: var(--modal-muted);
    }
    :global(html.light-mode) .btn.ghost {
        background: rgba(0, 0, 0, 0.04);
        color: var(--modal-muted);
    }
    .btn.ghost:hover:not(:disabled) {
        background: rgba(255, 255, 255, 0.08);
        color: var(--modal-text);
    }
    :global(html.light-mode) .btn.ghost:hover:not(:disabled) {
        background: rgba(0, 0, 0, 0.08);
        color: var(--modal-title);
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
        margin-bottom: 24px;
        font-size: 0.74rem;
        font-weight: 300;
        letter-spacing: 0.02em;
        display: flex;
        align-items: center;
        gap: 8px;
        text-transform: uppercase;
        flex-shrink: 0;
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

    .count {
        font-size: 0.66rem;
        font-weight: 400;
        letter-spacing: 0.06em;
        color: var(--modal-muted);
        background: rgba(255, 255, 255, 0.05);
        border-radius: 999px;
        padding: 2px 8px;
    }
    :global(html.light-mode) .count {
        background: rgba(0, 0, 0, 0.05);
        color: var(--modal-muted);
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
        color: var(--modal-muted);
        font-size: 0.66rem;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        padding: 0 10px 12px;
        white-space: nowrap;
    }
    td {
        padding: 10px;
        vertical-align: middle;
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
        background: var(--input-bg);
        border-radius: 8px;
        color: inherit;
        padding: 8px 12px;
        font-family: inherit;
        font-size: 0.76rem;
        font-weight: 300;
        letter-spacing: 0.04em;
        outline: none;
        transition: background-color 150ms ease, border-color 150ms ease;
    }
    .cell-input:focus {
        background: var(--input-bg-focus);
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
        background: var(--option-bg);
        color: var(--option-color);
    }
    
    .is-invalid {
        background: rgba(222, 132, 137, 0.06) !important;
    }
    :global(html.light-mode) .is-invalid {
        background: rgba(201, 81, 88, 0.06) !important;
    }

    .field-error-msg {
        display: block;
        color: #de8489;
        font-size: 0.64rem;
        margin-top: 4px;
        font-weight: 400;
        letter-spacing: 0.02em;
        text-transform: uppercase;
    }
    :global(html.light-mode) .field-error-msg {
        color: #c95158;
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
        color: var(--modal-muted);
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
        color: var(--modal-muted);
        background: rgba(255, 255, 255, 0.05);
        border-radius: 999px;
        padding: 2px 6px;
    }
    :global(html.light-mode) .tag {
        background: rgba(0, 0, 0, 0.05);
    }
    .date-cell {
        white-space: nowrap;
    }

    .adder {
        margin-top: 18px;
        padding-top: 14px;
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
        color: var(--modal-muted);
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
        color: var(--modal-muted);
        font-weight: 300;
        flex: 1;
        min-width: 220px;
    }
    .add-field input,
    .add-field select {
        background: var(--input-bg);
        border: 1px solid transparent;
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
        transition: background-color 150ms ease, border-color 150ms ease;
    }
    .add-field input::placeholder {
        color: var(--modal-submuted);
        text-transform: uppercase;
        letter-spacing: 0.04em;
    }
    .add-field input:focus,
    .add-field select:focus {
        background: var(--input-bg-focus);
    }
    .add-field select option {
        background: var(--option-bg);
        color: var(--option-color);
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
        color: var(--modal-muted);
    }
    .role-label {
        display: flex;
        flex-direction: column;
        gap: 6px;
        font-size: 0.66rem;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        color: var(--modal-muted);
        font-weight: 300;
    }
    .role-label input {
        background: var(--input-bg);
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
        transition: border-color 150ms ease;
    }
    .role-label input:focus {
        background: var(--input-bg-focus);
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
        color: var(--modal-muted);
        padding: 0 4px;
        font-weight: 300;
        margin-bottom: 4px;
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
    }
    .perm input[type='checkbox']:checked {
        background: #f5f7f8;
    }
    :global(html.light-mode) .perm input[type='checkbox']:checked {
        background: #111827;
    }
    .perm input[type='checkbox']:checked::before {
        content: '';
        width: 4px;
        height: 8px;

        transform: rotate(45deg);
        margin-top: -1px;
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
        background: rgba(255, 255, 255, 0.03);
        padding: 1px 4px;
        border-radius: 4px;
    }
    :global(html.light-mode) .perm code {
        background: rgba(0, 0, 0, 0.03);
    }

    .add-role {
        margin-top: 0;
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
        color: var(--modal-muted);
        font-weight: 300;
        flex: 1;
        min-width: 140px;
    }
    .small-input {
        background: var(--input-bg);
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
        transition: background-color 150ms ease, border-color 150ms ease;
    }
    .small-input::placeholder {
        color: var(--modal-submuted);
        text-transform: uppercase;
        letter-spacing: 0.04em;
    }
    .small-input:focus {
        background: var(--input-bg-focus);
    }

    .perms-create {
        width: 100%;
        box-sizing: border-box;
    }
    
    .perms-grid {
        display: grid;
        grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
        gap: 12px;
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

    /* Modal usunięcia roli */
    .confirm-overlay {
        z-index: 300;
        background: rgba(0, 0, 0, 0.8);
    }

    .confirm-modal {
        width: 440px;
        height: auto;
        min-height: auto;
        max-height: none;
    }

    .confirm-body {
        padding-bottom: 24px;
        overflow-y: visible;
    }

    .confirm-body p {
        margin: 0 0 24px;
        font-size: 0.92rem;
        line-height: 1.5;
        color: var(--modal-text);
        font-weight: 300;
    }

    .confirm-actions {
        display: flex;
        justify-content: flex-end;
        gap: 12px;
        margin: 0;
        padding-top: 20px;
        border-top: 1px solid rgba(255, 255, 255, 0.06);
    }
    
    :global(html.light-mode) .confirm-actions {
        border-top-color: rgba(0, 0, 0, 0.06);
    }

    .spinner-small {
        width: 10px;
        height: 10px;
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