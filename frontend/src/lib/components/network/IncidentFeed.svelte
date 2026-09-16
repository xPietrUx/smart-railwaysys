<script lang="ts">
    import { onDestroy, onMount } from 'svelte';
    import { t } from '$lib/i18n';
    import { eventLabel, formatEventMessage } from '$lib/services/labels';
    import type { RailEventNode } from '$lib/types/event';
    import type { StationNode } from '$lib/types/network';
    import type { Selected } from '$lib/types/selection';

    export let events: RailEventNode[];
    export let stations: StationNode[] = [];
    export let onSelect: (selected: Selected) => void = () => {};

    let nowSec = Date.now() / 1000;
    let interval: ReturnType<typeof setInterval>;

    const INCIDENT_ICONS: Record<string, string> = {
        signal_failure: 'electric_bolt',
        derailment: 'warning',
        track_blockage: 'do_not_disturb_on',
        default: 'error'
    };

    onMount(() => {
        interval = setInterval(() => {
            nowSec = Date.now() / 1000;
        }, 1000);
    });
    onDestroy(() => clearInterval(interval));

    function countdownLabel(resolvesAt: number): string {
        const remaining = Math.max(0, Math.round(resolvesAt - nowSec));
        if (remaining <= 0) return $t('incidents.soon');
        const minutes = Math.floor(remaining / 60);
        const seconds = Math.floor(remaining % 60);
        return minutes > 0 ? `${minutes} min ${seconds}s` : `${seconds}s`;
    }

    $: stationById = new Map(stations.map((station) => [station.id, station.name]));

    function stationName(id: string | null): string {
        if (!id) return '—';
        return stationById.get(id) ?? id;
    }

    function selectIncident(event: RailEventNode) {
        if (event.type === 'derailment' && event.trainId) {
            onSelect({ kind: 'train', id: event.trainId });
        } else if (event.stationId) {
            onSelect({ kind: 'station', id: event.stationId });
        } else if (event.segmentId) {
            onSelect({ kind: 'segment', id: event.segmentId });
        }
    }

    $: activeEvents = events
        .filter((event) => event.status === 'active')
        .slice()
        .sort((a, b) => b.startedAt - a.startedAt);

    $: resolvedEvents = events
        .filter((event) => event.status === 'resolved')
        .slice()
        .sort((a, b) => (b.resolvedAt ?? 0) - (a.resolvedAt ?? 0))
        .slice(0, 5);
</script>

<svelte:head>
    <link
        rel="stylesheet"
        href="https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined:opsz,wght,FILL,GRAD@20..48,100..700,0..1,-50..200"
    />
</svelte:head>

