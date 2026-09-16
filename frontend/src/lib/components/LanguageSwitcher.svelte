<script lang="ts">
    import { locale, setLocale, t, type Locale } from '$lib/i18n';

    function choose(nextLocale: Locale) {
        setLocale(nextLocale);
    }
</script>

<div class="language-switcher" role="group" aria-label={$t('language.label')}>
    <button
        type="button"
        class:active={$locale === 'pl'}
        aria-pressed={$locale === 'pl'}
        title={$t('language.polish')}
        tabindex="0"
        on:click={() => choose('pl')}
    >
        PL
    </button>
    <button
        type="button"
        class:active={$locale === 'en'}
        aria-pressed={$locale === 'en'}
        title={$t('language.english')}
        tabindex="0"
        on:click={() => choose('en')}
    >
        EN
    </button>
</div>

<style>
    .language-switcher {
        display: inline-flex;
        align-items: center;
        padding: 3px;
        border-radius: 8px;
        background: rgba(255, 255, 255, 0.04);
        border: 0;
        box-sizing: border-box;
        font-family: 'Inter Variable', Inter, sans-serif;
        transition: background-color 200ms ease;
    }

    :global(html.light-mode) .language-switcher,
    :global([data-theme='light']) .language-switcher,
    :global(.light) .language-switcher {
        background: rgba(0, 0, 0, 0.04);
    }

    button {
        border: 0;
        border-radius: 6px;
        padding: 4px 8px;
        background: transparent;
        color: #97a5ad;
        font-family: inherit;
        font-size: 0.68rem;
        font-weight: 400;
        letter-spacing: 0.08em;
        text-transform: uppercase;
        cursor: pointer;
        line-height: 1;
        transition: color 150ms ease, background-color 150ms ease, opacity 150ms ease;
    }

    :global(html.light-mode) button,
    :global([data-theme='light']) button,
    :global(.light) button {
        color: #64748b;
    }

    button:hover:not(.active) {
        color: #f5f7f8;
        background: rgba(255, 255, 255, 0.04);
    }

    :global(html.light-mode) button:hover:not(.active),
    :global([data-theme='light']) button:hover:not(.active),
    :global(.light) button:hover:not(.active) {
        color: #111827;
        background: rgba(0, 0, 0, 0.04);
    }

    button.active {
        background: #f4f1eb;
        color: #141414;
        font-weight: 500;
    }

    :global(html.light-mode) button.active,
    :global([data-theme='light']) button.active,
    :global(.light) button.active {
        background: #111827;
        color: #ffffff;
    }

    button:focus {
        outline: none;
    }

    button:focus-visible {
        outline: 2px solid rgba(255, 255, 255, 0.6);
        outline-offset: 1px;
    }

    :global(html.light-mode) button:focus-visible,
    :global([data-theme='light']) button:focus-visible,
    :global(.light) button:focus-visible {
        outline-color: rgba(17, 24, 39, 0.6);
    }
</style>