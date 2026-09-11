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
    const R_INNER = 42;
    const R_OUTER = 84;
    const CORE_R = 32;
    const GAP_DEG = 3;
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
        const from = startAngle + GAP_DEG;
        const to = startAngle + SPAN_DEG - GAP_DEG;
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
            <circle cx={CX} cy={CY} r={R_OUTER + 2} class="dial-base" />

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

    <!-- Pigułka z czasem symulacji -->
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
    .speed-control-wrapper {
        display: inline-flex;
        flex-direction: column;
        align-items: center;
        gap: 10px;
        font-family: 'Inter Variable', Inter, sans-serif;
        pointer-events: auto;
    }

    .speed-dial {
        position: relative;
        display: inline-block;
    }

    svg {
        display: block;
        overflow: visible;
        filter: drop-shadow(0 18px 40px rgba(0, 0, 0, 0.65));
        font-family: inherit;
    }

    .dial-base {
        fill: rgba(20, 20, 20, 0.96);
        backdrop-filter: blur(16px);
        -webkit-backdrop-filter: blur(16px);
    }

    .read-only .wedge,
    .read-only .core {
        pointer-events: none;
        cursor: default;
    }

    .wedge {
        fill: rgba(255, 255, 255, 0.03);
        cursor: pointer;
        outline: none;
        transition: fill 150ms ease;
    }

    .wedge:hover:not(:disabled) {
        fill: rgba(255, 255, 255, 0.08);
    }

    .wedge.active {
        fill: #f5f7f8;
    }

    .paused .wedge.active {
        fill: rgba(245, 247, 248, 0.25);
    }

    .wedge-label {
        font-size: 11.5px;
        font-weight: 300;
        fill: #97a5ad;
        text-anchor: middle;
        dominant-baseline: central;
        pointer-events: none;
        user-select: none;
        letter-spacing: 0.04em;
        transition: fill 150ms ease;
    }

    .wedge-label.lit {
        fill: #141414;
        font-weight: 500;
    }

    .paused .wedge-label.lit {
        fill: #f5f7f8;
    }

    .core {
        fill: #141414;
        cursor: pointer;
        outline: none;
        transition: fill 150ms ease;
    }

    .core:hover {
        fill: #1a1a1a;
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
        color: #f5f7f8;
        line-height: 1;
    }

    .paused .core-icon {
        color: #f0c29a;
    }

    .clock-badge {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        padding: 6px 14px;
        border-radius: 999px;
        background: rgba(20, 20, 20, 0.92);
        backdrop-filter: blur(16px);
        -webkit-backdrop-filter: blur(16px);
        box-shadow: 0 10px 30px rgba(0, 0, 0, 0.5);
        font-variant-numeric: tabular-nums;
        white-space: nowrap;
    }

    .clock-time {
        font-size: 0.82rem;
        font-weight: 400;
        letter-spacing: 0.06em;
        color: #ffffff;
    }

    .clock-divider {
        color: #55626b;
        font-size: 0.7rem;
    }

    .clock-speed {
        font-size: 0.72rem;
        font-weight: 300;
        letter-spacing: 0.08em;
        text-transform: uppercase;
        color: #97a5ad;
    }

    .paused-text {
        color: #f0c29a;
    }
</style>