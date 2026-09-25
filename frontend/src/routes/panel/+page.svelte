<script lang="ts">
    import { onDestroy, onMount } from 'svelte';
    import { fade } from 'svelte/transition';
    import { t } from '$lib/i18n'; 
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

    $: user = data?.user ?? null;
    $: permissions = user?.permissions ?? [];
    $: canControl = permissions.includes('simulation.control');
    $: canManageTimetable = permissions.includes('timetable.manage');
    $: isAdmin = permissions.includes('users.manage');

    const live = createLiveStore(fetch, data?.apiBaseUrl ?? '', {
        trains: data?.trains ?? [],
        events: data?.events ?? [],
        scenario: null,
        paused: false,
        speed: 1,
        simClockMinutes: 0,
        timestamp: data?.timestamp ?? Date.now() / 1000
    });
    const { snapshot, status } = live;

    onMount(() => {
        document.body.style.overflow = 'hidden';
        live.connect();
        return () => {
            document.body.style.overflow = '';
        };
    });
    onDestroy(() => live.disconnect());

    let selected: Selected | null = null;
    let highlight: HighlightFilter | null = null;
    let mapComponent: NetworkGraph | undefined;

    let isFullscreen = false;

    let showIncidents = false;
    let showTimetable = false;

    let editorOpen = false;
    let editorScenario: Scenario | null = null;
    let scenariosRefreshKey = 0;

    // wskazywanie celu na mapie
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

    $: liveGraph = data?.graph
        ? {
                ...data.graph,
                segments: applyEventsToSegments(data.graph.segments, $snapshot.events)
          }
        : { stations: [], segments: [], relationshipCount: 0 };

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
            if (showIncidents) {
                showIncidents = false;
                return;
            }
            if (showTimetable) {
                showTimetable = false;
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
    <title>Smart Railway System</title>
</svelte:head>

<svelte:window on:keydown={handleWindowKeydown} />

<main class="stage" class:fullscreen-mode={isFullscreen}>
    {#if !isFullscreen}
        <!-- Nagłówek i wyszukiwarka -->
        <header class="top-region" aria-label={$t('dock.navAria')}>
            <div class="topbar-wrapper">
                <SimulationHeader
                    snapshot={$snapshot}
                    status={$status}
                    apiBaseUrl={data.apiBaseUrl}
                    bind:highlight
                    {user}
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

        <!-- Szczegóły obiektu po lewej stronie -->
        {#if selected}
            <DetailsPanel
                graph={liveGraph}
                trains={$snapshot.trains}
                events={$snapshot.events}
                bind:selected
            />
        {/if}

        <!-- Prawa strona: 3 okrągłe ikony + wysuwane panele -->
        <aside class="right-menu-dock" aria-label={$t('dock.menuAria')}>
            <div class="side-buttons-column">
                <!-- 1. Incydenty -->
                <button
                    type="button"
                    class="circle-menu-btn"
                    class:active={showIncidents}
                    on:click={() => {
                        showIncidents = !showIncidents;
                        if (showIncidents) showTimetable = false;
                    }}
                    title={$t('dock.incidents')}
                    aria-label={$t('dock.incidents')}
                    aria-expanded={showIncidents}
                >
                    <span class="material-symbols-outlined" aria-hidden="true">warning</span>
                </button>

                <!-- 2. Panel administracji -->
                {#if isAdmin}
                    <a
                        href="/admin"
                        class="circle-menu-btn"
                        title={$t('dock.admin')}
                        aria-label={$t('dock.admin')}
                        data-sveltekit-preload-data="off"
                    >
                        <span class="material-symbols-outlined" aria-hidden="true">settings</span>
                    </a>
                {:else}
                    <div class="circle-menu-btn disabled" title={$t('dock.adminDisabled')}>
                        <span class="material-symbols-outlined" aria-hidden="true">settings</span>
                    </div>
                {/if}

                <!-- 3. Scenariusze symulacji -->
                <button
                    type="button"
                    class="circle-menu-btn"
                    class:active={showTimetable}
                    on:click={() => {
                        showTimetable = !showTimetable;
                        if (showTimetable) showIncidents = false;
                    }}
                    title={$t('dock.scenarios')}
                    aria-label={$t('dock.scenarios')}
                    aria-expanded={showTimetable}
                >
                    <span class="material-symbols-outlined" aria-hidden="true">calendar_month</span>
                </button>
            </div>

            <!-- Panel Incydentów z animacją fade -->
            {#if showIncidents}
                <div class="flyout-panel" transition:fade={{ duration: 180 }}>
                    <button
                        type="button"
                        class="panel-close-x"
                        on:click={() => (showIncidents = false)}
                        title={$t('editor.close')}
                        aria-label={$t('editor.close')}
                    >
                        <span class="material-symbols-outlined" aria-hidden="true">close</span>
                    </button>
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
            {/if}

            {#if showTimetable}
                <div class="flyout-panel" transition:fade={{ duration: 180 }}>
                    <button
                        type="button"
                        class="panel-close-x"
                        on:click={() => (showTimetable = false)}
                        title={$t('editor.close')}
                        aria-label={$t('editor.close')}
                    >
                        <span class="material-symbols-outlined" aria-hidden="true">close</span>
                    </button>
                    <TimetablePanel
                        apiBaseUrl={data.apiBaseUrl}
                        scenario={$snapshot.scenario}
                        refreshKey={scenariosRefreshKey}
                        onDetails={openScenarioDetails}
                        onCreate={openScenarioCreate}
                        readOnly={!canManageTimetable}
                    />
                </div>
            {/if}
        </aside>
    {/if}

    <section class="map-layer" aria-label={$t('map.aria')}>
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
        left: clamp(20px, 4vw, 56px);
        bottom: 24px;
        z-index: 15;
    }

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

    .right-menu-dock {
        position: absolute;
        right: 24px;
        top: 220px;
        z-index: 35;
        display: flex;
        align-items: center;
        gap: 16px;
        pointer-events: none;
    }

    .side-buttons-column {
        display: flex;
        flex-direction: column;
        gap: 12px;
        pointer-events: auto;
    }

    .circle-menu-btn {
        width: 38px;
        height: 38px;
        border-radius: 50%;
        border: 0;
        background: rgba(255, 255, 255, 0.08);
        color: #f5f7f8;
        backdrop-filter: blur(12px);
        -webkit-backdrop-filter: blur(12px);
        display: flex;
        align-items: center;
        justify-content: center;
        cursor: pointer;
        padding: 0;
        box-shadow: 0 10px 24px rgba(0, 0, 0, 0.4);
        transition: opacity 150ms ease, background-color 150ms ease, color 150ms ease;
        text-decoration: none; 
    }

    .circle-menu-btn .material-symbols-outlined {
        font-size: 18px;
        font-weight: 200;
        line-height: 1;
        user-select: none;
    }

    .circle-menu-btn:hover:not(.disabled) {
        background: rgba(255, 255, 255, 0.14);
        opacity: 0.85;
    }

    .circle-menu-btn:active:not(.disabled) {
        opacity: 0.65;
    }

    .circle-menu-btn.active {
        background: #f5f7f8;
        color: #141414;
    }

    .circle-menu-btn.disabled {
        opacity: 0.35;
        cursor: not-allowed;
    }

    /* Wersja jasna (light mode) */
    :global(html.light-mode) .circle-menu-btn {
        background: rgba(0, 0, 0, 0.05);
        color: #1f2933;
        box-shadow: 0 10px 24px rgba(0, 0, 0, 0.08);
    }

    :global(html.light-mode) .circle-menu-btn:hover:not(.disabled) {
        background: rgba(0, 0, 0, 0.1);
        opacity: 0.85;
    }

    :global(html.light-mode) .circle-menu-btn.active {
        background: #111827;
        color: #ffffff;
    }

    .circle-menu-btn:focus-visible {
        outline: 2px solid rgba(255, 255, 255, 0.65);
        outline-offset: 2px;
    }

    :global(html.light-mode) .circle-menu-btn:focus-visible {
        outline-color: rgba(17, 24, 39, 0.65);
    }

    .flyout-panel {
        position: absolute;
        right: 60px;
        top: 0;
        width: 340px;
        max-height: calc(100vh - 280px);
        display: flex;
        flex-direction: column;
        pointer-events: auto;
        z-index: 40;
    }

    .panel-close-x {
        position: absolute;
        top: 10px;
        right: 10px;
        z-index: 50;
        width: 24px;
        height: 24px;
        border: 0;
        border-radius: 50%;
        background: transparent;
        color: #97a5ad;
        cursor: pointer;
        display: flex;
        align-items: center;
        justify-content: center;
        padding: 0;
        transition: color 150ms ease;
    }

    .panel-close-x:hover {
        color: #ffffff;
    }

    :global(html.light-mode) .panel-close-x:hover {
        color: #111827;
    }

    .panel-close-x:focus-visible {
        outline: 2px solid rgba(255, 255, 255, 0.65);
        outline-offset: 2px;
    }

    .material-symbols-outlined {
        font-family: 'Material Symbols Outlined' !important;
        font-weight: normal;
        font-style: normal;
        font-size: 18px;
        line-height: 1;
        display: inline-block;
        white-space: nowrap;
        direction: ltr;
        -webkit-font-smoothing: antialiased;
        user-select: none;
    }

    @media (max-width: 900px) {
        .right-menu-dock {
            top: auto;
            bottom: 24px;
            right: 24px;
        }

        .flyout-panel {
            right: 0;
            bottom: 60px;
            top: auto;
            width: min(92vw, 340px);
        }
    }
</style>