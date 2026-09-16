<script lang="ts">
    import { t } from '$lib/i18n';
    import type { LiveSnapshot } from '$lib/services/live';
    import { pauseSimulation, resumeSimulation, setSimulationSpeed } from '$lib/services/simulation';

    export let snapshot: LiveSnapshot;
    export let apiBaseUrl: string;
    export let readOnly = false;

    const SPEEDS = [0.5, 1, 1.5, 2];
    const CX = 90;
    const CY = 90;
    const R_INNER = 40;
    const R_OUTER = 84;
    const CORE_R = 32;
    const SPAN_DEG = 360 / SPEEDS.length;

    function polar(radius: number, deg: number): { x: number; y: number } {
        const rad = (deg * Math.PI) / 180;
        return { x: CX + radius * Math.cos(rad), y: CY + radius * Math.sin(rad) };
    }

    function point(radius: number, deg: number): string {
        const { x, y } = polar(radius, deg);
        return `${x.toFixed(2)} ${y.toFixed(2)}`;
    }

    function wedgePath(index: number): string {
        const startAngle = index * SPAN_DEG - 90;
        const from = startAngle;
        const to = startAngle + SPAN_DEG;
        return [
            `M ${point(R_OUTER, from)}`,
            `A ${R_OUTER} ${R_OUTER} 0 0 1 ${point(R_OUTER, to)}`,
            `L ${point(R_INNER, to)}`,
            `A ${R_INNER} ${R_INNER} 0 0 0 ${point(R_INNER, from)}`,
            'Z'
        ].join(' ');
    }

    function labelPos(index: number): { x: number; y: number } {
        const startAngle = index * SPAN_DEG - 90;
        return polar((R_INNER + R_OUTER) / 2, startAngle + SPAN_DEG / 2);
    }

    function formatSimClock(clockMinutes: number): string {
        const simMinutes = Math.max(0, Math.floor(clockMinutes));
        const pad = (value: number) => String(value).padStart(2, '0');
        return `${pad(Math.floor(simMinutes / 60) % 24)}:${pad(simMinutes % 60)}`;
    }

    let busy = false;
    let optimisticPaused: boolean | null = null;
    let optimisticSpeed: number | null = null;
    $: paused = optimisticPaused ?? snapshot.paused;
    $: speed = optimisticSpeed ?? snapshot.speed;

    $: if (optimisticPaused !== null && snapshot.paused === optimisticPaused) optimisticPaused = null;
    $: if (optimisticSpeed !== null && snapshot.speed === optimisticSpeed) optimisticSpeed = null;

    async function togglePause() {
        if (busy || readOnly) return;
        busy = true;
        try {
            if (paused) {
                await resumeSimulation(fetch, apiBaseUrl);
                optimisticPaused = false;
            } else {
                await pauseSimulation(fetch, apiBaseUrl);
                optimisticPaused = true;
            }
        } catch {
            // Ignorujemy błąd
        } finally {
            busy = false;
        }
    }

    async function pickSpeed(option: number) {
        if (busy || readOnly || option === speed) return;
        busy = true;
        try {
            await setSimulationSpeed(fetch, apiBaseUrl, option);
            optimisticSpeed = option;
        } catch {
            // Ignorujemy błąd
        } finally {
            busy = false;
        }
    }

    function activateOnKey(event: KeyboardEvent, action: () => void) {
        if (event.key === 'Enter' || event.key === ' ') {
            event.preventDefault();
            action();
        }
    }
</script>

<svelte:head>
    <link
        rel="stylesheet"
        href="https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined:opsz,wght,FILL,GRAD@20..48,100..700,0..1,-50..200"
    />
</svelte:head>

