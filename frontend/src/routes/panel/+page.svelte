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

    let showLeftDock = true;
    let showRightDock = true;

    let editorOpen = false;
    let editorScenario: Scenario | null = null;
    let scenariosRefreshKey = 0;

    // IncidentFeed i NetworkGraph są rodzeństwem, więc stan wskazywania celu na
    // mapie (typ + funkcja rozwiązująca wybór) musi mieszkać tutaj, żeby móc
    // płynąć w obie strony.
    let pickMode: 'segment' | 'station' | 'train' | null = null;
    let pickResolver: ((id: string) => void) | null = null;

    function startPick(mode: 'segment' | 'station' | 'train', resolve: (id: string) => void) {
        pickMode = mode;
        pickResolver = resolve;
    }

    function cancelPick() {
        pickMode = null;
        pickResolver = null;
    }

    function handleMapPick(id: string) {
        const resolve = pickResolver;
        cancelPick();
        resolve?.(id);
    }

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
            if (pickMode) {
                cancelPick();
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
    <!-- 1. Najwyższy priorytet w tabulacji: Nagłówek i wyszukiwarka -->
    {#if !isFullscreen}
        <header class="top-region" aria-label="Nawigacja i sterowanie symulacją">
            <div class="topbar-wrapper">
                <SimulationHeader
                    snapshot={$snapshot}
                    status={$status}
                    apiBaseUrl={data.apiBaseUrl}
                    bind:highlight
                    user={data.user}
                    readOnly={!canControl}
                />
            </div>
            <div class="search-wrapper">
                <MapSearch
                    graph={liveGraph}
                    trains={$snapshot.trains}
                    events={$snapshot.events}
                    onSelect={handleMapSelect}
                />
            </div>
        </header>

        <!-- 2. Drugi priorytet: Lewy Dok (Zdarzenia) -->
        <aside class="dock dock-left" class:collapsed={!showLeftDock} aria-label="Panel zdarzeń">
            {#if showLeftDock}
                <div class="dock-wrapper">
                    <button
                        type="button"
                        class="dock-close-btn"
                        on:click={() => (showLeftDock = false)}
                        title="Zwiń zdarzenia"
                        aria-label="Zwiń zdarzenia"
                    >
                        <span class="material-symbols-outlined" aria-hidden="true">close</span>
                    </button>
                    <div class="dock-content">
                        <IncidentFeed
                            events={$snapshot.events}
                            stations={liveGraph.stations}
                            segments={liveGraph.segments}
                            onSelect={handleMapSelect}
                            readOnly={!canControl}
                            {pickMode}
                            onStartPick={startPick}
                            onCancelPick={cancelPick}
                        />
                    </div>
                </div>
            {:else}
                <button
                    type="button"
                    class="dock-collapsed-btn"
                    on:click={() => (showLeftDock = true)}
                    title="Pokaż zdarzenia"
                    aria-label="Pokaż zdarzenia"
                >
                    <span class="material-symbols-outlined" aria-hidden="true">warning</span>
                </button>
            {/if}
        </aside>

        <!-- 3. Trzeci priorytet: Prawy Dok (Dyspozytura i szczegóły) -->
        <aside class="dock dock-right" class:collapsed={!showRightDock} aria-label="Panel dyspozytorski">
            {#if showRightDock}
                <div class="dock-wrapper">
                    <button
                        type="button"
                        class="dock-close-btn"
                        on:click={() => (showRightDock = false)}
                        title="Zwiń dyspozyturę"
                        aria-label="Zwiń dyspozyturę"
                    >
                        <span class="material-symbols-outlined" aria-hidden="true">close</span>
                    </button>
                    <div class="dock-content">
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
                    </div>
                </div>
            {:else}
                <button
                    type="button"
                    class="dock-collapsed-btn"
                    on:click={() => (showRightDock = true)}
                    title="Pokaż dyspozyturę"
                    aria-label="Pokaż dyspozyturę"
                >
                    <span class="material-symbols-outlined" aria-hidden="true">tune</span>
                </button>
            {/if}
        </aside>
    {/if}

    <!-- 4. Czwarty priorytet: Mapa, kontrolki widoku oraz sterowanie prędkością -->
    <section class="map-layer" aria-label="Mapa sieci kolejowej">
        <NetworkGraph
            bind:this={mapComponent}
            graph={liveGraph}
            trains={$snapshot.trains}
            events={$snapshot.events}
            bind:highlight
            bind:selected
            {isFullscreen}
            {pickMode}
            onPick={handleMapPick}
            onCancelPick={cancelPick}
            on:toggleFullscreen={() => (isFullscreen = !isFullscreen)}
        />

        {#if !isFullscreen}
            <div class="speed-corner">
                <SimSpeedControl snapshot={$snapshot} apiBaseUrl={data.apiBaseUrl} readOnly={!canControl} />
            </div>
        {/if}
    </section>

    <!-- Modal edycji scenariusza rozkładu jazdy -->
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
        margin: 0;
        padding: 0;
        box-sizing: border-box;
    }

    :global(body) {
        font-family: 'Inter Variable', Inter, sans-serif;
        background: #141414;
        color: #f5f7f8;
        font-weight: 300;
        overflow: hidden;
    }

    .stage {
        position: relative;
        width: 100vw;
        height: 100dvh;
        overflow: hidden;
    }

    .map-layer {
        position: absolute;
        inset: 0;
        z-index: 1;
    }

    .speed-corner {
        position: absolute;
        left: 20px;
        bottom: 20px;
        z-index: 15;
    }

    /* Górny obszar sterowania */
    .top-region {
        position: absolute;
        top: 14px;
        left: 0;
        right: 0;
        z-index: 25;
        display: flex;
        flex-direction: column;
        align-items: center;
        gap: 10px;
        pointer-events: none;
        padding: 0 16px;
    }

    .topbar-wrapper {
        width: 100%;
        max-width: 1440px;
        pointer-events: auto;
    }

    .search-wrapper {
        pointer-events: auto;
    }

    /* Doki boczne */
    .dock {
        position: absolute;
        top: 130px;
        bottom: 24px;
        z-index: 20;
        width: clamp(280px, 23vw, 340px);
        pointer-events: none;
    }

    .dock-left {
        left: 20px;
        bottom: 120px;
    }

    .dock-right {
        right: 20px;
    }

    .dock-wrapper {
        position: relative;
        height: 100%;
        display: flex;
        flex-direction: column;
    }

    .dock-content {
        display: flex;
        flex-direction: column;
        gap: 12px;
        flex: 1;
        min-height: 0;
        pointer-events: none;
    }

    .dock-content > :global(*) {
        pointer-events: auto;
        max-height: 100%;
        overflow-y: auto;
        flex: 0 1 auto;
        min-height: 0;
    }

    /* Przycisk zamknięcia doku */
    .dock-close-btn {
        position: absolute;
        top: 10px;
        right: 10px;
        z-index: 10;
        width: 26px;
        height: 26px;
        border-radius: 50%;
        border: 0;
        background: rgba(255, 255, 255, 0.08);
        color: #97a5ad;
        display: inline-flex;
        align-items: center;
        justify-content: center;
        cursor: pointer;
        padding: 0;
        box-shadow: none !important;
        pointer-events: auto;
        transition: background-color 150ms ease, color 150ms ease;
    }

    .dock-close-btn:focus-visible,
    .dock-collapsed-btn:focus-visible {
        outline: 2px solid rgba(255, 255, 255, 0.7);
        outline-offset: 2px;
    }

    :global(html.light-mode) .dock-close-btn {
        background: rgba(0, 0, 0, 0.06);
        color: #52606a;
    }

    :global(html.light-mode) .dock-close-btn:focus-visible,
    :global(html.light-mode) .dock-collapsed-btn:focus-visible {
        outline-color: rgba(17, 24, 39, 0.7);
    }

    .dock-close-btn:hover {
        background: rgba(255, 255, 255, 0.16);
        color: #ffffff;
    }

    :global(html.light-mode) .dock-close-btn:hover {
        background: rgba(0, 0, 0, 0.12);
        color: #111827;
    }

    .dock-close-btn .material-symbols-outlined {
        font-size: 15px;
        line-height: 1;
    }

    /* Zwinięty dok */
    .dock.collapsed {
        width: 38px;
        height: 38px;
        bottom: auto;
    }

    .dock-collapsed-btn {
        width: 38px;
        height: 38px;
        border-radius: 50%;
        border: 0;
        background: rgba(255, 255, 255, 0.08);
        backdrop-filter: blur(12px);
        -webkit-backdrop-filter: blur(12px);
        color: #f5f7f8;
        display: inline-flex;
        align-items: center;
        justify-content: center;
        cursor: pointer;
        padding: 0;
        box-shadow: none !important;
        pointer-events: auto;
        transition: background-color 150ms ease, color 150ms ease;
    }

    :global(html.light-mode) .dock-collapsed-btn {
        background: rgba(0, 0, 0, 0.05);
        color: #111827;
        box-shadow: none !important;
    }

    .dock-collapsed-btn:hover {
        background: rgba(255, 255, 255, 0.14);
        color: #ffffff;
    }

    :global(html.light-mode) .dock-collapsed-btn:hover {
        background: rgba(0, 0, 0, 0.1);
        color: #111827;
    }

    .dock-collapsed-btn .material-symbols-outlined {
        font-size: 18px;
        font-weight: 200;
        line-height: 1;
        user-select: none;
    }

    @media (max-width: 1300px) {
        .dock {
            top: 140px;
            width: clamp(260px, 24vw, 300px);
        }
    }

    @media (max-width: 1080px) {
        .dock {
            top: 145px;
            width: 280px;
        }

        .dock-left {
            bottom: 110px;
        }
    }

    @media (max-width: 820px) {
        .stage {
            overflow-y: auto;
            height: auto;
            min-height: 100dvh;
            display: flex;
            flex-direction: column;
            padding: 12px;
            gap: 12px;
            box-sizing: border-box;
        }

        .top-region {
            position: static;
            padding: 0;
            pointer-events: auto;
        }

        .map-layer {
            position: relative;
            height: 55vh;
            border-radius: 12px;
            overflow: hidden;
            order: 2;
        }

        .dock {
            position: static;
            width: 100%;
            pointer-events: auto;
        }

        .dock-left {
            order: 3;
            bottom: auto;
        }

        .dock-right {
            order: 4;
        }
    }
</style>