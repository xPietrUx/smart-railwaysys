<script lang="ts">
    import { onDestroy, onMount } from 'svelte';
    import DetailsPanel from '$lib/components/network/DetailsPanel.svelte';
    import IncidentFeed from '$lib/components/network/IncidentFeed.svelte';
    import MapSearch from '$lib/components/network/MapSearch.svelte';
    import NetworkGraph from '$lib/components/network/NetworkGraph.svelte';
    import SimSpeedControl from '$lib/components/network/SimSpeedControl.svelte';
    import SimulationHeader from '$lib/components/network/SimulationHeader.svelte';
    import TimetableEditorModal from '$lib/components/network/TimetableEditorModal.svelte';
    import TimetablePanel from '$lib/components/network/TimetablePanel.svelte';
    import { createLiveStore } from '$lib/services/live';
    import { applyEventsToSegments } from '$lib/services/liveNetwork';
    import type { Scenario } from '$lib/types/scenario';
    import type { HighlightFilter, Selected } from '$lib/types/selection';
    import type { PageData } from './$types';

    export let data: PageData;

    $: permissions = data.user.permissions ?? [];
    $: canControl = permissions.includes('simulation.control');
    $: canManageTimetable = permissions.includes('timetable.manage');

    const live = createLiveStore(fetch, data.apiBaseUrl, {
        trains: data.trains,
        events: data.events,
        scenario: null,
        paused: false,
        speed: 1,
        simClockMinutes: 0,
        timestamp: data.timestamp
    });
    const { snapshot, status } = live;

    onMount(() => live.connect());
    onDestroy(() => live.disconnect());

    let selected: Selected | null = null;
    let highlight: HighlightFilter | null = null;
    let mapComponent: NetworkGraph | undefined;

    let isFullscreen = false;

    let editorOpen = false;
    let editorScenario: Scenario | null = null;
    let scenariosRefreshKey = 0;

    function openScenarioDetails(scenario: Scenario) {
        editorScenario = scenario;
        editorOpen = true;
    }

    function openScenarioCreate() {
        editorScenario = null;
        editorOpen = true;
    }

    function handleEditorClose(changed: boolean) {
        editorOpen = false;
        if (changed) scenariosRefreshKey += 1;
    }

    $: liveGraph = {
        ...data.graph,
        segments: applyEventsToSegments(data.graph.segments, $snapshot.events)
    };

    function handleWindowKeydown(event: KeyboardEvent) {
        if (event.key === 'Escape') {
            if (isFullscreen) {
                isFullscreen = false;
                return;
            }
            if (!editorOpen) {
                selected = null;
                highlight = null;
            }
        }
    }

    function handleMapSelect(sel: Selected) {
        selected = sel;
        mapComponent?.focusOn(sel);
    }
</script>

<svelte:head>
    <title>Smart Railway System — autonomiczna sieć kolejowa</title>
    <meta
        name="description"
        content="Autonomiczna symulacja pociągów na sieci kolejowej województwa śląskiego, na żywo z Memgraph."
    />
</svelte:head>

<svelte:window on:keydown={handleWindowKeydown} />