<div class="speed-control-wrapper" class:paused class:read-only={readOnly}>
    <div class="speed-dial">
        <svg
            viewBox="0 0 180 180"
            width="156"
            height="156"
            role="group"
            aria-label={$t('header.speed.title', { speed })}
        >
            <circle cx={CX} cy={CY} r={R_OUTER} class="dial-base" />

            {#each SPEEDS as option, index (option)}
                {@const active = option <= speed}
                <path
                    d={wedgePath(index)}
                    class="wedge"
                    class:active
                    role="button"
                    tabindex={readOnly ? -1 : 0}
                    aria-disabled={readOnly}
                    aria-label={$t('header.speed.set', { speed: option })}
                    aria-pressed={option === speed}
                    on:click={() => pickSpeed(option)}
                    on:keydown={(event) => activateOnKey(event, () => pickSpeed(option))}
                >
                    <title>{$t('header.speed.set', { speed: option })}</title>
                </path>
                <text
                    x={labelPos(index).x.toFixed(2)}
                    y={labelPos(index).y.toFixed(2)}
                    class="wedge-label"
                    class:lit={active}
                >
                    {option}×
                </text>
            {/each}

            <circle
                cx={CX}
                cy={CY}
                r={CORE_R}
                class="core"
                role="button"
                tabindex={readOnly ? -1 : 0}
                aria-disabled={readOnly}
                aria-label={paused ? $t('header.resumeTitle') : $t('header.pauseTitle')}
                on:click={togglePause}
                on:keydown={(event) => activateOnKey(event, togglePause)}
            >
                <title>{paused ? $t('header.resumeTitle') : $t('header.pauseTitle')}</title>
            </circle>

            <foreignObject x={CX - 12} y={CY - 12} width="24" height="24" style="overflow: visible;">
                <div xmlns="http://www.w3.org/1999/xhtml" class="core-center-content">
                    <span class="material-symbols-outlined core-icon" aria-hidden="true">
                        {paused ? 'play_arrow' : 'pause'}
                    </span>
                </div>
            </foreignObject>
        </svg>
    </div>

    <div class="clock-badge" title={$t('header.elapsedTitle')}>
        <span class="clock-time">{formatSimClock(snapshot.simClockMinutes)}</span>
        <span class="clock-divider">·</span>
        <span class="clock-speed">
            {#if paused}
                <span class="paused-text">{$t('header.paused')}</span>
            {:else}
                {speed}×
            {/if}
        </span>
    </div>
</div>

<style>
    .material-symbols-outlined {
        font-family: 'Material Symbols Outlined' !important;
        font-weight: normal;
        font-style: normal;
        font-size: 19px;
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

    .speed-control-wrapper {
        --dial-base-fill: rgba(255, 255, 255, 0.04);
        --dial-filter: drop-shadow(0 20px 48px rgba(0, 0, 0, 0.6));
        --wedge-fill: transparent;
        --wedge-hover: rgba(255, 255, 255, 0.06);
        --wedge-active: rgba(255, 255, 255, 0.14);
        --wedge-active-paused: rgba(255, 255, 255, 0.08);
        --wedge-label: #97a5ad;
        --wedge-label-lit: #ffffff;
        --wedge-label-lit-paused: #97a5ad;
        --core-fill: rgba(20, 20, 20, 0.95);
        --core-hover: rgba(30, 30, 30, 0.95);
        --core-icon: #f5f7f8;
        --clock-bg: rgba(255, 255, 255, 0.04);
        --clock-border: 0;
        --clock-shadow: 0 10px 24px rgba(0, 0, 0, 0.4);
        --clock-time: #f5f7f8;
        --clock-divider: #64748b;
        --clock-speed: #97a5ad;
        --color-paused: #f0c29a;
        --focus-ring: rgba(255, 255, 255, 0.65);

        display: inline-flex;
        flex-direction: column;
        align-items: center;
        gap: 10px;
        font-family: 'Inter Variable', Inter, sans-serif;
        pointer-events: auto;
    }

    :global(html.light-mode) .speed-control-wrapper,
    :global([data-theme='light']) .speed-control-wrapper,
    :global(.light) .speed-control-wrapper {
        --dial-base-fill: rgba(0, 0, 0, 0.04);
        --dial-filter: drop-shadow(0 20px 48px rgba(0, 0, 0, 0.08));
        --wedge-fill: transparent;
        --wedge-hover: rgba(0, 0, 0, 0.04);
        --wedge-active: rgba(0, 0, 0, 0.12);
        --wedge-active-paused: rgba(0, 0, 0, 0.06);
        --wedge-label: #64748b;
        --wedge-label-lit: #111827;
        --wedge-label-lit-paused: #64748b;
        --core-fill: rgba(244, 245, 243, 0.98);
        --core-hover: #ffffff;
        --core-icon: #111827;
        --clock-bg: rgba(0, 0, 0, 0.04);
        --clock-border: 0;
        --clock-shadow: 0 10px 24px rgba(0, 0, 0, 0.08);
        --clock-time: #111827;
        --clock-divider: #94a3b8;
        --clock-speed: #64748b;
        --color-paused: #c97d39;
        --focus-ring: rgba(17, 24, 39, 0.65);
    }

    .speed-dial {
        position: relative;
        display: inline-block;
    }

    svg {
        display: block;
        overflow: visible;
        filter: var(--dial-filter);
        font-family: inherit;
        transition: filter 200ms ease;
    }

    .dial-base {
        fill: var(--dial-base-fill);
        backdrop-filter: blur(16px);
        -webkit-backdrop-filter: blur(16px);
        transition: fill 200ms ease;
    }

    .read-only .wedge,
    .read-only .core {
        pointer-events: none;
        cursor: default;
    }

    .wedge {
        fill: var(--wedge-fill);
        stroke: transparent;
        stroke-width: 0;
        cursor: pointer;
        outline: none;
        transition: fill 150ms ease;
    }

    .wedge:focus {
        outline: none;
    }

    .wedge:focus-visible {
        outline: 2px solid var(--focus-ring);
        outline-offset: -2px;
    }

    .wedge:hover:not(:disabled) {
        fill: var(--wedge-hover);
    }

    .wedge.active {
        fill: var(--wedge-active);
    }

    .paused .wedge.active {
        fill: var(--wedge-active-paused);
    }

    .wedge-label {
        font-size: 11px;
        font-weight: 300;
        fill: var(--wedge-label);
        text-anchor: middle;
        dominant-baseline: central;
        pointer-events: none;
        user-select: none;
        letter-spacing: 0.04em;
        transition: fill 150ms ease;
    }

    .wedge-label.lit {
        fill: var(--wedge-label-lit);
        font-weight: 500;
    }

    .paused .wedge-label.lit {
        fill: var(--wedge-label-lit-paused);
    }

    .core {
        fill: var(--core-fill);
        cursor: pointer;
        outline: none;
        stroke: transparent;
        stroke-width: 0;
        transition: fill 150ms ease;
    }

    .core:focus {
        outline: none;
    }

    .core:focus-visible {
        outline: 2px solid var(--focus-ring);
        outline-offset: 2px;
    }

    .core:hover {
        fill: var(--core-hover);
    }

    .core-center-content {
        width: 24px;
        height: 24px;
        display: flex;
        align-items: center;
        justify-content: center;
        pointer-events: none;
    }

    .core-icon {
        font-size: 18px;
        color: var(--core-icon);
        line-height: 1;
        transition: color 150ms ease;
    }

    .paused .core-icon {
        color: var(--color-paused);
    }

    .clock-badge {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        padding: 5px 12px;
        border-radius: 999px;
        background: var(--clock-bg);
        border: var(--clock-border);
        backdrop-filter: blur(12px);
        -webkit-backdrop-filter: blur(12px);
        box-shadow: var(--clock-shadow);
        font-variant-numeric: tabular-nums;
        white-space: nowrap;
        transition: background-color 200ms ease, box-shadow 200ms ease;
    }

    .clock-time {
        font-size: 0.78rem;
        font-weight: 400;
        letter-spacing: 0.06em;
        color: var(--clock-time);
    }

    .clock-divider {
        color: var(--clock-divider);
        font-size: 0.68rem;
    }

    .clock-speed {
        font-size: 0.7rem;
        font-weight: 300;
        letter-spacing: 0.08em;
        text-transform: uppercase;
        color: var(--clock-speed);
    }

    .paused-text {
        color: var(--color-paused);
    }
</style>