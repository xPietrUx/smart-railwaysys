<script lang="ts">
    import { page } from '$app/stores';
    import { onMount } from 'svelte';
    import { locale, setLocale, t } from '$lib/i18n';
    import type { ConnectionStatus, LiveSnapshot } from '$lib/services/live';
    import { clearTrains } from '$lib/services/simulation';
    import type { HighlightFilter } from '$lib/types/selection';
    import type { TrainStatus } from '$lib/types/train';

    export let snapshot: LiveSnapshot;
    export let status: ConnectionStatus;
    export let apiBaseUrl: string;
    export let highlight: HighlightFilter | null = null;
    export let readOnly = false;
    export let user: { email: string; role: string; permissions: string[] } | null = null;

    $: isGuest = user?.role === 'guest';
    $: isAdmin = user?.permissions?.includes('users.manage') ?? false;

    let lightMode = false;
    let isCollapsed = false;
    let navElement: HTMLElement;

    function toggleCollapse() {
        isCollapsed = !isCollapsed;
    }

    function toggleTrainFilter(trainStatus: TrainStatus) {
        highlight =
            highlight?.kind === 'train-status' && highlight.status === trainStatus
                ? null
                : { kind: 'train-status', status: trainStatus };
    }

    function toggleIncidentFilter() {
        highlight = highlight?.kind === 'incidents' ? null : { kind: 'incidents' };
    }

    function toggleLanguage() {
        setLocale($locale === 'pl' ? 'en' : 'pl');
    }

    function toggleLightMode() {
        lightMode = !lightMode;
        document.documentElement.classList.toggle('light-mode', lightMode);
        localStorage.setItem('smart-railway.theme', lightMode ? 'light' : 'dark');
    }

    onMount(() => {
        lightMode = localStorage.getItem('smart-railway.theme') === 'light';
        document.documentElement.classList.toggle('light-mode', lightMode);
    });

    onMount(() => {
        if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) return;

        let cancelled = false;
        let cleanup: (() => void) | undefined;

        void Promise.all([
            import('gsap'),
            import('gsap/SplitText'),
            import('gsap/ScrambleTextPlugin')
        ]).then(([gsapModule, splitTextModule, scrambleModule]) => {
            if (cancelled || !navElement) return;

            const { gsap } = gsapModule;
            const { SplitText } = splitTextModule;
            const { ScrambleTextPlugin } = scrambleModule;
            gsap.registerPlugin(SplitText, ScrambleTextPlugin);

            const effects = [...navElement.querySelectorAll<HTMLElement>('.scrambled-text')].map(
                (element) => {
                    const split = SplitText.create(element, {
                        type: 'chars',
                        charsClass: 'scrambled-char'
                    });

                    split.chars.forEach((character) => {
                        gsap.set(character, { attr: { 'data-content': character.textContent ?? '' } });
                    });

                    const handleMove = (event: PointerEvent) => {
                        const radius = 42;
                        const duration = 1.2;

                        split.chars.forEach((character) => {
                            const { left, top, width, height } = character.getBoundingClientRect();
                            const distance = Math.hypot(
                                event.clientX - (left + width / 2),
                                event.clientY - (top + height / 2)
                            );

                            if (distance < radius) {
                                gsap.to(character, {
                                    overwrite: true,
                                    duration: duration * (1 - distance / radius),
                                    scrambleText: {
                                        text: character.getAttribute('data-content') ?? '',
                                        chars: '.:',
                                        speed: 0.5
                                    },
                                    ease: 'none'
                                });
                            }
                        });
                    };

                    const handleLeave = () => {
                        gsap.killTweensOf(split.chars);
                        split.chars.forEach((character) => {
                            character.textContent = character.getAttribute('data-content') ?? '';
                        });
                    };

                    element.addEventListener('pointermove', handleMove);
                    element.addEventListener('pointerleave', handleLeave);
                    return { element, split, handleMove, handleLeave };
                }
            );

            cleanup = () => {
                effects.forEach(({ element, split, handleMove, handleLeave }) => {
                    element.removeEventListener('pointermove', handleMove);
                    element.removeEventListener('pointerleave', handleLeave);
                    gsap.killTweensOf(split.chars);
                    split.revert();
                });
            };
        });

        return () => {
            cancelled = true;
            cleanup?.();
        };
    });

    $: activeTrainStatus = highlight?.kind === 'train-status' ? highlight.status : null;
    $: incidentsActive = highlight?.kind === 'incidents';

    $: debugMode = $page.url.searchParams.get('debug') === '1';

    $: runningCount = snapshot.trains.filter((t) => t.status === 'running').length;
    $: dwellingCount = snapshot.trains.filter((t) => t.status === 'dwelling').length;
    $: waitingCount = snapshot.trains.filter((t) => t.status === 'waiting').length;
    $: derailedCount = snapshot.trains.filter((t) => t.status === 'derailed').length;
    $: activeIncidents = snapshot.events.filter((e) => e.status === 'active').length;

    $: lastUpdateLabel = snapshot.timestamp
        ? new Date(snapshot.timestamp * 1000).toLocaleTimeString($locale === 'pl' ? 'pl-PL' : 'en-GB')
        : '—';

    function connectionLabel(connectionStatus: ConnectionStatus): string {
        if (connectionStatus === 'connecting') return $t('connection.connecting');
        if (connectionStatus === 'open') return $t('connection.open');
        if (connectionStatus === 'reconnecting') return $t('connection.reconnecting');
        return $t('connection.polling');
    }

    const statusDotClass: Record<ConnectionStatus, string> = {
        connecting: 'dot-amber',
        open: 'dot-green',
        reconnecting: 'dot-amber',
        'polling-fallback': 'dot-red'
    };

    let triggering = false;
    async function triggerRandomEvent() {
        if (triggering) return;
        triggering = true;
        try {
            await fetch(`${apiBaseUrl}/api/simulation/events/trigger`, { method: 'POST' });
        } catch {
            // Cicho pomijamy błąd
        } finally {
            triggering = false;
        }
    }

    $: paused = snapshot.paused;

    let controlBusy = false;

    async function handleClearTrains() {
        if (controlBusy) return;
        controlBusy = true;
        try {
            await clearTrains(fetch, apiBaseUrl);
        } catch {
            // Cicho pomijamy
        } finally {
            controlBusy = false;
        }
    }
