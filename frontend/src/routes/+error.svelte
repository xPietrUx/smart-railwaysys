<script lang="ts">
    import { onMount } from 'svelte';
    import { resolve } from '$app/paths';
    import { page } from '$app/stores';
    import LanguageSwitcher from '$lib/components/LanguageSwitcher.svelte';
    import { initLocale, t } from '$lib/i18n';

    onMount(initLocale);
</script>

<svelte:head>
    <title>{$t('error.status', { status: $page.status })} — Smart Railway System</title>
</svelte:head>

<main>
    <section class="error-card">
        <div class="switcher"><LanguageSwitcher /></div>
        <p>{$t('error.status', { status: $page.status })}</p>
        <h1>{$t('error.title')}</h1>
        <span>{$t('error.description')}</span>
        <a href={resolve('/')}>{$t('error.home')}</a>
    </section>
</main>

<style>
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
        padding: 32px;
        border: 0;
        border-radius: 14px;
        background: rgba(20, 20, 20, 0.96);
        box-shadow: 0 24px 60px rgba(0, 0, 0, 0.7);
    }

    .switcher {
        position: absolute;
        top: 20px;
        right: 20px;
    }

    p {
        margin: 0 0 6px;
        color: #97a5ad;
        font-size: 0.68rem;
        font-weight: 300;
        letter-spacing: 0.08em;
        text-transform: uppercase;
    }

    h1 {
        margin: 0 0 12px;
        font-size: 1.15rem;
        font-weight: 400;
        letter-spacing: 0.04em;
        text-transform: uppercase;
        color: #ffffff;
    }

    span {
        display: block;
        color: #97a5ad;
        font-size: 0.78rem;
        font-weight: 300;
        line-height: 1.5;
        letter-spacing: 0.02em;
    }

    a {
        display: inline-block;
        margin-top: 24px;
        padding: 9px 16px;
        border-radius: 8px;
        background: #f4f1eb;
        color: #141414;
        font-size: 0.74rem;
        font-weight: 500;
        text-transform: uppercase;
        letter-spacing: 0.06em;
        text-decoration: none;
        transition: opacity 150ms ease;
    }

    a:hover {
        opacity: 0.85;
    }
</style>