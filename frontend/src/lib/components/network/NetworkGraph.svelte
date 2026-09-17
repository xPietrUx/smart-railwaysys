<script lang="ts">
    import { createEventDispatcher } from 'svelte';
    import {
        eventLabel,
        formatEventMessage,
        trainEndpoints,
        trainStatusLabel,
        trainTargetId
    } from '$lib/services/labels';
    import { t } from '$lib/i18n';
    import type { RailEventNode } from '$lib/types/event';
    import type { DirectionalState, NetworkGraph, StationNode } from '$lib/types/network';
    import type { HighlightFilter, Selected } from '$lib/types/selection';
    import type { TrainNode } from '$lib/types/train';

    type SegmentItem = NetworkGraph['segments'][number];

    export let graph: NetworkGraph;
    export let trains: TrainNode[] = [];
    export let events: RailEventNode[] = [];
    export let selected: Selected | null = null;
    export let highlight: HighlightFilter | null = null;
    export let isFullscreen = false;
    /** Tryb wskazywania celu incydentu na mapie (patrz IncidentFeed) — gdy ustawiony,
     *  kliknięcia w pasujący typ elementu wołają onPick zamiast normalnego zaznaczania. */
    export let pickMode: 'segment' | 'station' | 'train' | null = null;
    export let onPick: (id: string) => void = () => {};
    export let onCancelPick: () => void = () => {};

    const dispatch = createEventDispatcher<{ toggleFullscreen: void }>();

    let containerWidth = 1000;
    let containerHeight = 740;

    const padding = 56;
    $: graphWidth = Math.max(containerWidth, 600);
    $: graphHeight = Math.max(containerHeight, 400);
    $: plotWidth = graphWidth - padding * 2;
    $: plotHeight = graphHeight - padding * 2;

    const MAX_ZOOM = 8;
    const MIN_ZOOM = 0.5;
    $: ASPECT = graphHeight / graphWidth;
    const PAN_MARGIN_RATIO = 0.35;

    let view = { x: 0, y: 0, w: 1000, h: 740 };
    let svgEl: SVGSVGElement;
    let pointerActive = false;
    let wasDragged = false;
    let activePointerId: number | null = null;
    let lastPointer = { x: 0, y: 0 };
    let downPointer = { x: 0, y: 0 };

    $: zoom = graphWidth / view.w;
    $: markerScale = 1 / Math.sqrt(zoom);

    function clampView(v: { x: number; y: number; w: number; h: number }) {
        const w = Math.min(Math.max(v.w, graphWidth / MAX_ZOOM), graphWidth / MIN_ZOOM);
        const h = w * ASPECT;
        const marginX = w * PAN_MARGIN_RATIO;
        const marginY = h * PAN_MARGIN_RATIO;
        return {
            w,
            h,
            x: Math.min(Math.max(v.x, -marginX), graphWidth - w + marginX),
            y: Math.min(Math.max(v.y, -marginY), graphHeight - h + marginY)
        };
    }

    const FOCUS_ZOOM = 2.4;
    let focusRaf: number | null = null;

    function cancelFocusAnimation() {
        if (focusRaf !== null) {
            cancelAnimationFrame(focusRaf);
            focusRaf = null;
        }
    }

    function animateViewTo(target: { x: number; y: number; w: number; h: number }, duration = 500) {
        cancelFocusAnimation();
        const from = { ...view };
        const t0 = performance.now();
        const ease = (t: number) => 1 - Math.pow(1 - t, 3);
        const step = (now: number) => {
            const progress = Math.min(1, (now - t0) / duration);
            const k = ease(progress);
            view = {
                x: from.x + (target.x - from.x) * k,
                y: from.y + (target.y - from.y) * k,
                w: from.w + (target.w - from.w) * k,
                h: from.h + (target.h - from.h) * k
            };
            focusRaf = progress < 1 ? requestAnimationFrame(step) : null;
        };
        focusRaf = requestAnimationFrame(step);
    }

    export function focusOn(target: Selected) {
        let point: { x: number; y: number } | null = null;
        if (target.kind === 'station') {
            point = positionById.get(target.id) ?? null;
        } else if (target.kind === 'segment') {
            const segment = segmentById.get(target.id);
            const source = segment ? positionById.get(segment.source) : null;
            const targetPos = segment ? positionById.get(segment.target) : null;
            if (source && targetPos) {
                point = { x: (source.x + targetPos.x) / 2, y: (source.y + targetPos.y) / 2 };
            }
        } else {
            const train = trains.find((item) => item.id === target.id);
            point = train ? getTrainPosition(train, positionById) : null;
        }
        if (!point) return;
        const targetZoom = Math.min(Math.max(zoom, FOCUS_ZOOM), MAX_ZOOM);
        const w = graphWidth / targetZoom;
        const h = w * ASPECT;
        animateViewTo(clampView({ w, h, x: point.x - w / 2, y: point.y - h / 2 }));
    }

    function applyZoom(cx: number, cy: number, factor: number) {
        cancelFocusAnimation();
        const newW = Math.min(Math.max(view.w / factor, graphWidth / MAX_ZOOM), graphWidth / MIN_ZOOM);
        const realFactor = view.w / newW;
        view = clampView({
            w: newW,
            h: newW * ASPECT,
            x: cx - (cx - view.x) / realFactor,
            y: cy - (cy - view.y) / realFactor
        });
    }

    function svgPointFromClient(clientX: number, clientY: number) {
        const ctm = svgEl?.getScreenCTM();
        if (!ctm) return { x: view.x + view.w / 2, y: view.y + view.h / 2 };
        const point = new DOMPoint(clientX, clientY).matrixTransform(ctm.inverse());
        return { x: point.x, y: point.y };
    }

    function handleWheel(event: WheelEvent) {
        event.preventDefault();
        const point = svgPointFromClient(event.clientX, event.clientY);
        applyZoom(point.x, point.y, event.deltaY < 0 ? 1.25 : 0.8);
    }

    function handleDblClick(event: MouseEvent) {
        const point = svgPointFromClient(event.clientX, event.clientY);
        applyZoom(point.x, point.y, 1.6);
    }

    function handlePointerDown(event: PointerEvent) {
        if (event.button !== 0) return;
        cancelFocusAnimation();
        pointerActive = true;
        wasDragged = false;
        activePointerId = event.pointerId;
        downPointer = { x: event.clientX, y: event.clientY };
        lastPointer = { x: event.clientX, y: event.clientY };
    }

    function handlePointerMove(event: PointerEvent) {
        if (!pointerActive || event.pointerId !== activePointerId) return;
        if (!wasDragged) {
            const moved = Math.hypot(event.clientX - downPointer.x, event.clientY - downPointer.y);
            if (moved < 4) return;
            wasDragged = true;
            svgEl.setPointerCapture(event.pointerId);
        }
        const from = svgPointFromClient(lastPointer.x, lastPointer.y);
        const to = svgPointFromClient(event.clientX, event.clientY);
        view = clampView({ ...view, x: view.x - (to.x - from.x), y: view.y - (to.y - from.y) });
        lastPointer = { x: event.clientX, y: event.clientY };
    }

    function handlePointerUp(event: PointerEvent) {
        if (!pointerActive || event.pointerId !== activePointerId) return;
        pointerActive = false;
        activePointerId = null;
        if (svgEl.hasPointerCapture(event.pointerId)) {
            svgEl.releasePointerCapture(event.pointerId);
        }
        setTimeout(() => {
            wasDragged = false;
        }, 0);
    }

    function handleBackgroundClick(event: MouseEvent) {
        if (wasDragged) return;
        if (event.target === svgEl) {
            if (pickMode !== null) {
                onCancelPick();
                return;
            }
            selected = null;
            highlight = null;
        }
    }

    function handleSvgKeydown(event: KeyboardEvent) {
        if (event.key === 'Escape') {
            if (isFullscreen) {
                dispatch('toggleFullscreen');
                return;
            }
            if (pickMode !== null) {
                onCancelPick();
                return;
            }
            selected = null;
            highlight = null;
        }
    }

    function zoomInStep() {
        applyZoom(view.x + view.w / 2, view.y + view.h / 2, 1.4);
    }

    function zoomOutStep() {
        applyZoom(view.x + view.w / 2, view.y + view.h / 2, 1 / 1.4);
    }

    function resetView() {
        cancelFocusAnimation();
        view = { x: 0, y: 0, w: graphWidth, h: graphHeight };
    }

    function normalize(value: number, min: number, max: number) {
        if (max === min) return 0.5;
        return (value - min) / (max - min);
    }

    function stationBounds(items: StationNode[]) {
        return {
            minLat: Math.min(...items.map((station) => station.lat)),
            maxLat: Math.max(...items.map((station) => station.lat)),
            minLon: Math.min(...items.map((station) => station.lon)),
            maxLon: Math.max(...items.map((station) => station.lon))
        };
    }

    function project(station: StationNode, bounds: ReturnType<typeof stationBounds>) {
        return {
            x: padding + normalize(station.lon, bounds.minLon, bounds.maxLon) * plotWidth,
            y: padding + (1 - normalize(station.lat, bounds.minLat, bounds.maxLat)) * plotHeight
        };
    }

    function stationRadius(station: StationNode) {
        return 9 + Math.min(9, station.dailyTrains / 55);
    }

    function stationShape(type: string): 'hub' | 'through' | 'terminus' {
        if (type === 'węzeł') return 'hub';
        if (type === 'końcowa') return 'terminus';
        return 'through';
    }

    function stationName(id: string | null | undefined) {
        if (!id) return '—';
        return stationById.get(id)?.name ?? id;
    }

    function relationLabel(train: TrainNode) {
        const { fromId, toId } = trainEndpoints(train);
        return `${stationName(fromId)} → ${stationName(toId)}`;
    }

    function handleKeydown(event: KeyboardEvent, action: () => void) {
        if (event.key === 'Enter' || event.key === ' ') {
            event.preventDefault();
            action();
        }
    }

    function getSegmentStatus(segment: SegmentItem, activeEvents: RailEventNode[]): 'blocked' | 'restricted' | 'ok' {
        const hasBlockedEvent = activeEvents.some(
            (e) =>
                e.status === 'active' &&
                e.segmentId === segment.segmentId &&
                (e.severity === 'major' || e.type === 'line_failure')
        );
        if (hasBlockedEvent) return 'blocked';

        const hasRestrictedEvent = activeEvents.some(
            (e) => e.status === 'active' && e.segmentId === segment.segmentId
        );
        if (hasRestrictedEvent) return 'restricted';

        if (segment.forward?.status === 'blocked' || segment.backward?.status === 'blocked') {
            return 'blocked';
        }
        if (segment.forward?.status === 'restricted' || segment.backward?.status === 'restricted') {
            return 'restricted';
        }
        return 'ok';
    }

    function segmentColor(status: 'blocked' | 'restricted' | 'ok'): string {
        if (status === 'blocked') return 'var(--color-blocked, #de8489)';
        if (status === 'restricted') return 'var(--color-restricted, #f0c29a)';
        return 'var(--track-base, #38404a)';
    }

    function trainRadius(train: TrainNode) {
        if (train.type === 'IC') return 10.5;
        if (train.type === 'FREIGHT') return 8;
        return 9.2;
    }

    function trainColor(train: TrainNode) {
        if (train.status === 'derailed') return 'var(--color-blocked, #de8489)';
        if (train.status === 'waiting') return 'var(--color-restricted, #f0c29a)';
        if (train.status === 'dwelling') return 'var(--color-dwelling, #87979f)';
        return 'var(--train-base, #f5f7f8)';
    }

    function getTrainPosition(
        train: TrainNode,
        positionById: Map<string, { x: number; y: number }>
    ): { x: number; y: number } | null {
        const current = positionById.get(train.currentStationId);
        if (!current) return null;
        if ((train.status === 'derailed' || train.status === 'waiting') && train.nextStationId && train.currentSegmentId) {
            const next = positionById.get(train.nextStationId);
            if (next) {
                return {
                    x: current.x + (next.x - current.x) * train.progress,
                    y: current.y + (next.y - current.y) * train.progress
                };
            }
        }
        if (train.status !== 'running' || !train.nextStationId) return current;
        const next = positionById.get(train.nextStationId);
        if (!next) return current;
        return {
            x: current.x + (next.x - current.x) * train.progress,
            y: current.y + (next.y - current.y) * train.progress
        };
    }

    $: stations = graph.stations;
    $: segments = graph.segments;
    $: bounds = stations.length ? stationBounds(stations) : null;
    $: positionById = new Map(
        stations.map((station) => [station.id, bounds ? project(station, bounds) : { x: 0, y: 0 }])
    );
    $: stationById = new Map(stations.map((station) => [station.id, station]));
    $: segmentById = new Map(segments.map((segment) => [segment.segmentId, segment]));

    $: stationsWithSignalFailure = new Set(
        events
            .filter(
                (event) => event.status === 'active' && event.type === 'signal_failure' && event.stationId
            )
            .map((event) => event.stationId as string)
    );

    // Podczas wskazywania celu incydentu stacje/pociągi mogą wizualnie leżeć nad
    // odcinkami (i pociągi nad stacjami) — wyłączamy im pointer-events, żeby klik
    // "przeszedł" do właściwej, klikalnej warstwy pod spodem.
    $: stationsClickable = pickMode !== 'segment';
    $: trainsClickable = pickMode === null || pickMode === 'train';
    $: badgesClickable = pickMode === null;

    $: {
        if (selected && stations.length > 0) {
            const sel = selected;
            const valid =
                sel.kind === 'station'
                    ? stationById.has(sel.id)
                    : sel.kind === 'segment'
                        ? segmentById.has(sel.id)
                        : trains.length === 0 || trains.some((train) => train.id === sel.id);
            if (!valid) selected = null;
        }
    }

    $: selectedKind = selected?.kind ?? null;
    $: selectedStation = selected?.kind === 'station' ? (stationById.get(selected.id) ?? null) : null;
    $: selectedSegmentId = selected?.kind === 'segment' ? selected.id : null;
    let selectedTrain: TrainNode | null;
    $: {
        if (selected?.kind === 'train') {
            const trainId = selected.id;
            selectedTrain = trains.find((train) => train.id === trainId) ?? null;
        } else {
            selectedTrain = null;
        }
    }

    $: selectedStationIds = new Set<string>(
        selectedStation
            ? segments
                    .filter(
                        (segment) =>
                            segment.source === selectedStation?.id || segment.target === selectedStation?.id
                    )
                    .flatMap((segment) => [segment.source, segment.target])
                    .concat(selectedStation.id)
            : []
    );
    $: selectedSegmentNodeIds = (() => {
        const segment = selectedSegmentId ? segmentById.get(selectedSegmentId) : null;
        return new Set<string>(segment ? [segment.source, segment.target] : []);
    })();
    $: selectedTrainRouteSegments = new Set<string>(selectedTrain?.routeSegmentIds ?? []);
    $: selectedTrainRouteStations = new Set<string>(selectedTrain?.routeStationIds ?? []);
    $: selectedTrainTargetId = selectedTrain ? trainTargetId(selectedTrain) : null;

    type IncidentBadge = { event: RailEventNode; x: number; y: number; atStation: boolean };
    $: incidentBadges = events
        .filter((event) => event.status === 'active')
        .map((event): IncidentBadge | null => {
            if (event.type === 'signal_failure' && event.stationId) {
                const point = positionById.get(event.stationId);
                return point ? { event, x: point.x, y: point.y, atStation: true } : null;
            }
            if (event.segmentId) {
                const segment = segmentById.get(event.segmentId);
                if (!segment) return null;
                const source = positionById.get(segment.source);
                const target = positionById.get(segment.target);
                if (!source || !target) return null;
                return {
                    event,
                    x: (source.x + target.x) / 2,
                    y: (source.y + target.y) / 2,
                    atStation: false
                };
            }
            return null;
        })
        .filter((badge): badge is IncidentBadge => badge !== null);

    const MATERIAL_EVENT_ICONS: Record<string, string> = {
        signal_failure: 'electric_bolt',
        line_failure: 'warning',
        speed_restriction: 'slow_motion_video',
        default: 'error'
    };

    function pickStation(id: string) {
        if (wasDragged) return;
        if (pickMode !== null) {
            if (pickMode === 'station' && !stationsWithSignalFailure.has(id)) onPick(id);
            return;
        }
        selected = { kind: 'station', id };
    }

    function pickSegment(id: string) {
        if (wasDragged) return;
        if (pickMode !== null) {
            const segment = segmentById.get(id);
            if (pickMode === 'segment' && segment && getSegmentStatus(segment, events) === 'ok') {
                onPick(id);
            }
            return;
        }
        selected = { kind: 'segment', id };
    }

    function pickTrain(id: string) {
        if (wasDragged) return;
        if (pickMode !== null) {
            const train = trains.find((item) => item.id === id);
            if (pickMode === 'train' && train?.status === 'running') onPick(id);
            return;
        }
        selected = { kind: 'train', id };
    }

    function pickIncident(badge: IncidentBadge) {
        if (wasDragged) return;
        if (pickMode !== null) return;
        const { event } = badge;
        if (event.stationId) {
            selected = { kind: 'station', id: event.stationId };
        } else if (event.segmentId) {
            selected = { kind: 'segment', id: event.segmentId };
        }
    }
