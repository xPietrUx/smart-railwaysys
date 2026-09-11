<script lang="ts">
    import { SvelteMap } from 'svelte/reactivity';
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

    function formatLine(segment: TrackSegment) {
        return `${$t('details.line')} ${segment.line}`;
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
    <div class="panel details">
        <div class="panel-header">
            <div>
                <p class="panel-label">
                    {#if selectedKind === 'train'}
                        {$t('details.train')}
                    {:else if selectedKind === 'segment'}
                        {$t('details.segment')}
                    {:else}
                        {$t('details.station')}
                    {/if}
                </p>
                <h2>
                    {#if selectedKind === 'station'}
                        {selectedStation?.name}
                    {:else if selectedKind === 'segment'}
                        {selectedSegment?.segmentId}
                    {:else}
                        {selectedTrain?.name}
                    {/if}
                </h2>
            </div>
            <button type="button" class="close" on:click={close} aria-label={$t('details.close')}>
                <span class="material-symbols-outlined" aria-hidden="true">close</span>
            </button>
        </div>

        {#if selectedKind === 'station' && selectedStation}
            <div class="detail-grid">
                <div><span>{$t('details.code')}</span><strong>{selectedStation.code}</strong></div>
                <div>
                    <span>{$t('details.type')}</span><strong
                        >{formatStationType(selectedStation.type, $t)}</strong
                    >
                </div>
                <div>
                    <span>{$t('details.platforms')}</span><strong>{selectedStation.platforms}</strong>
                </div>
                <div><span>{$t('details.tracks')}</span><strong>{selectedStation.tracks}</strong></div>
                <div>
                    <span>{$t('details.trainsPerDay')}</span><strong>{selectedStation.dailyTrains}</strong>
                </div>
                <div>
                    <span>{$t('details.connections')}</span><strong
                        >{degreeByStation.get(selectedStation.id) ?? 0}</strong
                    >
                </div>
            </div>

            {#if (trainsByStation.get(selectedStation.id) ?? []).length > 0}
                <div class="section">
                    <h3>{$t('details.trainsAtStation')}</h3>
                    <ul class="connections">
                        {#each trainsByStation.get(selectedStation.id) ?? [] as train (train.id)}
                            <li>
                                <button
                                    type="button"
                                    class="train-chip status-{train.status}"
                                    on:click={() => pickTrain(train.id)}
                                >
                                    <div>
                                        <strong>{train.name}</strong>
                                        <span>{trainTypeLabel(train.type, $t)} · {relationLabel(train)}</span>
                                    </div>
                                    <small>{trainStatusLabel(train.status, $t)}</small>
                                </button>
                            </li>
                        {/each}
                    </ul>
                </div>
            {/if}

            <div class="section">
                <h3>{$t('details.nearestConnections')}</h3>
                <ul class="connections">
                    {#each connectedSegments as segment (segment.segmentId)}
                        <li>
                            <button type="button" on:click={() => pickSegment(segment.segmentId)}>
                                <div>
                                    <strong>{segment.segmentId}</strong>
                                    <span>{formatLine(segment)} · {segment.distKm} km</span>
                                </div>
                                <small>
                                    {stationById.get(segment.source)?.name} → {stationById.get(segment.target)?.name}
                                </small>
                            </button>
                        </li>
                    {/each}
                </ul>
            </div>
        {:else if selectedKind === 'segment' && selectedSegment}
            <div class="detail-grid">
                <div><span>{$t('details.line')}</span><strong>{selectedSegment.line}</strong></div>
                <div><span>{$t('details.length')}</span><strong>{selectedSegment.distKm} km</strong></div>
                <div>
                    <span>{$t('details.travelTime')}</span><strong>{selectedSegment.travelMin} min</strong>
                </div>
                <div><span>Vmax</span><strong>{selectedSegment.vmax} km/h</strong></div>
                <div><span>{$t('details.tracks')}</span><strong>{selectedSegment.railTracks}</strong></div>
            </div>

            <div class="section">
                <h3>{$t('details.directionState')}</h3>
                <div class="direction-grid">
                    <div class="direction-card status-{selectedSegment.forward.status}">
                        <span>
                            {stationById.get(selectedSegment.source)?.name} → {stationById.get(
                                selectedSegment.target
                            )?.name}
                        </span>
                        <strong>{directionStatusLabel(selectedSegment.forward.status, $t)}</strong>
                        {#if selectedSegment.forward.restrictedVmax}
                            <small>{$t('details.upTo', { speed: selectedSegment.forward.restrictedVmax })}</small>
                        {/if}
                    </div>
                    <div class="direction-card status-{selectedSegment.backward.status}">
                        <span>
                            {stationById.get(selectedSegment.target)?.name} → {stationById.get(
                                selectedSegment.source
                            )?.name}
                        </span>
                        <strong>{directionStatusLabel(selectedSegment.backward.status, $t)}</strong>
                        {#if selectedSegment.backward.restrictedVmax}
                            <small>{$t('details.upTo', { speed: selectedSegment.backward.restrictedVmax })}</small
                            >
                        {/if}
                    </div>
                </div>
            </div>

            {#if trainsOnSelectedSegment.length > 0}
                <div class="section">
                    <h3>{$t('details.trainsOnSegment')}</h3>
                    <ul class="connections">
                        {#each trainsOnSelectedSegment as train (train.id)}
                            <li>
                                <button
                                    type="button"
                                    class="train-chip status-{train.status}"
                                    on:click={() => pickTrain(train.id)}
                                >
                                    <div>
                                        <strong>{train.name}</strong>
                                        <span>{trainTypeLabel(train.type, $t)}</span>
                                    </div>
                                    <small>{Math.round(train.progress * 100)}%</small>
                                </button>
                            </li>
                        {/each}
                    </ul>
                </div>
            {/if}

            <div class="section">
                <h3>{$t('details.connects')}</h3>
                <ul class="connections">
                    <li>
                        <button type="button" on:click={() => pickStation(selectedSegment?.source ?? '')}>
                            <div>
                                <strong>{stationById.get(selectedSegment?.source ?? '')?.name}</strong>
                                <span>{selectedSegment?.source}</span>
                            </div>
                            <small>{$t('details.stationA')}</small>
                        </button>
                    </li>
                    <li>
                        <button type="button" on:click={() => pickStation(selectedSegment?.target ?? '')}>
                            <div>
                                <strong>{stationById.get(selectedSegment?.target ?? '')?.name}</strong>
                                <span>{selectedSegment?.target}</span>
                            </div>
                            <small>{$t('details.stationB')}</small>
                        </button>
                    </li>
                </ul>
            </div>
        {:else if selectedKind === 'train' && selectedTrain}
            <p class="train-relation">{relationLabel(selectedTrain)}</p>

            <div class="detail-grid">
                <div>
                    <span>{$t('details.status')}</span><strong
                        >{trainStatusLabel(selectedTrain.status, $t)}</strong
                    >
                </div>
                <div>
                    <span>{$t('details.type')}</span><strong>{trainTypeLabel(selectedTrain.type, $t)}</strong>
                </div>
                <div>
                    <span>{$t('details.nextStop')}</span>
                    <strong>
                        {selectedTrain.status === 'running' ? stationName(selectedTrain.nextStationId) : '—'}
                    </strong>
                </div>
                <div>
                    <span>{$t('details.segmentProgress')}</span><strong
                        >{Math.round(selectedTrain.progress * 100)}%</strong
                    >
                </div>
                <div><span>Vmax</span><strong>{selectedTrain.vmax} km/h</strong></div>
                <div>
                    <span>{$t('details.direction')}</span>
                    <strong
                        >{selectedTrain.direction === 'outbound'
                            ? $t('details.outbound')
                            : $t('details.return')}</strong
                    >
                </div>
            </div>

            {#if selectedTrainDelayEvent}
                <div class="delay-card">
                    <strong class="delay-title">
                        <span class="material-symbols-outlined inline-icon" aria-hidden="true">warning</span>
                        {$t('details.delayedByIncident')}
                    </strong>
                    <p>{formatEventMessage(selectedTrainDelayEvent, $t, stationName)}</p>
                </div>
            {/if}

            {#if selectedTrain.routeStationIds.length > 0}
                <div class="section">
                    <h3>{$t('details.route', { destination: stationName(selectedTrainTargetId) })}</h3>
                    <ol class="route-list">
                        {#each selectedTrain.routeStationIds as stationId, index (`${index}-${stationId}`)}
                            <li
                                class:current={index === selectedTrain.routeIndex}
                                class:passed={index < selectedTrain.routeIndex}
                            >
                                <button type="button" on:click={() => pickStation(stationId)}>
                                    {stationName(stationId)}
                                </button>
                                {#if index === selectedTrain.routeIndex}
                                    <small>
                                        {#if selectedTrain.status === 'running'}
                                            {$t('details.enRouteTo', {
                                                station: stationName(selectedTrain.nextStationId)
                                            })}
                                        {:else}
                                            {trainStatusLabel(selectedTrain.status, $t)}
                                        {/if}
                                    </small>
                                {/if}
                            </li>
                        {/each}
                    </ol>
                </div>
            {/if}
        {/if}
    </div>
{/if}

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
        font-family: 'Inter Variable', Inter, sans-serif;
        color: #f5f7f8;
    }

    .panel-header {
        display: flex;
        justify-content: space-between;
        align-items: flex-start;
        gap: 12px;
        margin-bottom: 14px;
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
    h3,
    p {
        margin: 0;
    }

    h2 {
        font-size: 1.1rem;
        font-weight: 400;
        letter-spacing: 0.04em;
        text-transform: uppercase;
        color: #ffffff;
    }

    .close {
        border: 0;
        background: transparent;
        color: #97a5ad;
        width: 28px;
        height: 28px;
        border-radius: 6px;
        display: flex;
        align-items: center;
        justify-content: center;
        cursor: pointer;
        flex-shrink: 0;
        transition: color 150ms ease, background-color 150ms ease;
    }

    .close .material-symbols-outlined {
        font-size: 18px;
    }

    .close:hover {
        color: #ffffff;
        background: rgba(255, 255, 255, 0.06);
    }

    .detail-grid {
        display: grid;
        grid-template-columns: repeat(2, minmax(0, 1fr));
        gap: 8px;
    }

    .detail-grid > div {
        background: rgba(255, 255, 255, 0.03);
        border-radius: 10px;
        padding: 10px 12px;
    }

    .detail-grid span,
    .connections small {
        display: block;
        color: #97a5ad;
        font-size: 0.68rem;
        font-weight: 300;
        letter-spacing: 0.06em;
        text-transform: uppercase;
    }

    .detail-grid strong {
        display: block;
        margin-top: 4px;
        font-size: 0.88rem;
        font-weight: 400;
        letter-spacing: 0.04em;
        color: #f5f7f8;
    }

    .train-relation {
        margin: 0 0 14px;
        padding: 10px 12px;
        border-radius: 10px;
        background: rgba(255, 255, 255, 0.04);
        font-weight: 400;
        font-size: 0.78rem;
        letter-spacing: 0.06em;
        text-transform: uppercase;
        color: #f5f7f8;
    }

    .delay-card {
        margin-top: 14px;
        padding: 12px;
        border-radius: 10px;
        background: rgba(222, 132, 137, 0.1);
    }

    .delay-title {
        display: flex;
        align-items: center;
        gap: 6px;
        font-size: 0.74rem;
        font-weight: 400;
        letter-spacing: 0.06em;
        text-transform: uppercase;
        color: #de8489;
    }

    .inline-icon {
        font-size: 16px;
    }

    .delay-card p {
        margin: 6px 0 0;
        font-size: 0.74rem;
        font-weight: 300;
        letter-spacing: 0.02em;
        color: #f5f7f8;
        line-height: 1.4;
    }

    .route-list {
        list-style: none;
        margin: 0;
        padding: 0;
        display: grid;
        gap: 4px;
    }

    .route-list li {
        display: flex;
        align-items: center;
        gap: 10px;
        padding-left: 14px;
        position: relative;
    }

    .route-list li::before {
        content: '';
        position: absolute;
        left: 0;
        width: 6px;
        height: 6px;
        border-radius: 999px;
        background: rgba(255, 255, 255, 0.2);
    }

    .route-list li.passed::before {
        background: rgba(255, 255, 255, 0.08);
    }

    .route-list li.current::before {
        background: #f5f7f8;
        box-shadow: 0 0 8px rgba(245, 247, 248, 0.6);
    }

    .route-list button {
        background: none;
        border: 0;
        color: #97a5ad;
        font-family: inherit;
        font-size: 0.76rem;
        font-weight: 300;
        letter-spacing: 0.04em;
        text-transform: uppercase;
        padding: 4px 0;
        cursor: pointer;
        text-align: left;
    }

    .route-list li.passed button {
        color: #55626b;
    }

    .route-list li.current button {
        color: #ffffff;
        font-weight: 400;
    }

    .route-list button:hover {
        color: #ffffff;
    }

    .route-list small {
        color: #97a5ad;
        font-size: 0.68rem;
        font-weight: 300;
        letter-spacing: 0.04em;
        white-space: nowrap;
    }

    .section {
        margin-top: 18px;
    }

    .section h3 {
        margin-bottom: 10px;
        font-size: 0.68rem;
        font-weight: 400;
        letter-spacing: 0.08em;
        text-transform: uppercase;
        color: #97a5ad;
    }

    .direction-grid {
        display: grid;
        grid-template-columns: 1fr;
        gap: 8px;
    }

    .direction-card {
        border-radius: 10px;
        padding: 10px 12px;
        background: rgba(255, 255, 255, 0.03);
    }

    .direction-card span {
        display: block;
        font-size: 0.68rem;
        font-weight: 300;
        letter-spacing: 0.06em;
        text-transform: uppercase;
        color: #97a5ad;
    }

    .direction-card strong {
        display: block;
        margin-top: 4px;
        font-size: 0.82rem;
        font-weight: 400;
        letter-spacing: 0.04em;
        text-transform: uppercase;
        color: #f5f7f8;
    }

    .direction-card small {
        display: block;
        margin-top: 4px;
        color: #f0c29a;
        font-size: 0.68rem;
        font-weight: 300;
        letter-spacing: 0.04em;
        text-transform: uppercase;
    }

    .direction-card.status-active strong {
        color: #6cb09f;
    }

    .direction-card.status-restricted strong {
        color: #f0c29a;
    }

    .direction-card.status-blocked strong {
        color: #de8489;
    }

    .connections {
        list-style: none;
        padding: 0;
        margin: 0;
        display: grid;
        gap: 6px;
    }

    .connections button {
        width: 100%;
        text-align: left;
        border: 0;
        background: rgba(255, 255, 255, 0.03);
        color: inherit;
        padding: 10px 12px;
        border-radius: 10px;
        display: flex;
        justify-content: space-between;
        align-items: center;
        gap: 12px;
        cursor: pointer;
        transition: background-color 150ms ease;
    }

    .connections button:hover {
        background: rgba(255, 255, 255, 0.06);
    }

    .connections strong {
        display: block;
        font-size: 0.78rem;
        font-weight: 400;
        letter-spacing: 0.06em;
        text-transform: uppercase;
        color: #f5f7f8;
    }

    .connections span {
        display: block;
        color: #97a5ad;
        font-size: 0.72rem;
        font-weight: 300;
        letter-spacing: 0.04em;
        text-transform: uppercase;
        margin-top: 2px;
    }

    .train-chip strong {
        display: block;
        font-size: 0.78rem;
        font-weight: 400;
        letter-spacing: 0.06em;
        text-transform: uppercase;
        color: #f5f7f8;
    }

    .train-chip span {
        display: block;
        color: #97a5ad;
        font-size: 0.72rem;
        font-weight: 300;
        letter-spacing: 0.04em;
        text-transform: uppercase;
        margin-top: 2px;
    }

    .train-chip small {
        font-weight: 400;
        letter-spacing: 0.06em;
        text-transform: uppercase;
        white-space: nowrap;
    }

    .train-chip.status-waiting small {
        color: #f0c29a;
    }

    .train-chip.status-derailed small {
        color: #de8489;
    }

    .train-chip.status-dwelling small {
        color: #97a5ad;
    }
</style>