<main class="stage" class:fullscreen-mode={isFullscreen}>
    <div class="map-layer">
        <NetworkGraph
            bind:this={mapComponent}
            graph={liveGraph}
            trains={$snapshot.trains}
            events={$snapshot.events}
            bind:highlight
            bind:selected
            {isFullscreen}
            on:toggleFullscreen={() => (isFullscreen = !isFullscreen)}
        />
        {#if !isFullscreen}
            <div class="speed-corner">
                <SimSpeedControl snapshot={$snapshot} apiBaseUrl={data.apiBaseUrl} readOnly={!canControl} />
            </div>
        {/if}
    </div>

    {#if !isFullscreen}
        <div class="topbar">
            <SimulationHeader
                snapshot={$snapshot}
                status={$status}
                apiBaseUrl={data.apiBaseUrl}
                bind:highlight
                user={data.user}
                readOnly={!canControl}
            />
        </div>

        <div class="search-layer">
            <MapSearch
                graph={liveGraph}
                trains={$snapshot.trains}
                events={$snapshot.events}
                onSelect={handleMapSelect}
            />
        </div>
    {/if}

    <aside class="dock dock-left" class:hidden={isFullscreen}>
        <IncidentFeed events={$snapshot.events} onSelect={handleMapSelect} />
    </aside>

    <aside class="dock dock-right" class:hidden={isFullscreen}>
        {#if selected}
            <DetailsPanel
                graph={liveGraph}
                trains={$snapshot.trains}
                events={$snapshot.events}
                bind:selected
            />
        {/if}
        <TimetablePanel
            apiBaseUrl={data.apiBaseUrl}
            scenario={$snapshot.scenario}
            refreshKey={scenariosRefreshKey}
            onDetails={openScenarioDetails}
            onCreate={openScenarioCreate}
            readOnly={!canManageTimetable}
        />
    </aside>

    {#if editorOpen}
        <TimetableEditorModal
            apiBaseUrl={data.apiBaseUrl}
            graph={liveGraph}
            scenario={editorScenario}
            onClose={handleEditorClose}
        />
    {/if}
</main>

<style>
    :global(html),
    :global(body) {
        height: 100%;
    }

    :global(body) {
        margin: 0;
        font-family: 'Inter Variable', Inter, sans-serif;
        background: #141414;
        color: #f5f7f8;
        font-weight: 300;
    }

    .stage {
        position: relative;
        height: 100dvh;
        overflow: hidden;
    }

    .map-layer {
        position: absolute;
        inset: 0;
    }

    .speed-corner {
        position: absolute;
        left: 20px;
        bottom: 20px;
        z-index: 15;
    }

    .search-layer {
        position: absolute;
        top: 118px;
        left: 50%;
        transform: translateX(-50%);
        z-index: 18;
    }

    .topbar {
        position: absolute;
        top: 20px;
        left: 24px;
        right: 24px;
        z-index: 20;
        pointer-events: none;
    }

    .topbar :global(.bar) {
        pointer-events: auto;
    }

    .dock {
        position: absolute;
        top: 96px;
        bottom: 24px;
        z-index: 10;
        width: min(320px, 86vw);
        display: flex;
        flex-direction: column;
        align-items: stretch;
        gap: 12px;
        pointer-events: none;
        transition: opacity 200ms ease, transform 200ms ease;
    }

    /* Poszerzony prawy panel (rozkłady jazdy / detali) */
    .dock-right {
        right: 24px;
        width: min(400px, 90vw);
    }

    .dock.hidden {
        opacity: 0;
        pointer-events: none;
        transform: scale(0.98);
    }

    .dock > :global(*) {
        pointer-events: auto;
        max-height: 100%;
        overflow-y: auto;
        flex: 0 1 auto;
        min-height: 0;
    }

    /* Minimalistyczny scrollbar w formie kropki/pigułki dla elementów wewnątrz doków */
    .dock > :global(*)::-webkit-scrollbar {
        width: 8px;
        height: 8px;
    }

    .dock > :global(*)::-webkit-scrollbar-track {
        background: transparent;
    }

    .dock > :global(*)::-webkit-scrollbar-thumb {
        background: rgba(245, 247, 248, 0.4);
        border-radius: 999px;
        border: 2px solid transparent;
        background-clip: padding-box;
    }

    .dock > :global(*)::-webkit-scrollbar-thumb:hover {
        background: rgba(245, 247, 248, 0.75);
    }

    .dock-left {
        left: 24px;
        bottom: 24px;
    }

    @media (max-width: 1400px) {
        .dock {
            top: 110px;
        }

        .search-layer {
            top: 128px;
        }
    }

    @media (max-width: 900px) {
        .stage {
            height: auto;
            min-height: 100dvh;
            overflow: visible;
            display: flex;
            flex-direction: column;
            gap: 12px;
            padding: 12px;
            box-sizing: border-box;
        }

        .map-layer {
            position: relative;
            inset: auto;
            height: 60vh;
            border-radius: 14px;
            overflow: hidden;
            order: 2;
        }

        .topbar {
            position: static;
            pointer-events: auto;
            order: 1;
        }

        .search-layer {
            position: static;
            transform: none;
            align-self: center;
            order: 1;
        }

        .dock {
            position: static;
            width: auto;
            pointer-events: auto;
        }

        .dock-right {
            width: auto;
        }

        .dock.hidden {
            display: none;
        }

        .dock > :global(*) {
            max-height: none;
            overflow-y: visible;
        }

        .dock-right {
            order: 3;
        }

        .dock-left {
            order: 4;
        }
    }
</style>