<div class="panel incidents">
    <div class="panel-header">
        <div>
            <p class="panel-label">{$t('incidents.live')}</p>
            <h2>
                {$t('incidents.title')}
                {#if activeEvents.length > 0}
                    <span class="count">{activeEvents.length}</span>
                {/if}
            </h2>
        </div>
    </div>

    <div class="scroll-area">
        {#if activeEvents.length === 0}
            <p class="empty">{$t('incidents.empty')}</p>
        {:else}
            <ul class="incident-list">
                {#each activeEvents as event (event.id)}
                    <li>
                        <button
                            type="button"
                            class="incident active-incident severity-{event.severity}"
                            on:click={() => selectIncident(event)}
                            title={$t('incidents.showOnMap')}
                        >
                            <span class="material-symbols-outlined icon" aria-hidden="true">
                                {INCIDENT_ICONS[event.type] ?? INCIDENT_ICONS.default}
                            </span>
                            <div class="incident-body">
                                <strong>{eventLabel(event.type, $t)}</strong>
                                <p>{formatEventMessage(event, $t, stationName)}</p>
                                <small>
                                    {$t('incidents.resolvesIn', { time: countdownLabel(event.resolvesAt) })}
                                </small>
                            </div>
                        </button>
                    </li>
                {/each}
            </ul>
        {/if}

        {#if resolvedEvents.length > 0}
            <div class="section">
                <h3>{$t('incidents.recentlyResolved')}</h3>
                <ul class="incident-list resolved">
                    {#each resolvedEvents as event (event.id)}
                        <li>
                            <div class="incident">
                                <span class="material-symbols-outlined icon" aria-hidden="true">
                                    {INCIDENT_ICONS[event.type] ?? INCIDENT_ICONS.default}
                                </span>
                                <div class="incident-body">
                                    <strong>{eventLabel(event.type, $t)}</strong>
                                    <p>{formatEventMessage(event, $t, stationName)}</p>
                                </div>
                            </div>
                        </li>
                    {/each}
                </ul>
            </div>
        {/if}
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

    .panel {
        --panel-bg: rgba(20, 20, 20, 0.94);
        --panel-shadow: 0 20px 48px rgba(0, 0, 0, 0.6);
        --panel-border: 1px solid rgba(255, 255, 255, 0.06);
        --panel-title: #ffffff;
        --panel-text: #f5f7f8;
        --panel-muted: #97a5ad;
        --card-bg: rgba(255, 255, 255, 0.03);
        --card-bg-hover: rgba(255, 255, 255, 0.07);
        --severity-major-bg: rgba(222, 132, 137, 0.1);
        --severity-major-hover: rgba(222, 132, 137, 0.16);
        --severity-major-color: #de8489;
        --severity-minor-bg: rgba(240, 194, 154, 0.1);
        --severity-minor-hover: rgba(240, 194, 154, 0.16);
        --severity-minor-color: #f0c29a;
        --count-bg: rgba(222, 132, 137, 0.15);
        --count-color: #de8489;
        --focus-ring: rgba(255, 255, 255, 0.65);

        background: var(--panel-bg);
        backdrop-filter: blur(16px);
        -webkit-backdrop-filter: blur(16px);
        border: var(--panel-border);
        box-shadow: var(--panel-shadow);
        border-radius: 14px;
        padding: 16px 18px;
        display: flex;
        flex-direction: column;
        max-height: min(420px, calc(100vh - 340px));
        min-height: 0;
        box-sizing: border-box;
        font-family: 'Inter Variable', Inter, sans-serif;
        color: var(--panel-text);
        transition: background-color 200ms ease, color 200ms ease, border-color 200ms ease;
    }

    :global(html.light-mode) .panel.incidents,
    :global([data-theme='light']) .panel.incidents,
    :global(.light) .panel.incidents {
        --panel-bg: rgba(244, 245, 243, 0.96);
        --panel-shadow: 0 20px 48px rgba(0, 0, 0, 0.08);
        --panel-border: 1px solid rgba(0, 0, 0, 0.08);
        --panel-title: #111827;
        --panel-text: #1f2933;
        --panel-muted: #52606a;
        --card-bg: rgba(0, 0, 0, 0.03);
        --card-bg-hover: rgba(0, 0, 0, 0.06);
        --severity-major-bg: rgba(201, 81, 88, 0.12);
        --severity-major-hover: rgba(201, 81, 88, 0.2);
        --severity-major-color: #c95158;
        --severity-minor-bg: rgba(201, 125, 57, 0.12);
        --severity-minor-hover: rgba(201, 125, 57, 0.2);
        --severity-minor-color: #c97d39;
        --count-bg: rgba(201, 81, 88, 0.15);
        --count-color: #c95158;
        --focus-ring: rgba(17, 24, 39, 0.65);
    }

    button:focus {
        outline: none;
    }

    button:focus-visible {
        outline: 2px solid var(--focus-ring);
        outline-offset: 2px;
    }

    .panel-header {
        margin-bottom: 12px;
        flex-shrink: 0;
    }

    .panel-label {
        margin: 0 0 4px;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        font-size: 0.66rem;
        font-weight: 300;
        color: var(--panel-muted);
    }

    h2,
    h3 {
        margin: 0;
    }

    h2 {
        font-size: 1.05rem;
        font-weight: 400;
        letter-spacing: 0.04em;
        text-transform: uppercase;
        color: var(--panel-title);
        display: flex;
        align-items: center;
        gap: 8px;
    }

    .count {
        background: var(--count-bg);
        color: var(--count-color);
        border-radius: 999px;
        font-size: 0.68rem;
        font-weight: 400;
        padding: 2px 8px;
        line-height: 1.2;
    }

    .scroll-area {
        overflow-y: auto;
        min-height: 0;
        flex: 1;
        padding-right: 4px;
        scrollbar-width: thin;
        scrollbar-color: rgba(255, 255, 255, 0.15) transparent;
    }

    :global(html.light-mode) .scroll-area {
        scrollbar-color: rgba(0, 0, 0, 0.15) transparent;
    }

    .scroll-area::-webkit-scrollbar {
        width: 4px;
    }

    .scroll-area::-webkit-scrollbar-thumb {
        background: rgba(255, 255, 255, 0.15);
        border-radius: 4px;
    }

    :global(html.light-mode) .scroll-area::-webkit-scrollbar-thumb {
        background: rgba(0, 0, 0, 0.15);
    }

    .empty {
        margin: 0;
        color: var(--panel-muted);
        font-size: 0.76rem;
        font-weight: 300;
        letter-spacing: 0.04em;
        text-transform: uppercase;
    }

    .incident-list {
        list-style: none;
        margin: 0;
        padding: 0;
        display: grid;
        gap: 6px;
    }

    .incident {
        display: flex;
        gap: 10px;
        align-items: flex-start;
        padding: 10px 12px;
        border-radius: 10px;
        background: var(--card-bg);
        border: 0;
        width: 100%;
        text-align: left;
        color: inherit;
        box-sizing: border-box;
        transition: background-color 150ms ease;
    }

    button.incident {
        cursor: pointer;
    }

    button.incident:hover {
        background: var(--card-bg-hover);
    }

    .active-incident.severity-major {
        background: var(--severity-major-bg);
    }

    .active-incident.severity-major:hover {
        background: var(--severity-major-hover);
    }

    .active-incident.severity-minor {
        background: var(--severity-minor-bg);
    }

    .active-incident.severity-minor:hover {
        background: var(--severity-minor-hover);
    }

    .icon {
        font-size: 18px;
        color: var(--panel-muted);
        margin-top: 1px;
        flex-shrink: 0;
    }

    .severity-major .icon {
        color: var(--severity-major-color);
    }

    .severity-minor .icon {
        color: var(--severity-minor-color);
    }

    .incident-body {
        min-width: 0;
        flex: 1;
    }

    .incident-body strong {
        display: block;
        font-size: 0.76rem;
        font-weight: 400;
        letter-spacing: 0.06em;
        text-transform: uppercase;
        color: var(--panel-text);
    }

    .incident-body p {
        margin: 3px 0 0;
        font-size: 0.74rem;
        font-weight: 300;
        color: var(--panel-muted);
        line-height: 1.4;
        letter-spacing: 0.02em;
    }

    .incident-body small {
        display: block;
        margin-top: 4px;
        color: var(--severity-minor-color);
        font-size: 0.68rem;
        font-weight: 400;
        letter-spacing: 0.04em;
        text-transform: uppercase;
    }

    .section {
        margin-top: 14px;
    }

    .section h3 {
        margin-bottom: 8px;
        font-size: 0.68rem;
        font-weight: 400;
        color: var(--panel-muted);
        text-transform: uppercase;
        letter-spacing: 0.08em;
    }

    .resolved .incident {
        opacity: 0.55;
    }
</style>