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
        const seconds = remaining % 60;
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
        background: rgba(20, 20, 20, 0.94);
        backdrop-filter: blur(16px);
        -webkit-backdrop-filter: blur(16px);
        border: 0;
        box-shadow: 0 20px 48px rgba(0, 0, 0, 0.6);
        border-radius: 14px;
        padding: 20px;
        display: flex;
        flex-direction: column;
        min-height: 0;
        font-family: 'Inter Variable', Inter, sans-serif;
        color: #f5f7f8;
    }

    .panel-header {
        margin-bottom: 14px;
        flex-shrink: 0;
    }

    .panel-label {
        margin: 0 0 4px;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        font-size: 0.66rem;
        font-weight: 300;
        color: #97a5ad;
    }

    h2,
    h3 {
        margin: 0;
    }

    h2 {
        font-size: 1.1rem;
        font-weight: 400;
        letter-spacing: 0.04em;
        text-transform: uppercase;
        color: #ffffff;
        display: flex;
        align-items: center;
        gap: 8px;
    }

    .count {
        background: rgba(222, 132, 137, 0.15);
        color: #de8489;
        border-radius: 999px;
        font-size: 0.68rem;
        font-weight: 400;
        padding: 2px 8px;
        line-height: 1.2;
    }

    .scroll-area {
        overflow-y: auto;
        min-height: 0;
    }

    .empty {
        margin: 0;
        color: #97a5ad;
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
        background: rgba(255, 255, 255, 0.03);
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
        background: rgba(255, 255, 255, 0.07);
    }

    .active-incident.severity-major {
        background: rgba(222, 132, 137, 0.1);
    }

    .active-incident.severity-major:hover {
        background: rgba(222, 132, 137, 0.16);
    }

    .active-incident.severity-minor {
        background: rgba(240, 194, 154, 0.1);
    }

    .active-incident.severity-minor:hover {
        background: rgba(240, 194, 154, 0.16);
    }

    .icon {
        font-size: 18px;
        color: #97a5ad;
        margin-top: 1px;
    }

    .severity-major .icon {
        color: #de8489;
    }

    .severity-minor .icon {
        color: #f0c29a;
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
        color: #f5f7f8;
    }

    .incident-body p {
        margin: 3px 0 0;
        font-size: 0.74rem;
        font-weight: 300;
        color: #97a5ad;
        line-height: 1.4;
        letter-spacing: 0.02em;
    }

    .incident-body small {
        display: block;
        margin-top: 4px;
        color: #f0c29a;
        font-size: 0.68rem;
        font-weight: 400;
        letter-spacing: 0.04em;
        text-transform: uppercase;
    }

    .section {
        margin-top: 18px;
    }

    .section h3 {
        margin-bottom: 8px;
        font-size: 0.68rem;
        font-weight: 400;
        color: #97a5ad;
        text-transform: uppercase;
        letter-spacing: 0.08em;
    }

    .resolved .incident {
        opacity: 0.5;
    }
</style>