</script>

<header class="site-header" class:collapsed={isCollapsed}>
    <button
        class="collapse-bubble"
        type="button"
        on:click={toggleCollapse}
        aria-label={isCollapsed ? 'Rozwiń nawigację' : 'Zwiń nawigację'}
        title={isCollapsed ? 'Rozwiń nagłówek' : 'Zwiń nagłówek'}
    >
        <span class="material-symbols-outlined" aria-hidden="true">
            {isCollapsed ? 'expand_more' : 'expand_less'}
        </span>
    </button>

    <div class="content-wrapper" class:hidden={isCollapsed} bind:this={navElement}>
        <div class="metrics-center">
            <div class="metrics">
                <button
                    type="button"
                    class="metric metric-ok"
                    class:active={activeTrainStatus === 'running'}
                    aria-pressed={activeTrainStatus === 'running'}
                    on:click={() => toggleTrainFilter('running')}
                    title={activeTrainStatus === 'running'
                        ? $t('header.filter.disable')
                        : $t('header.filter.running')}
                >
                    <span>{$t('header.metric.running')}</span>
                    <strong>{runningCount}</strong>
                    {#if activeTrainStatus === 'running'}<span class="clear-mark">×</span>{/if}
                </button>
                <button
                    type="button"
                    class="metric"
                    class:active={activeTrainStatus === 'dwelling'}
                    aria-pressed={activeTrainStatus === 'dwelling'}
                    on:click={() => toggleTrainFilter('dwelling')}
                    title={activeTrainStatus === 'dwelling'
                        ? $t('header.filter.disable')
                        : $t('header.filter.dwelling')}
                >
                    <span>{$t('header.metric.dwelling')}</span>
                    <strong>{dwellingCount}</strong>
                    {#if activeTrainStatus === 'dwelling'}<span class="clear-mark">×</span>{/if}
                </button>
                <button
                    type="button"
                    class="metric"
                    class:metric-warning={waitingCount > 0}
                    class:active={activeTrainStatus === 'waiting'}
                    aria-pressed={activeTrainStatus === 'waiting'}
                    on:click={() => toggleTrainFilter('waiting')}
                    title={activeTrainStatus === 'waiting'
                        ? $t('header.filter.disable')
                        : $t('header.filter.waiting')}
                >
                    <span>{$t('header.metric.waiting')}</span>
                    <strong>{waitingCount}</strong>
                    {#if activeTrainStatus === 'waiting'}<span class="clear-mark">×</span>{/if}
                </button>
                <button
                    type="button"
                    class="metric"
                    class:metric-danger={derailedCount > 0}
                    class:active={activeTrainStatus === 'derailed'}
                    aria-pressed={activeTrainStatus === 'derailed'}
                    on:click={() => toggleTrainFilter('derailed')}
                    title={activeTrainStatus === 'derailed'
                        ? $t('header.filter.disable')
                        : $t('header.filter.derailed')}
                >
                    <span>{$t('header.metric.derailed')}</span>
                    <strong>{derailedCount}</strong>
                    {#if activeTrainStatus === 'derailed'}<span class="clear-mark">×</span>{/if}
                </button>
                <button
                    type="button"
                    class="metric"
                    class:metric-danger={activeIncidents > 0}
                    class:active={incidentsActive}
                    aria-pressed={incidentsActive}
                    on:click={toggleIncidentFilter}
                    title={incidentsActive ? $t('header.filter.disable') : $t('header.filter.incidents')}
                >
                    <span>{$t('header.metric.incidents')}</span>
                    <strong>{activeIncidents}</strong>
                    {#if incidentsActive}<span class="clear-mark">×</span>{/if}
                </button>
            </div>

            {#if !readOnly}
                <div class="sim-controls">
                    <button
                        type="button"
                        class="ctrl-btn ctrl-danger"
                        on:click={handleClearTrains}
                        disabled={controlBusy || snapshot.trains.length === 0}
                        title={$t('header.clearTrainsTitle')}
                    >
                        <span>{$t('header.clearTrains')}</span>
                    </button>
                </div>
            {/if}

            <div class="status-strip" title={$t('header.connectionTitle', { time: lastUpdateLabel })}>
                {#if paused}
                    <span class="status-dot dot-amber"></span>
                    <span class="status-label">{$t('header.paused')}</span>
                {:else}
                    <span class="status-dot {statusDotClass[status]}"></span>
                    <span class="status-label">{connectionLabel(status)}</span>
                {/if}
                <span class="status-time">{lastUpdateLabel}</span>
            </div>

            {#if debugMode && !readOnly}
                <button type="button" class="debug-btn" on:click={triggerRandomEvent} disabled={triggering}>
                    {triggering ? $t('header.triggering') : `${$t('header.event')}`}
                </button>
            {/if}
        </div>

        <div class="actions">
            <button
                class="icon-button"
                type="button"
                on:click={toggleLanguage}
                aria-label={$locale === 'pl' ? 'Zmień język na angielski' : 'Change language to Polish'}
                title={$locale === 'pl' ? 'English' : 'Polski'}
            >
                <span class="material-symbols-outlined" aria-hidden="true">language</span>
            </button>
            <button
                class="icon-button"
                type="button"
                on:click={toggleLightMode}
                aria-label={lightMode ? 'Włącz tryb ciemny' : 'Włącz tryb jasny'}
                title={lightMode ? 'Tryb ciemny' : 'Tryb jasny'}
            >
                <span class="material-symbols-outlined" class:is-light={lightMode} aria-hidden="true"
                    >{lightMode ? 'dark_mode' : 'light_mode'}</span
                >
            </button>

            {#if user}
                {#if isGuest}
                    <span class="guest-badge">{$t('header.guestBadge')}</span>
                    <a class="login" href="/login" data-sveltekit-preload-data="off">
                        {$t('header.login')}
                    </a>
                {:else}
                    {#if isAdmin}
                        <a class="login admin-link" href="/admin" data-sveltekit-preload-data="off">
                            {$t('header.admin')}
                        </a>
                    {/if}
                    <span class="account-email" title={user.email}>{user.email}</span>
                    <form method="POST" action="/wyloguj" style="margin: 0;">
                        <button class="login logout-btn" type="submit">{$t('header.logout')}</button>
                    </form>
                {/if}
            {/if}
        </div>
    </div>
</header>

<style>
    .site-header {
        height: 76px;
        padding: 0 clamp(20px, 5vw, 72px);
        display: flex;
        align-items: center;
        justify-content: center;
        position: relative;
        z-index: 100;
        border: 0;
        background: transparent;
        box-sizing: border-box;
        pointer-events: none;
        transition: height 300ms ease;
    }
    .site-header > * {
        pointer-events: auto;
    }
    .site-header.collapsed {
        height: 52px;
    }
    .collapse-bubble {
        position: absolute;
        left: clamp(20px, 5vw, 72px);
        width: 36px;
        height: 36px;
        border-radius: 50%;
        border: 0;
        background: rgba(255, 255, 255, 0.04);
        color: #97a5ad;
        display: flex;
        align-items: center;
        justify-content: center;
        cursor: pointer;
        z-index: 110;
        pointer-events: auto;
        transition: background-color 200ms ease, color 200ms ease, transform 200ms ease;
    }
    .collapse-bubble:hover {
        background: rgba(255, 255, 255, 0.08);
        color: #fff;
        transform: scale(1.05);
    }
    .content-wrapper {
        width: 100%;
        display: flex;
        align-items: center;
        justify-content: space-between;
        opacity: 1;
        visibility: visible;
        pointer-events: auto;
        transition: opacity 200ms ease, visibility 200ms ease;
    }
    .content-wrapper.hidden {
        opacity: 0;
        visibility: hidden;
        pointer-events: none;
        position: absolute;
    }
    .metrics-center {
        display: flex;
        align-items: center;
        justify-content: center;
        gap: 16px;
        flex-wrap: wrap;
        margin-left: 50px;
    }
    .metrics {
        display: flex;
        align-items: center;
        flex-wrap: wrap;
        gap: 6px;
    }
    .metric {
        display: inline-flex;
        align-items: baseline;
        gap: 6px;
        background: rgba(255, 255, 255, 0.03);
        border: 0;
        border-radius: 8px;
        padding: 6px 10px;
        font: inherit;
        color: inherit;
        cursor: pointer;
        transition: background-color 180ms ease;
    }
    .metric:hover {
        background: rgba(255, 255, 255, 0.07);
    }
    .metric.active {
        background: rgba(255, 255, 255, 0.12);
    }
    .clear-mark {
        color: #97a5ad;
        font-weight: 300;
        font-size: 0.8rem;
        line-height: 1;
        margin-left: 2px;
    }
    .metric span {
        color: #97a5ad;
        font-size: 0.68rem;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        font-family: 'Inter Variable', Inter, sans-serif;
        font-weight: 300;
    }
    .metric strong {
        font-size: 0.8rem;
        font-weight: 500;
        line-height: 1;
        color: #fff;
    }
    .metric-ok strong {
        color: #6cb09f;
    }
    .metric-warning strong {
        color: #f0c29a;
    }
    .metric-danger strong {
        color: #de8489;
    }
    .status-strip {
        display: flex;
        align-items: center;
        gap: 8px;
        font-size: 0.72rem;
        font-weight: 300;
        letter-spacing: 0.08em;
        text-transform: uppercase;
        color: #97a5ad;
        padding: 5px 12px;
        border-radius: 999px;
        background: rgba(255, 255, 255, 0.03);
        white-space: nowrap;
    }
    .status-dot {
        width: 7px;
        height: 7px;
        border-radius: 999px;
        display: inline-block;
    }
    .dot-green {
        background: #6cb09f;
        box-shadow: 0 0 8px rgba(108, 176, 159, 0.6);
    }
    .dot-amber {
        background: #f0c29a;
        box-shadow: 0 0 8px rgba(240, 194, 154, 0.6);
    }
    .dot-red {
        background: #de8489;
        box-shadow: 0 0 8px rgba(222, 132, 137, 0.6);
    }
    .status-label {
        font-weight: 400;
        color: #cbd5e1;
        text-transform: uppercase;
        letter-spacing: 0.08em;
    }
    .status-time {
        color: #64748b;
        font-size: 0.68rem;
    }
    .sim-controls {
        display: flex;
        gap: 6px;
    }
    .ctrl-btn {
        padding: 6px 10px;
        border-radius: 7px;
        border: 0;
        background: rgba(255, 255, 255, 0.03);
        color: #97a5ad;
        font-family: inherit;
        font-size: 0.7rem;
        font-weight: 300;
        letter-spacing: 0.04em;
        text-transform: uppercase;
        cursor: pointer;
        white-space: nowrap;
        transition: background-color 180ms ease, color 180ms ease;
    }
    .ctrl-btn:hover:not(:disabled) {
        background: rgba(255, 255, 255, 0.08);
        color: #fff;
    }
    .ctrl-btn:disabled {
        opacity: 0.4;
        cursor: default;
    }
    .ctrl-danger:hover:not(:disabled) {
        background: rgba(222, 132, 137, 0.15);
        color: #de8489;
    }
    .debug-btn {
        padding: 6px 10px;
        border-radius: 7px;
        border: 0;
        background: rgba(255, 255, 255, 0.03);
        color: #97a5ad;
        font-family: inherit;
        font-size: 0.7rem;
        font-weight: 300;
        cursor: pointer;
        transition: background-color 180ms ease, color 180ms ease;
    }
    .debug-btn:hover:not(:disabled) {
        color: #ffffff;
        background: rgba(255, 255, 255, 0.08);
    }
    .actions {
        display: flex;
        align-items: center;
        gap: 12px;
    }
    .login {
        color: #dddddd;
        background: #1c1c1c;
        text-decoration: none;
        padding: 10px 16px;
        border-radius: 8px;
        font-size: 0.72rem;
        font-weight: 500;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        transition: color 300ms ease, background-color 300ms ease, opacity 180ms ease;
        border: 0;
        cursor: pointer;
        font-family: inherit;
    }
    .login:hover {
        opacity: 0.65;
    }
    .guest-badge {
        font-size: 0.64rem;
        color: #97a5ad;
        text-transform: uppercase;
        letter-spacing: 0.08em;
    }
    .account-email {
        font-size: 0.72rem;
        font-weight: 300;
        color: #97a5ad;
        max-width: 140px;
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
    }
    .icon-button {
        display: grid;
        place-items: center;
        width: 36px;
        height: 36px;
        padding: 0;
        border: 0;
        background: transparent;
        color: #97a5ad;
        cursor: pointer;
        transition: color 300ms ease;
    }
    .icon-button:hover {
        color: #fff;
    }
    .material-symbols-outlined {
        font-size: 21px;
        font-variation-settings: 'FILL' 0, 'wght' 300, 'GRAD' 0, 'opsz' 24;
        transition: transform 300ms ease;
    }
    .material-symbols-outlined.is-light {
        transform: rotate(180deg);
    }
    :global(html.light-mode) .icon-button {
        color: #52606a;
    }
    :global(html.light-mode) .icon-button:hover {
        color: #111827;
    }
    :global(html.light-mode) .login {
        background: #e5e7eb;
        color: #1f2937;
    }
    :global(html.light-mode) .collapse-bubble {
        background: rgba(0, 0, 0, 0.04);
        color: #52606a;
    }
    @media (max-width: 1100px) {
        .site-header {
            height: auto;
            flex-direction: column;
            padding: 14px 20px;
            gap: 12px;
        }
        .site-header.collapsed {
            height: 52px;
        }
        .metrics-center {
            flex-direction: column;
            width: 100%;
            margin-left: 0;
        }
        .actions {
            width: 100%;
            justify-content: center;
            flex-wrap: wrap;
        }
    }
</style>