</script>

<svelte:head>
    <link
        rel="stylesheet"
        href="https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined:opsz,wght,FILL,GRAD@20..48,100..700,0..1,-50..200"
    />
</svelte:head>

<div
    class="map-root"
    class:fullscreen={isFullscreen}
    bind:clientWidth={containerWidth}
    bind:clientHeight={containerHeight}
>
    {#if stations.length > 0 && bounds}
        <!-- svelte-ignore a11y_no_noninteractive_tabindex a11y_no_noninteractive_element_interactions -->
        <svg
            bind:this={svgEl}
            viewBox={`${view.x} ${view.y} ${view.w} ${view.h}`}
            class="graph"
            class:panning={pointerActive && wasDragged}
            class:names-hidden={zoom < 1.35}
            class:pick-mode={pickMode !== null}
            role="application"
            tabindex="-1"
            aria-label={$t('map.aria')}
            on:wheel|nonpassive={handleWheel}
            on:dblclick={handleDblClick}
            on:pointerdown={handlePointerDown}
            on:pointermove={handlePointerMove}
            on:pointerup={handlePointerUp}
            on:pointercancel={handlePointerUp}
            on:click={handleBackgroundClick}
            on:keydown={handleSvgKeydown}
        >
            <defs>
                <filter id="glow" x="-40%" y="-40%" width="180%" height="180%">
                    <feGaussianBlur stdDeviation="3" result="blur" />
                    <feMerge>
                        <feMergeNode in="blur" />
                        <feMergeNode in="SourceGraphic" />
                    </feMerge>
                </filter>
            </defs>

            {#each segments as segment (segment.segmentId)}
                {@const source = positionById.get(segment.source)}
                {@const target = positionById.get(segment.target)}
                {@const isSelected = selectedSegmentId === segment.segmentId}
                {@const onTrainRoute =
                    selectedKind === 'train' && selectedTrainRouteSegments.has(segment.segmentId)}
                {@const status = getSegmentStatus(segment, events)}
                {@const hasIncident = status !== 'ok'}
                {@const dimmed =
                    pickMode !== null
                        ? pickMode !== 'segment' || status !== 'ok'
                        : (selectedKind === 'station' &&
                              !selectedStationIds.has(segment.source) &&
                              !selectedStationIds.has(segment.target)) ||
                          (selectedKind === 'train' && !onTrainRoute) ||
                          (highlight?.kind === 'incidents' && !hasIncident)}
                {#if source && target}
                    <line
                        class="track"
                        x1={source.x}
                        y1={source.y}
                        x2={target.x}
                        y2={target.y}
                        stroke={isSelected ? 'var(--track-selected, #ffffff)' : segmentColor(status)}
                        stroke-width={isSelected ? 6.5 : onTrainRoute ? 5.5 : 4.8}
                        stroke-linecap="round"
                        vector-effect="non-scaling-stroke"
                        opacity={dimmed ? 0.2 : 0.95}
                    />
                    <!-- svelte-ignore a11y_click_events_have_key_events a11y_no_static_element_interactions -->
                    <line
                        class="hit-line"
                        class:dimmed
                        x1={source.x}
                        y1={source.y}
                        x2={target.x}
                        y2={target.y}
                        stroke="transparent"
                        stroke-width="16"
                        on:click={() => pickSegment(segment.segmentId)}
                    />
                {/if}
            {/each}

            {#each stations as station (station.id)}
                {@const point = positionById.get(station.id)}
                {@const isStationSelected = selectedStation?.id === station.id}
                {@const isTrainTarget = selectedTrainTargetId === station.id}
                {@const shape = stationShape(station.type)}
                {@const hasSignalFailure = stationsWithSignalFailure.has(station.id)}
                {@const dimmed =
                    pickMode !== null
                        ? pickMode !== 'station' || hasSignalFailure
                        : (selectedKind === 'segment' && !selectedSegmentNodeIds.has(station.id)) ||
                          (selectedKind === 'train' &&
                              !selectedTrainRouteStations.has(station.id) &&
                              !isTrainTarget) ||
                          (highlight?.kind === 'incidents' && !hasSignalFailure)}
                {#if point}
                    <g
                        class="station focus-target"
                        transform={`translate(${point.x}, ${point.y})`}
                        class:selected={isStationSelected}
                        class:dimmed
                        class:route-target={isTrainTarget}
                        style="pointer-events: {stationsClickable ? 'auto' : 'none'}"
                        on:click={() => pickStation(station.id)}
                        role="button"
                        tabindex="0"
                        aria-label={$t('map.stationAria', { name: station.name })}
                        on:keydown={(event) => handleKeydown(event, () => pickStation(station.id))}
                    >
                        <g transform={`scale(${markerScale})`}>
                            {#if hasSignalFailure}
                                <circle
                                    r={stationRadius(station) + 7}
                                    stroke="var(--color-restricted, #f0c29a)"
                                    stroke-width="2.5"
                                    fill="none"
                                    class="signal-ring"
                                />
                            {/if}
                            {#if isTrainTarget}
                                <circle
                                    r={stationRadius(station) + 9}
                                    stroke="var(--target-ring, #97a5ad)"
                                    stroke-width="2"
                                    stroke-dasharray="4,4"
                                    fill="none"
                                    class="target-ring"
                                />
                            {/if}
                            {#if shape === 'hub'}
                                <rect
                                    class="marker"
                                    x={-stationRadius(station) * 0.8}
                                    y={-stationRadius(station) * 0.8}
                                    width={stationRadius(station) * 1.6}
                                    height={stationRadius(station) * 1.6}
                                    rx="3"
                                    transform="rotate(45)"
                                    fill="var(--hub-fill, #f5f7f8)"
                                    filter={isStationSelected ? 'url(#glow)' : undefined}
                                />
                            {:else if shape === 'terminus'}
                                <circle
                                    class="marker"
                                    r={stationRadius(station)}
                                    fill="var(--color-restricted, #f0c29a)"
                                    filter={isStationSelected ? 'url(#glow)' : undefined}
                                />
                                <circle r={stationRadius(station) * 0.4} fill="var(--map-bg, #141414)" />
                            {:else}
                                <circle
                                    class="marker"
                                    r={stationRadius(station)}
                                    fill="var(--color-dwelling, #87979f)"
                                    filter={isStationSelected ? 'url(#glow)' : undefined}
                                />
                            {/if}
                            {#if isStationSelected}
                                <circle
                                    r={stationRadius(station) + 5}
                                    stroke="var(--selection-ring-stroke, #f5f7f8)"
                                    stroke-width="1.5"
                                    fill="none"
                                    class="selection-ring"
                                />
                            {/if}
                            <circle r={stationRadius(station) + 5} fill="transparent" />
                            <text class="station-code" y="-18">{station.code}</text>
                            <text class="station-name" y={stationRadius(station) + 18}>{station.name}</text>
                        </g>
                    </g>
                {/if}
            {/each}

            {#each trains as train (train.id)}
                {@const pos = getTrainPosition(train, positionById)}
                {@const isTrainSelected = selected?.kind === 'train' && selected.id === train.id}
                {@const isHighlighted =
                    highlight !== null &&
                    (highlight.kind === 'train-status'
                        ? train.status === highlight.status
                        : train.delayedByEventId !== null || train.status === 'derailed')}
                {@const dimmed =
                    pickMode !== null
                        ? pickMode !== 'train' || train.status !== 'running'
                        : (selectedKind === 'train' && !isTrainSelected) ||
                          (highlight !== null && !isHighlighted)}
                {#if pos}
                    <g
                        transform={`translate(${pos.x}, ${pos.y})`}
                        class="train-marker focus-target"
                        class:running={train.status === 'running'}
                        class:derailed={train.status === 'derailed'}
                        class:selected={isTrainSelected}
                        class:highlighted={isHighlighted}
                        class:dimmed
                        style="pointer-events: {trainsClickable ? 'auto' : 'none'}"
                        on:click={() => pickTrain(train.id)}
                        role="button"
                        tabindex="0"
                        aria-label={$t('map.trainAria', {
                            name: train.name,
                            status: trainStatusLabel(train.status, $t),
                            relation: relationLabel(train)
                        })}
                        on:keydown={(event) => handleKeydown(event, () => pickTrain(train.id))}
                    >
                        <g transform={`scale(${markerScale})`}>
                            {#if isHighlighted}
                                <circle r={trainRadius(train) + 8} class="highlight-ring" />
                            {/if}
                            {#if isTrainSelected}
                                <circle r={trainRadius(train) + 6} class="selected-ring" />
                            {/if}
                            {#if train.status === 'running'}
                                <circle
                                    r={trainRadius(train) + 5}
                                    fill={trainColor(train)}
                                    opacity="0.25"
                                    class="train-pulse"
                                />
                            {/if}
                            <circle
                                r={trainRadius(train)}
                                fill={trainColor(train)}
                                stroke="none"
                            />
                            {#if train.status === 'derailed'}
                                <text y="4" text-anchor="middle" class="train-warning">!</text>
                            {/if}
                            <text y={-trainRadius(train) - 7} class="train-label" text-anchor="middle"
                                >{train.name}</text
                            >
                        </g>
                    </g>
                {/if}
            {/each}

            {#each incidentBadges as badge (badge.event.id)}
                <g
                    class="incident-badge severity-{badge.event.severity} focus-target"
                    transform={`translate(${badge.x}, ${badge.y}) scale(${markerScale})`}
                    style="pointer-events: {badgesClickable ? 'auto' : 'none'}"
                    on:click={() => pickIncident(badge)}
                    role="button"
                    tabindex="0"
                    aria-label={`${eventLabel(badge.event.type, $t)}: ${formatEventMessage(
                        badge.event,
                        $t,
                        stationName
                    )}`}
                    on:keydown={(event) => handleKeydown(event, () => pickIncident(badge))}
                >
                    <g transform={badge.atStation ? 'translate(17, -17)' : ''}>
                        <circle r="13" class="badge-bg" />
                        <foreignObject x="-9" y="-9" width="18" height="18" style="overflow: visible;">
                            <div xmlns="http://www.w3.org/1999/xhtml" class="badge-icon-wrapper">
                                <span class="material-symbols-outlined badge-symbol" aria-hidden="true">
                                    {MATERIAL_EVENT_ICONS[badge.event.type] ?? MATERIAL_EVENT_ICONS.default}
                                </span>
                            </div>
                        </foreignObject>
                    </g>
                </g>
            {/each}
        </svg>

        <!-- Kontrolki widoku mapy (zoom / reset / pełny ekran) -->
        <div class="zoom-controls">
            <button
                type="button"
                class="ctrl-btn"
                on:click={() => dispatch('toggleFullscreen')}
                aria-label={isFullscreen ? 'Wyłącz pełny ekran' : 'Włącz pełny ekran'}
                title={isFullscreen ? 'Wyłącz pełny ekran' : 'Włącz pełny ekran'}
            >
                <span class="material-symbols-outlined ctrl-icon" aria-hidden="true">
                    {isFullscreen ? 'fullscreen_exit' : 'fullscreen'}
                </span>
            </button>

            <button
                type="button"
                class="ctrl-btn"
                on:click={resetView}
                aria-label={$t('map.reset')}
                title={$t('map.reset')}
            >
                <span class="material-symbols-outlined ctrl-icon" aria-hidden="true">restart_alt</span>
            </button>
            <button
                type="button"
                class="ctrl-btn"
                on:click={zoomInStep}
                aria-label={$t('map.zoomIn')}
                title={$t('map.zoomIn')}
            >
                <span class="material-symbols-outlined ctrl-icon" aria-hidden="true">add</span>
            </button>
            <button
                type="button"
                class="ctrl-btn"
                on:click={zoomOutStep}
                aria-label={$t('map.zoomOut')}
                title={$t('map.zoomOut')}
            >
                <span class="material-symbols-outlined ctrl-icon" aria-hidden="true">remove</span>
            </button>
        </div>

        <div class="map-legend-container">
            <div class="map-legend">
                <div class="legend-group">
                    <span><i class="legend-shape hub"></i>{$t('map.legend.hub')}</span>
                    <span><i class="legend-shape through"></i>{$t('map.legend.through')}</span>
                    <span><i class="legend-shape terminus"></i>{$t('map.legend.terminus')}</span>
                </div>
                <span class="legend-divider"></span>
                <div class="legend-group">
                    <span><i class="legend-line active"></i>{$t('map.legend.active')}</span>
                    <span><i class="legend-line restricted"></i>{$t('map.legend.restricted')}</span>
                    <span><i class="legend-line blocked"></i>{$t('map.legend.blocked')}</span>
                </div>
            </div>
            <div class="legend-hint">{$t('map.legend.hint')}</div>
        </div>
    {:else}
        <div class="empty-state" role="status">
            <span class="material-symbols-outlined empty-state-icon" aria-hidden="true">map</span>
            <p class="empty-state-text">{$t('map.empty')}</p>
        </div>
    {/if}
</div>

<style>
    .map-root {
        --map-bg: #141414;
        --track-base: #38404a;
        --track-selected: #ffffff;
        --station-code: #f5f7f8;
        --station-name: #97a5ad;
        --hub-fill: #f5f7f8;
        --selection-ring-stroke: #f5f7f8;
        --target-ring: #97a5ad;
        --train-base: #f5f7f8;
        --train-label: #f5f7f8;
        --train-warning-text: #141414;
        --color-blocked: #de8489;
        --color-restricted: #f0c29a;
        --color-dwelling: #87979f;
        --ctrl-bg: rgba(255, 255, 255, 0.08);
        --ctrl-bg-hover: rgba(255, 255, 255, 0.14);
        --ctrl-color: #f5f7f8;
        --ctrl-shadow: none;
        --legend-bg: rgba(20, 20, 20, 0.92);
        --legend-shadow: 0 16px 40px rgba(0, 0, 0, 0.45);
        --legend-text: #97a5ad;
        --legend-hint: #64748b;
        --legend-divider: rgba(255, 255, 255, 0.08);
        --focus-ring: rgba(255, 255, 255, 0.65);
        --badge-major-bg: rgba(222, 132, 137, 0.22);
        --badge-minor-bg: rgba(240, 194, 154, 0.22);

        position: relative;
        width: 100%;
        height: 100%;
        background: var(--map-bg);
        font-family: 'Inter Variable', Inter, sans-serif;
        transition: background-color 200ms ease;
    }

    :global(html.light-mode) .map-root,
    :global([data-theme='light']) .map-root,
    :global(.light) .map-root {
        --map-bg: #f4f5f3;
        --track-base: #b4bec9;
        --track-selected: #111827;
        --station-code: #111827;
        --station-name: #52606a;
        --hub-fill: #111827;
        --selection-ring-stroke: #111827;
        --target-ring: #6b7280;
        --train-base: #1f2933;
        --train-label: #111827;
        --train-warning-text: #ffffff;
        --color-blocked: #c95158;
        --color-restricted: #c97d39;
        --color-dwelling: #6b7280;
        --ctrl-bg: rgba(0, 0, 0, 0.05);
        --ctrl-bg-hover: rgba(0, 0, 0, 0.1);
        --ctrl-color: #111827;
        --ctrl-shadow: none;
        --legend-bg: rgba(255, 255, 255, 0.94);
        --legend-shadow: 0 16px 40px rgba(0, 0, 0, 0.08);
        --legend-text: #52606a;
        --legend-hint: #94a3b8;
        --legend-divider: rgba(0, 0, 0, 0.08);
        --focus-ring: rgba(17, 24, 39, 0.65);
        --badge-major-bg: rgba(201, 81, 88, 0.18);
        --badge-minor-bg: rgba(201, 125, 57, 0.18);
    }

    .map-root.fullscreen {
        position: fixed !important;
        inset: 0 !important;
        width: 100vw !important;
        height: 100vh !important;
        z-index: 1000 !important;
    }

    .graph *:focus {
        outline: none;
    }

    /* Wyraźny wskaźnik skupienia dla użytkowników klawiatury na mapie */
    .focus-target:focus-visible {
        outline: 2px solid var(--focus-ring);
        outline-offset: 4px;
    }

    .graph {
        position: absolute;
        inset: 0;
        width: 100%;
        height: 100%;
        display: block;
        cursor: grab;
        touch-action: none;
        outline: none;
        background: var(--map-bg);
        font-family: 'Inter Variable', Inter, sans-serif;
        transition: background-color 200ms ease;
    }

    .graph.panning,
    .graph.panning :global(*) {
        cursor: grabbing !important;
    }

    .graph.pick-mode {
        cursor: crosshair;
    }

    .graph :global(.hit-line),
    .graph :global(g.station),
    .graph :global(g.train-marker),
    .graph :global(g.incident-badge) {
        cursor: pointer;
    }

    /* Podczas wskazywania celu incydentu kursor ma wyglądać jak "oznacz tutaj
       awarię", a nie zwykły "kliknij, aby zobaczyć szczegóły" — bez tych reguł
       ogólna zasada cursor:pointer powyżej (ta sama swoistość, ale niżej w
       arkuszu) wygrywała nad .pick-mode i psuła wskaźnik nad elementami. */
    .graph.pick-mode :global(.hit-line),
    .graph.pick-mode :global(g.station),
    .graph.pick-mode :global(g.train-marker) {
        cursor: crosshair;
    }

    .graph.pick-mode :global(.hit-line.dimmed),
    .graph.pick-mode :global(g.station.dimmed),
    .graph.pick-mode :global(g.train-marker.dimmed) {
        cursor: not-allowed;
    }

    .graph.pick-mode :global(g.incident-badge) {
        cursor: default;
    }

    .material-symbols-outlined {
        font-family: 'Material Symbols Outlined' !important;
        font-weight: normal;
        font-style: normal;
        font-size: 18px;
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

    .graph :global(g.station .marker),
    .graph :global(g.station .selection-ring) {
        transition: transform 200ms ease, opacity 200ms ease, stroke 200ms ease;
    }

    .graph :global(g.station.selected .marker) {
        stroke: var(--selection-ring-stroke);
        stroke-width: 2px;
    }

    .selection-ring {
        animation: selection-pulse 1.8s ease-in-out infinite;
        stroke: var(--selection-ring-stroke) !important;
    }

    @keyframes selection-pulse {
        0%, 100% {
            opacity: 0.8;
            transform: scale(1);
        }
        50% {
            opacity: 0.3;
            transform: scale(1.12);
        }
    }

    .graph :global(g.station.dimmed) {
        opacity: 0.15;
    }

    .graph :global(g.train-marker.dimmed) {
        opacity: 0.25;
    }

    .graph.names-hidden
        :global(g.station:not(.selected):not(.route-target):not(:hover) .station-name) {
        display: none;
    }

    .signal-ring {
        animation: signal-pulse 1.6s ease-in-out infinite;
    }

    .target-ring {
        animation: signal-pulse 2s ease-in-out infinite;
    }

    @keyframes signal-pulse {
        0%,
        100% {
            opacity: 1;
        }
        50% {
            opacity: 0.35;
        }
    }

    .station-code {
        fill: var(--station-code);
        font-size: 0.85rem;
        font-weight: 500;
        text-anchor: middle;
        stroke: none;
        letter-spacing: -0.01em;
    }

    .station-name {
        fill: var(--station-name);
        font-size: 0.76rem;
        font-weight: 400;
        text-anchor: middle;
        stroke: none;
        letter-spacing: -0.01em;
    }

    .train-marker {
        transition: transform 0.9s linear;
    }

    .train-marker .selected-ring {
        fill: none;
        stroke: var(--selection-ring-stroke);
        stroke-width: 2.5;
        stroke-dasharray: 4, 4;
    }

    .train-marker .highlight-ring {
        fill: none;
        stroke: var(--color-restricted);
        stroke-width: 2.5;
        animation: highlight-pulse 1.4s ease-in-out infinite;
    }

    @keyframes highlight-pulse {
        0%,
        100% {
            opacity: 1;
        }
        50% {
            opacity: 0.35;
        }
    }

    .train-marker.running .train-pulse {
        transform-box: fill-box;
        transform-origin: center;
        animation: train-pulse 1.4s ease-in-out infinite;
    }

    .train-marker.derailed {
        animation: derailed-shake 0.4s ease-in-out infinite;
    }

    @keyframes train-pulse {
        0%,
        100% {
            transform: scale(1);
            opacity: 0.35;
        }
        50% {
            transform: scale(1.35);
            opacity: 0.1;
        }
    }

    @keyframes derailed-shake {
        0%,
        100% {
            transform: translate(0, 0);
        }
        25% {
            transform: translate(-1px, 0.5px);
        }
        75% {
            transform: translate(1px, -0.5px);
        }
    }

    .train-label {
        font-size: 0.65rem;
        font-weight: 400;
        fill: var(--train-label);
        stroke: none;
        letter-spacing: -0.01em;
    }

    .train-warning {
        font-size: 0.65rem;
        font-weight: 800;
        fill: var(--train-warning-text);
        stroke: none;
    }

    .incident-badge .badge-bg {
        stroke: none;
    }

    .incident-badge.severity-major .badge-bg {
        fill: var(--badge-major-bg);
    }

    .incident-badge.severity-minor .badge-bg {
        fill: var(--badge-minor-bg);
    }

    .incident-badge {
        animation: badge-pulse 1.8s ease-in-out infinite;
    }

    @keyframes badge-pulse {
        0%,
        100% {
            opacity: 1;
        }
        50% {
            opacity: 0.55;
        }
    }

    .badge-icon-wrapper {
        width: 18px;
        height: 18px;
        display: flex;
        align-items: center;
        justify-content: center;
    }

    .badge-symbol {
        font-size: 13px;
        color: var(--legend-text);
    }

    .severity-major .badge-symbol {
        color: var(--color-blocked);
    }

    .severity-minor .badge-symbol {
        color: var(--color-restricted);
    }

    .zoom-controls {
        position: absolute;
        right: 24px;
        bottom: 74px;
        display: flex;
        flex-direction: column;
        gap: 8px;
        z-index: 30;
    }

    .ctrl-btn {
        width: 38px;
        height: 38px;
        border-radius: 50%;
        border: 0;
        background: var(--ctrl-bg);
        color: var(--ctrl-color);
        backdrop-filter: blur(12px);
        -webkit-backdrop-filter: blur(12px);
        display: flex;
        align-items: center;
        justify-content: center;
        cursor: pointer;
        padding: 0;
        box-shadow: none !important;
        transition: background-color 150ms ease, color 150ms ease;
    }

    .ctrl-btn:focus {
        outline: none;
    }

    .ctrl-btn:focus-visible {
        outline: 2px solid var(--focus-ring);
        outline-offset: 2px;
    }

    .ctrl-btn:hover {
        background: var(--ctrl-bg-hover);
        transform: none !important;
    }

    .ctrl-btn:active {
        transform: none !important;
    }

    .ctrl-icon {
        font-size: 18px;
        font-weight: 200;
        line-height: 1;
        user-select: none;
    }

    .map-legend-container {
        position: absolute;
        left: 50%;
        transform: translateX(-50%);
        bottom: 20px;
        display: flex;
        flex-direction: column;
        align-items: center;
        gap: 6px;
        z-index: 10;
        max-width: min(92vw, 780px);
    }

    .map-legend {
        display: flex;
        align-items: center;
        gap: 14px;
        padding: 6px 16px;
        border-radius: 10px;
        background: var(--legend-bg);
        backdrop-filter: blur(16px);
        -webkit-backdrop-filter: blur(16px);
        box-shadow: var(--legend-shadow);
        color: var(--legend-text);
        font-size: 0.68rem;
        font-weight: 300;
        letter-spacing: 0.04em;
        text-transform: uppercase;
        transition: background-color 200ms ease, color 200ms ease;
    }

    .legend-group {
        display: flex;
        align-items: center;
        gap: 14px;
    }

    .map-legend span {
        display: inline-flex;
        align-items: center;
        gap: 6px;
    }

    .legend-hint {
        color: var(--legend-hint);
        font-size: 0.62rem;
        letter-spacing: 0.04em;
        text-transform: uppercase;
        text-align: center;
    }

    .legend-divider {
        width: 1px;
        height: 12px;
        background: var(--legend-divider);
    }

    .legend-shape {
        width: 7px;
        height: 7px;
        display: inline-block;
    }

    .legend-shape.hub {
        background: var(--hub-fill);
        transform: rotate(45deg);
        border-radius: 1px;
    }

    .legend-shape.through {
        background: var(--color-dwelling);
        border-radius: 999px;
    }

    .legend-shape.terminus {
        background: var(--color-restricted);
        border-radius: 999px;
    }

    .legend-line {
        width: 14px;
        height: 4px;
        display: inline-block;
        border-radius: 2px;
    }

    .legend-line.active {
        background: var(--track-base);
    }

    .legend-line.restricted {
        background: var(--color-restricted);
    }

    .legend-line.blocked {
        background: var(--color-blocked);
    }

    .empty-state {
        position: absolute;
        inset: 0;
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        gap: 8px;
        color: var(--legend-text);
        background: var(--map-bg);
        transition: background-color 200ms ease, color 200ms ease;
    }

    .empty-state-icon {
        font-size: 32px;
        opacity: 0.6;
    }

    .empty-state-text {
        margin: 0;
        font-size: 0.76rem;
        font-weight: 300;
        letter-spacing: 0.06em;
        text-transform: uppercase;
    }

    @media (max-width: 900px) {
        .map-legend-container {
            display: none;
        }
    }
</style>