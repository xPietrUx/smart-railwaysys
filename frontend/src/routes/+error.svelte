<script lang="ts">
    import { onMount } from 'svelte';
    import { resolve } from '$app/paths';
    import { page } from '$app/stores';
    import LanguageSwitcher from '$lib/components/LanguageSwitcher.svelte';
    import { initLocale, t } from '$lib/i18n';

    let lightMode = false;

    onMount(() => {
        initLocale();
        lightMode = localStorage.getItem('smart-railway.theme') === 'light';
        document.documentElement.classList.toggle('light-mode', lightMode);
    });

    function toggleLightMode() {
        lightMode = !lightMode;
        document.documentElement.classList.toggle('light-mode', lightMode);
        localStorage.setItem('smart-railway.theme', lightMode ? 'light' : 'dark');
    }
</script>

<svelte:head>
    <link
        rel="stylesheet"
        href="https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined:opsz,wght,FILL,GRAD@20..48,100..700,0..1,-50..200"
    />
    <title>{$t('error.status', { status: $page.status })} — Smart Railway System</title>
</svelte:head>

<main>
    <section class="error-card" role="region" aria-labelledby="error-heading">
        <div class="top-actions">
            <button
                class="icon-button"
                type="button"
                on:click={toggleLightMode}
                aria-label={lightMode ? 'Włącz tryb ciemny' : 'Włącz tryb jasny'}
                title={lightMode ? 'Tryb ciemny' : 'Tryb jasny'}
                tabindex="0"
            >
                <span class="material-symbols-outlined" class:is-light={lightMode} aria-hidden="true">
                    {lightMode ? 'dark_mode' : 'light_mode'}
                </span>
            </button>
            <LanguageSwitcher />
        </div>

        <div class="error-badge">
            <span class="status-indicator" aria-hidden="true"></span>
            <p>{$t('error.status', { status: $page.status })}</p>
        </div>

        <h1 id="error-heading">{$t('error.title')}</h1>
        <span class="description">{$t('error.description')}</span>

        <a href={resolve('/')} class="home-btn" tabindex="0">
            <span class="material-symbols-outlined icon-inline" aria-hidden="true">arrow_back</span>
            <span>{$t('error.home')}</span>
        </a>
    </section>
</main>

<style>
    .material-symbols-outlined {
        font-family: 'Material Symbols Outlined' !important;
        font-weight: normal;
        font-style: normal;
        font-size: 19px;
        line-height: 1;
        display: inline-block;
        white-space: nowrap;
        direction: ltr;
        -webkit-font-smoothing: antialiased;
        font-feature-settings: 'liga';
        font-variation-settings: 'FILL' 0, 'wght' 200, 'GRAD' 0, 'opsz' 24;
        user-select: none;
        vertical-align: middle;
    }

    :global(html),
    :global(body) {
        height: 100%;
    }

    :global(body) {
        margin: 0;
        font-family: 'Inter Variable', Inter, sans-serif;
        font-weight: 300;
        background: #141414;
        color: #f5f7f8;
        transition: background-color 200ms ease, color 200ms ease;
    }

    :global(html.light-mode) :global(body),
    :global([data-theme='light']) :global(body),
    :global(.light) :global(body) {
        background: #f4f5f3;
        color: #111827;
    }

    a:focus,
    button:focus {
        outline: none;
    }

    a:focus-visible,
    button:focus-visible {
        outline: 2px solid rgba(255, 255, 255, 0.65);
        outline-offset: 3px;
        border-radius: 6px;
    }

    :global(html.light-mode) a:focus-visible,
    :global(html.light-mode) button:focus-visible {
        outline-color: rgba(17, 24, 39, 0.65);
    }

    main {
        min-height: 100dvh;
        display: grid;
        place-items: center;
        padding: 24px;
        box-sizing: border-box;
    }

    .error-card {
        position: relative;
        width: min(440px, 100%);
        box-sizing: border-box;
        padding: 38px 32px 34px;
        border-radius: 16px;
        background: rgba(20, 20, 20, 0.96);
        border: 1px solid rgba(255, 255, 255, 0.06);
        box-shadow: 0 24px 60px rgba(0, 0, 0, 0.65);
        transition: background-color 200ms ease, box-shadow 200ms ease, border-color 200ms ease;
    }

    :global(html.light-mode) .error-card {
        background: #ffffff;
        border-color: rgba(0, 0, 0, 0.08);
        box-shadow: 0 24px 60px rgba(0, 0, 0, 0.08);
    }

    .top-actions {
        position: absolute;
        top: 20px;
        right: 20px;
        display: flex;
        align-items: center;
        gap: 6px;
    }

    .icon-button {
        display: grid;
        place-items: center;
        width: 32px;
        height: 32px;
        padding: 0;
        border: 0;
        border-radius: 8px;
        background: transparent;
        color: #97a5ad;
        cursor: pointer;
        transition: color 150ms ease, background-color 150ms ease;
    }

    .icon-button:hover {
        color: #f5f7f8;
        background: rgba(255, 255, 255, 0.04);
    }

    :global(html.light-mode) .icon-button {
        color: #64748b;
    }

    :global(html.light-mode) .icon-button:hover {
        color: #111827;
        background: rgba(0, 0, 0, 0.04);
    }

    .material-symbols-outlined.is-light {
        transform: rotate(180deg);
    }

    .error-badge {
        display: inline-flex;
        align-items: center;
        gap: 8px;
        padding: 4px 10px;
        border-radius: 999px;
        background: rgba(222, 132, 137, 0.12);
        margin-bottom: 14px;
    }

    :global(html.light-mode) .error-badge {
        background: rgba(201, 81, 88, 0.1);
    }

    .status-indicator {
        width: 6px;
        height: 6px;
        border-radius: 50%;
        background: #de8489;
    }

    :global(html.light-mode) .status-indicator {
        background: #c95158;
    }

    p {
        margin: 0;
        color: #de8489;
        font-size: 0.68rem;
        font-weight: 400;
        letter-spacing: 0.08em;
        text-transform: uppercase;
    }

    :global(html.light-mode) p {
        color: #c95158;
    }

    h1 {
        margin: 0 0 10px;
        font-size: 1.15rem;
        font-weight: 400;
        letter-spacing: 0.04em;
        text-transform: uppercase;
        color: #ffffff;
    }

    :global(html.light-mode) h1 {
        color: #111827;
    }

    .description {
        display: block;
        color: #97a5ad;
        font-size: 0.78rem;
        font-weight: 300;
        line-height: 1.6;
        letter-spacing: 0.02em;
    }

    :global(html.light-mode) .description {
        color: #64748b;
    }

    .home-btn {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        margin-top: 24px;
        padding: 9px 16px;
        border-radius: 8px;
        background: #f4f1eb;
        color: #141414;
        font-size: 0.72rem;
        font-weight: 500;
        text-transform: uppercase;
        letter-spacing: 0.06em;
        text-decoration: none;
        transition: opacity 150ms ease, transform 120ms ease;
    }

    :global(html.light-mode) .home-btn {
        background: #111827;
        color: #ffffff;
    }

    .home-btn:hover {
        opacity: 0.85;
        transform: translateY(-1px);
    }

    .home-btn:active {
        transform: translateY(0);
    }

    .icon-inline {
        font-size: 16px;
    }
</style>