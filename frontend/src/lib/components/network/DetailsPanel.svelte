<script lang="ts">
    import { SvelteMap } from 'svelte/reactivity';
    import { fade } from 'svelte/transition';
    import { t } from '$lib/i18n';
    import {
        directionStatusLabel,
        formatEventMessage,
        formatStationType,
        trainEndpoints,
        trainStatusLabel,
        trainTargetId,
        trainTypeLabel
    } from '$lib/services/labels';
    import type { RailEventNode } from '$lib/types/event';
    import type { NetworkGraph, TrackSegment } from '$lib/types/network';
    import type { Selected } from '$lib/types/selection';
    import type { TrainNode } from '$lib/types/train';

    export let graph: NetworkGraph;
    export let trains: TrainNode[] = [];
    export let events: RailEventNode[] = [];
    export let selected: Selected | null = null;

    $: stations = graph.stations;
    $: segments = graph.segments;
    $: stationById = new Map(stations.map((station) => [station.id, station]));
    $: degreeByStation = (() => {
        const map = new SvelteMap<string, number>();
        for (const segment of segments) {
            map.set(segment.source, (map.get(segment.source) ?? 0) + 1);
            map.set(segment.target, (map.get(segment.target) ?? 0) + 1);
        }
        return map;
    })();

    $: trainsByStation = (() => {
        const map = new SvelteMap<string, TrainNode[]>();
        for (const train of trains) {
            if (train.status === 'running') continue;
            const list = map.get(train.currentStationId) ?? [];
            list.push(train);
            map.set(train.currentStationId, list);
        }
        return map;
    })();

    $: selectedKind = selected?.kind ?? null;
    $: selectedStation = selected?.kind === 'station' ? (stationById.get(selected.id) ?? null) : null;
    let selectedSegment: TrackSegment | null;
    $: {
        if (selected?.kind === 'segment') {
            const segmentId = selected.id;
            selectedSegment = segments.find((segment) => segment.segmentId === segmentId) ?? null;
        } else {
            selectedSegment = null;
        }
    }
    let selectedTrain: TrainNode | null;
    $: {
        if (selected?.kind === 'train') {
            const trainId = selected.id;
            selectedTrain = trains.find((train) => train.id === trainId) ?? null;
        } else {
            selectedTrain = null;
        }
    }

    $: connectedSegments = selectedStation
        ? segments.filter(
                (segment) =>
                    segment.source === selectedStation?.id || segment.target === selectedStation?.id
            )
        : [];
    $: trainsOnSelectedSegment = selectedSegment
        ? trains.filter((train) => train.currentSegmentId === selectedSegment?.segmentId)
        : [];
    $: selectedTrainTargetId = selectedTrain ? trainTargetId(selectedTrain) : null;
    $: selectedTrainDelayEvent = (() => {
        const eventId = selectedTrain?.delayedByEventId;
        if (!eventId) return null;
        return events.find((event) => event.id === eventId) ?? null;
    })();

    function stationName(id: string | null | undefined) {
        if (!id) return '—';
        return stationById.get(id)?.name ?? id;
    }

    function relationLabel(train: TrainNode) {
        const { fromId, toId } = trainEndpoints(train);
        return `${stationName(fromId)} → ${stationName(toId)}`;
    }

    function pickStation(id: string) {
        selected = { kind: 'station', id };
    }

    function pickSegment(id: string) {
        selected = { kind: 'segment', id };
    }

    function pickTrain(id: string) {
        selected = { kind: 'train', id };
    }

    function close() {
        selected = null;
    }
</script>

<svelte:head>
    <link
        rel="stylesheet"
        href="https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined:opsz,wght,FILL,GRAD@20..48,100..700,0..1,-50..200"
    />
</svelte:head>

