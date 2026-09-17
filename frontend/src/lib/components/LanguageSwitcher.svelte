<script lang="ts">
    import { locale, setLocale, t, type Locale } from '$lib/i18n';

    function toggleLocale() {
        const next: Locale = $locale === 'pl' ? 'en' : 'pl';
        setLocale(next);
    }
</script>

<svelte:head>
    <link
        rel="stylesheet"
        href="https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined:opsz,wght,FILL,GRAD@20..48,100..700,0..1,-50..200"
    />
</svelte:head>

<button
    type="button"
    class="icon-button"
    on:click={toggleLocale}
    title={$t('language.label')}
    aria-label={$t('language.label')}
    tabindex="0"
>
    <span class="material-symbols-outlined" aria-hidden="true">translate</span>
    <span class="lang-text">{$locale.toUpperCase()}</span>
</button>

<style>
    .icon-button {
        display: inline-flex;
        align-items: center;
        gap: 4px;
        height: 32px;
        padding: 0 8px;
        border: 0;
        border-radius: 8px;
        background: transparent;
        color: #97a5ad;
        cursor: pointer;
        font-family: 'Inter Variable', Inter, sans-serif;
        font-size: 0.68rem;
        font-weight: 400;
        letter-spacing: 0.08em;
        text-transform: uppercase;
        transition: color 150ms ease, background-color 150ms ease;
    }

    .icon-button:hover {
        color: #f5f7f8;
        background: rgba(255, 255, 255, 0.04);
    }

    :global(html.light-mode) .icon-button,
    :global([data-theme='light']) .icon-button,
    :global(.light) .icon-button {
        color: #64748b;
    }

    :global(html.light-mode) .icon-button:hover,
    :global([data-theme='light']) .icon-button:hover,
    :global(.light) .icon-button:hover {
        color: #111827;
        background: rgba(0, 0, 0, 0.04);
    }

    .material-symbols-outlined {
        font-size: 17px;
    }

    .icon-button:focus {
        outline: none;
    }

    .icon-button:focus-visible {
        outline: 2px solid rgba(255, 255, 255, 0.6);
        outline-offset: 1px;
    }

    :global(html.light-mode) .icon-button:focus-visible {
        outline-color: rgba(17, 24, 39, 0.6);
    }
</style>