{#if selected}
    <aside
        class="left-details-container"
        transition:fade={{ duration: 180 }}
    >
        <button
            type="button"
            class="close-btn"
            on:click={close}
            aria-label={$t('details.close')}
            title={$t('details.close')}
        >
            <span class="material-symbols-outlined" aria-hidden="true">close</span>
        </button>

        {#key selected.id}
            <div
                class="details-content"
                in:fade={{ duration: 140 }}
                out:fade={{ duration: 90 }}
            >
                {#if selectedKind === 'station' && selectedStation}
                    <div class="circle-badge">
                        <span class="badge-main-text">{selectedStation.code || selectedStation.id.slice(0, 3)}</span>
                    </div>

                    <div class="divider"></div>

                    <div class="stats-stream">
                        <div class="stat-line primary-title">
                            <strong class="stat-value text-large">{selectedStation.name}</strong>
                            <span class="stat-dash">—</span>
                            <span class="stat-label">{$t('details.station')}</span>
                        </div>

                        <div class="stat-line">
                            <strong class="stat-value">{formatStationType(selectedStation.type, $t)}</strong>
                            <span class="stat-dash">—</span>
                            <span class="stat-label">{$t('details.type')}</span>
                        </div>

                        <div class="stat-line">
                            <strong class="stat-value">{selectedStation.platforms}</strong>
                            <span class="stat-dash">—</span>
                            <span class="stat-label">{$t('details.platforms')}</span>
                        </div>

                        <div class="stat-line">
                            <strong class="stat-value">{selectedStation.tracks}</strong>
                            <span class="stat-dash">—</span>
                            <span class="stat-label">{$t('details.tracks')}</span>
                        </div>

                        <div class="stat-line">
                            <strong class="stat-value">{selectedStation.dailyTrains}</strong>
                            <span class="stat-dash">—</span>
                            <span class="stat-label">{$t('details.trainsPerDay')}</span>
                        </div>

                        <div class="stat-line">
                            <strong class="stat-value">{degreeByStation.get(selectedStation.id) ?? 0}</strong>
                            <span class="stat-dash">—</span>
                            <span class="stat-label">{$t('details.connections')}</span>
                        </div>

                        {#if (trainsByStation.get(selectedStation.id) ?? []).length > 0}
                            <div class="sub-block">
                                <span class="sub-label">{$t('details.trainsAtStation')}</span>
                                <div class="interactive-pills">
                                    {#each trainsByStation.get(selectedStation.id) ?? [] as train (train.id)}
                                        <button type="button" class="mini-pill" on:click={() => pickTrain(train.id)}>
                                            <span>{train.name}</span>
                                            <small>{trainStatusLabel(train.status, $t)}</small>
                                        </button>
                                    {/each}
                                </div>
                            </div>
                        {/if}

                        {#if connectedSegments.length > 0}
                            <div class="sub-block">
                                <span class="sub-label">{$t('details.nearestConnections')}</span>
                                <div class="interactive-pills">
                                    {#each connectedSegments as segment (segment.segmentId)}
                                        <button type="button" class="mini-pill" on:click={() => pickSegment(segment.segmentId)}>
                                            <span>{segment.segmentId}</span>
                                            <small>{segment.distKm} km</small>
                                        </button>
                                    {/each}
                                </div>
                            </div>
                        {/if}
                    </div>

                {:else if selectedKind === 'segment' && selectedSegment}
                    <div class="circle-badge">
                        <span class="badge-main-text">{selectedSegment.line}</span>
                    </div>

                    <div class="divider"></div>

                    <div class="stats-stream">
                        <div class="stat-line primary-title">
                            <strong class="stat-value text-large">{selectedSegment.segmentId}</strong>
                            <span class="stat-dash">—</span>
                            <span class="stat-label">{$t('details.segment')}</span>
                        </div>

                        <div class="stat-line">
                            <strong class="stat-value">{selectedSegment.distKm} km</strong>
                            <span class="stat-dash">—</span>
                            <span class="stat-label">{$t('details.length')}</span>
                        </div>

                        <div class="stat-line">
                            <strong class="stat-value">{selectedSegment.travelMin} min</strong>
                            <span class="stat-dash">—</span>
                            <span class="stat-label">{$t('details.travelTime')}</span>
                        </div>

                        <div class="stat-line">
                            <strong class="stat-value">{selectedSegment.vmax} km/h</strong>
                            <span class="stat-dash">—</span>
                            <span class="stat-label">VMAX</span>
                        </div>

                        <div class="stat-line">
                            <strong class="stat-value">{selectedSegment.railTracks}</strong>
                            <span class="stat-dash">—</span>
                            <span class="stat-label">{$t('details.tracks')}</span>
                        </div>

                        <div class="stat-line">
                            <strong class="stat-value status-{selectedSegment.forward.status}">
                                {directionStatusLabel(selectedSegment.forward.status, $t)}
                            </strong>
                            <span class="stat-dash">—</span>
                            <span class="stat-label">FORWARD</span>
                        </div>

                        <div class="stat-line">
                            <strong class="stat-value status-{selectedSegment.backward.status}">
                                {directionStatusLabel(selectedSegment.backward.status, $t)}
                            </strong>
                            <span class="stat-dash">—</span>
                            <span class="stat-label">BACKWARD</span>
                        </div>

                        {#if trainsOnSelectedSegment.length > 0}
                            <div class="sub-block">
                                <span class="sub-label">{$t('details.trainsOnSegment')}</span>
                                <div class="interactive-pills">
                                    {#each trainsOnSelectedSegment as train (train.id)}
                                        <button type="button" class="mini-pill" on:click={() => pickTrain(train.id)}>
                                            <span>{train.name}</span>
                                            <small>{Math.round(train.progress * 100)}%</small>
                                        </button>
                                    {/each}
                                </div>
                            </div>
                        {/if}

                        <div class="sub-block">
                            <span class="sub-label">{$t('details.connects')}</span>
                            <div class="interactive-pills">
                                <button type="button" class="mini-pill" on:click={() => pickStation(selectedSegment?.source ?? '')}>
                                    <span>{stationById.get(selectedSegment?.source ?? '')?.name}</span>
                                    <small>{$t('details.stationA')}</small>
                                </button>
                                <button type="button" class="mini-pill" on:click={() => pickStation(selectedSegment?.target ?? '')}>
                                    <span>{stationById.get(selectedSegment?.target ?? '')?.name}</span>
                                    <small>{$t('details.stationB')}</small>
                                </button>
                            </div>
                        </div>
                    </div>

                {:else if selectedKind === 'train' && selectedTrain}
                    <div class="circle-badge">
                        <span class="badge-main-text">{selectedTrain.name.slice(0, 3)}</span>
                    </div>

                    <div class="divider"></div>

                    <div class="stats-stream">
                        <div class="stat-line primary-title">
                            <strong class="stat-value text-large">{selectedTrain.name}</strong>
                            <span class="stat-dash">—</span>
                            <span class="stat-label">{trainTypeLabel(selectedTrain.type, $t)}</span>
                        </div>

                        <div class="stat-line">
                            <strong class="stat-value status-{selectedTrain.status}">
                                {trainStatusLabel(selectedTrain.status, $t)}
                            </strong>
                            <span class="stat-dash">—</span>
                            <span class="stat-label">{$t('details.status')}</span>
                        </div>

                        <div class="stat-line">
                            <strong class="stat-value">{relationLabel(selectedTrain)}</strong>
                            <span class="stat-dash">—</span>
                            <span class="stat-label">RELACJA</span>
                        </div>

                        <div class="stat-line">
                            <strong class="stat-value">
                                {selectedTrain.status === 'running' ? stationName(selectedTrain.nextStationId) : '—'}
                            </strong>
                            <span class="stat-dash">—</span>
                            <span class="stat-label">{$t('details.nextStop')}</span>
                        </div>

                        <div class="stat-line">
                            <strong class="stat-value">{Math.round(selectedTrain.progress * 100)}%</strong>
                            <span class="stat-dash">—</span>
                            <span class="stat-label">{$t('details.segmentProgress')}</span>
                        </div>

                        <div class="stat-line">
                            <strong class="stat-value">{selectedTrain.vmax} km/h</strong>
                            <span class="stat-dash">—</span>
                            <span class="stat-label">VMAX</span>
                        </div>

                        {#if selectedTrainDelayEvent}
                            <div class="delay-alert">
                                <strong>! {$t('details.delayedByIncident')}</strong>
                                <p>{formatEventMessage(selectedTrainDelayEvent, $t, stationName)}</p>
                            </div>
                        {/if}

                        {#if selectedTrain.routeStationIds.length > 0}
                            <div class="sub-block">
                                <span class="sub-label">TRASA ({selectedTrain.routeStationIds.length})</span>
                                <div class="route-strip">
                                    {#each selectedTrain.routeStationIds as stationId, index}
                                        <button
                                            type="button"
                                            class="route-dot-item"
                                            class:is-active={index === selectedTrain.routeIndex}
                                            class:is-passed={index < selectedTrain.routeIndex}
                                            on:click={() => pickStation(stationId)}
                                            title={stationName(stationId)}
                                        >
                                            <span>{stationName(stationId)}</span>
                                        </button>
                                    {/each}
                                </div>
                            </div>
                        {/if}
                    </div>
                {/if}
            </div>
        {/key}
    </aside>
{/if}

<style>
    .material-symbols-outlined {
        font-family: 'Material Symbols Outlined' !important;
        font-weight: normal;
        font-style: normal;
        font-size: 20px;
        line-height: 1;
        display: inline-block;
        white-space: nowrap;
        direction: ltr;
        -webkit-font-smoothing: antialiased;
        user-select: none;
    }

    .left-details-container {
        position: fixed;
        left: clamp(20px, 4vw, 56px);
        bottom: 230px;
        z-index: 80;
        width: 240px;
        display: flex;
        flex-direction: column;
        align-items: flex-start;
        font-family: 'Inter Variable', Inter, sans-serif;
        font-weight: 300;
        color: #f5f7f8;
        pointer-events: auto;
        user-select: none;
    }

    :global(html.light-mode) .left-details-container {
        color: #111827;
    }

    .details-content {
        width: 100%;
        display: flex;
        flex-direction: column;
        align-items: flex-start;
    }

    button:focus {
        outline: none;
    }

    button:focus-visible {
        outline: 2px solid rgba(255, 255, 255, 0.65);
        outline-offset: 2px;
    }

    :global(html.light-mode) button:focus-visible {
        outline: 2px solid rgba(17, 24, 39, 0.65);
    }

    .close-btn {
        background: transparent;
        border: 0;
        color: #97a5ad;
        padding: 0;
        margin-bottom: 14px;
        cursor: pointer;
        display: flex;
        align-items: center;
        justify-content: center;
        width: 26px;
        height: 26px;
        border-radius: 6px;
        transition: color 150ms ease, transform 150ms ease;
    }

    .close-btn:hover {
        color: #ffffff;
        transform: scale(1.1);
    }

    :global(html.light-mode) .close-btn:hover {
        color: #111827;
    }

    .circle-badge {
        width: 170px;
        height: 170px;
        border-radius: 50%;
        background: #edece8;
        color: #111111;
        display: flex;
        align-items: center;
        justify-content: center;
        box-shadow: 0 10px 30px rgba(0, 0, 0, 0.35);
        margin-bottom: 20px;
        transition: background-color 200ms ease, color 200ms ease;
    }

    :global(html.light-mode) .circle-badge {
        background: #111111;
        color: #ffffff;
        box-shadow: 0 10px 30px rgba(0, 0, 0, 0.1);
    }

    .badge-main-text {
        font-family: 'Inter Variable', Inter, sans-serif;
        font-size: 3.4rem;
        font-weight: 300;
        line-height: 1;
        letter-spacing: -0.04em;
        text-transform: uppercase;
    }

    .divider {
        width: 100%;
        height: 1px;
        background: rgba(255, 255, 255, 0.15);
        margin-bottom: 14px;
    }

    :global(html.light-mode) .divider {
        background: rgba(0, 0, 0, 0.12);
    }

    .stats-stream {
        display: flex;
        flex-direction: column;
        gap: 8px;
        width: 100%;
        max-height: 44vh;
        overflow-y: auto;
        scrollbar-width: none;
        font-weight: 300;
    }

    .stats-stream::-webkit-scrollbar {
        display: none;
    }

    .stat-line {
        display: flex;
        align-items: baseline;
        gap: 6px;
        white-space: nowrap;
    }

    .stat-line.primary-title {
        margin-bottom: 2px;
    }

    .stat-value {
        font-family: 'Inter Variable', Inter, sans-serif;
        font-size: 0.94rem;
        font-weight: 300;
        letter-spacing: -0.01em;
        color: #ffffff;
    }

    .stat-value.text-large {
        font-size: 1.05rem;
    }

    :global(html.light-mode) .stat-value {
        color: #111827;
    }

    .stat-dash {
        color: #55626b;
        font-size: 0.72rem;
        font-weight: 300;
    }

    .stat-label {
        font-size: 0.65rem;
        font-weight: 300;
        letter-spacing: 0.08em;
        text-transform: uppercase;
        color: #8c9ba5;
    }

    :global(html.light-mode) .stat-label {
        color: #6b7280;
    }

    .status-running,
    .status-active {
        color: #6cb09f !important;
    }
    :global(html.light-mode) .status-running,
    :global(html.light-mode) .status-active {
        color: #2e8570 !important;
    }

    .status-waiting,
    .status-restricted {
        color: #f0c29a !important;
    }
    :global(html.light-mode) .status-waiting,
    :global(html.light-mode) .status-restricted {
        color: #c97d39 !important;
    }

    .status-derailed,
    .status-blocked {
        color: #de8489 !important;
    }
    :global(html.light-mode) .status-derailed,
    :global(html.light-mode) .status-blocked {
        color: #c95158 !important;
    }

    .sub-block {
        margin-top: 8px;
        display: flex;
        flex-direction: column;
        gap: 5px;
    }

    .sub-label {
        font-size: 0.62rem;
        font-weight: 300;
        letter-spacing: 0.1em;
        text-transform: uppercase;
        color: #55626b;
    }

    .interactive-pills {
        display: flex;
        flex-direction: column;
        gap: 4px;
    }

    .mini-pill {
        background: rgba(255, 255, 255, 0.04);
        border: 0;
        border-radius: 6px;
        padding: 6px 10px;
        color: inherit;
        display: flex;
        justify-content: space-between;
        align-items: center;
        cursor: pointer;
        font-family: inherit;
        font-size: 0.74rem;
        font-weight: 300;
        transition: background-color 150ms ease;
    }

    .mini-pill:hover {
        background: rgba(255, 255, 255, 0.08);
    }

    :global(html.light-mode) .mini-pill {
        background: rgba(0, 0, 0, 0.04);
    }

    :global(html.light-mode) .mini-pill:hover {
        background: rgba(0, 0, 0, 0.08);
    }

    .mini-pill small {
        color: #8c9ba5;
        font-size: 0.64rem;
        font-weight: 300;
        text-transform: uppercase;
    }

    .delay-alert {
        margin-top: 6px;
        padding: 8px;
        border-radius: 6px;
        background: rgba(222, 132, 137, 0.12);
        color: #de8489;
        font-size: 0.72rem;
        font-weight: 300;
    }

    .delay-alert p {
        margin: 2px 0 0;
        color: #f5f7f8;
        font-size: 0.68rem;
        font-weight: 300;
    }

    :global(html.light-mode) .delay-alert p {
        color: #111827;
    }

    .route-strip {
        display: flex;
        flex-direction: column;
        gap: 3px;
    }

    .route-dot-item {
        background: none;
        border: 0;
        border-radius: 4px;
        padding: 3px 4px;
        color: #8c9ba5;
        text-align: left;
        font-family: inherit;
        font-size: 0.72rem;
        font-weight: 300;
        cursor: pointer;
        transition: color 150ms ease;
    }

    .route-dot-item:hover {
        color: #ffffff;
    }

    :global(html.light-mode) .route-dot-item:hover {
        color: #111827;
    }

    .route-dot-item.is-active {
        color: #ffffff;
        font-weight: 400;
    }

    :global(html.light-mode) .route-dot-item.is-active {
        color: #111827;
    }

    .route-dot-item.is-passed {
        color: #55626b;
    }
</style>