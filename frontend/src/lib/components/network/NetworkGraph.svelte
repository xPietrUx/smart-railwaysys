<script lang="ts">
	import { onMount, onDestroy } from 'svelte';
	import type { NetworkGraph, StationNode, TrackSegment } from '$lib/types/network';
	import type { FastestRouteResponse } from '$lib/types/routing';
	import type { TrainState } from '$lib/types/simulation';
	import { updateSegmentStatus } from '$lib/services/network';
	import { fetchTrains, tickSimulation } from '$lib/services/simulation';
	import RouteControlPanel from './RouteControlPanel.svelte';
	import BreakdownControlPanel from './BreakdownControlPanel.svelte';
	import TrainControlPanel from './TrainControlPanel.svelte';

	export let graph: NetworkGraph;


	type Selected = { kind: 'station'; id: string } | { kind: 'segment'; id: string };


	const padding = 56;
	const graphWidth = 1000;
	const graphHeight = 620;
	const plotWidth = graphWidth - padding * 2;
	const plotHeight = graphHeight - padding * 2;

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
		return 10 + Math.min(10, station.dailyTrains / 55);
	}

	function edgeStrokeWidth(segment: TrackSegment) {
		return 2 + segment.railTracks * 0.9;
	}

	function formatLine(segment: TrackSegment) {
		return `Linia ${segment.line}`;
	}

	function formatStationType(type: string) {
		return type.charAt(0).toUpperCase() + type.slice(1);
	}

	function handleKeydown(event: KeyboardEvent, action: () => void) {
		if (event.key === 'Enter' || event.key === ' ') {
			event.preventDefault();
			action();
		}
	}

	$: stations = graph.stations;
	$: segments = graph.segments;
	$: bounds = stations.length ? stationBounds(stations) : null;
	$: positionById = new Map(
		stations.map((station) => [station.id, bounds ? project(station, bounds) : { x: 0, y: 0 }])
	);
	$: stationById = new Map(stations.map((station) => [station.id, station]));
	$: uniqueSegments = Array.from(new Map(segments.map((segment) => [segment.segmentId, segment])).values());
	$: degreeByStation = (() => {
		const map = new Map<string, number>();
		for (const segment of uniqueSegments) {
			map.set(segment.source, (map.get(segment.source) ?? 0) + 1);
			map.set(segment.target, (map.get(segment.target) ?? 0) + 1);
		}
		return map;
	})();
	$: busiestStation = stations.reduce((best, station) => {
		if (!best) return station;
		const currentDegree = degreeByStation.get(station.id) ?? 0;
		const bestDegree = degreeByStation.get(best.id) ?? 0;
		return currentDegree > bestDegree ? station : best;
	}, stations[0] ?? null);

	let selectedState: Selected | null = null;
	let selectedKind: Selected['kind'] | null = null;
	let selectedStation: StationNode | null = null;
	let selectedSegment: TrackSegment | null = null;
	let connectedSegments: TrackSegment[] = [];
	let selectedStationIds = new Set<string>();
	let selectedSegmentNodeIds = new Set<string>();
	let selectedSegmentEdgeIds = new Set<string>();
	let activeRoute: FastestRouteResponse | null = null;

	$: routeStationIds = new Set<string>(
		activeRoute?.found ? activeRoute.path.map((s) => s.id) : []
	);
	$: routeSegmentIds = new Set<string>(
		activeRoute?.found ? activeRoute.segments.map((s) => s.segmentId) : []
	);

	$: selectedKind = selectedState?.kind ?? null;
	$: if (stations.length > 0 && (!selectedState || selectedState.kind === 'station' && !stationById.has(selectedState.id))) {
		selectedState = { kind: 'station', id: busiestStation?.id ?? stations[0].id };
	}
	$: selectedStation =
		selectedState?.kind === 'station' ? stationById.get(selectedState.id) ?? null : null;
	$: {
		if (selectedState?.kind === 'segment') {
			const segmentId = selectedState.id;
			selectedSegment =
				uniqueSegments.find((segment) => segment.segmentId === segmentId) ?? null;
		} else {
			selectedSegment = null;
		}
	}
	$: connectedSegments = selectedStation
		? uniqueSegments.filter(
				(segment) => segment.source === selectedStation.id || segment.target === selectedStation.id
			)
		: [];
	$: selectedStationIds = new Set<string>(
		selectedStation
			? connectedSegments.flatMap((segment) => [segment.source, segment.target]).concat(selectedStation.id)
			: []
	);
	$: selectedSegmentNodeIds = new Set<string>(
		selectedSegment ? [selectedSegment.source, selectedSegment.target] : []
	);
	$: {
		const segment = selectedSegment;
		if (segment) {
			selectedSegmentEdgeIds = new Set(
				segments.filter((item) => item.segmentId === segment.segmentId).map((item) => item.id)
			);
		} else {
			selectedSegmentEdgeIds = new Set();
		}
	}

	function pickStation(id: string) {
		selectedState = { kind: 'station', id };
	}

	function pickSegment(id: string) {
		selectedState = { kind: 'segment', id };
	}

	let togglingStatus = false;
	async function toggleSegmentStatus(segment: TrackSegment) {
		if (togglingStatus) return;
		togglingStatus = true;
		try {
			const baseUrl = import.meta.env.VITE_API_URL ?? 'http://localhost:8000';
			const newStatus = segment.status === 'active' ? 'blocked' : 'active';
			await updateSegmentStatus(fetch, baseUrl, segment.segmentId, newStatus);
			graph.segments = graph.segments.map((s) =>
				s.segmentId === segment.segmentId ? { ...s, status: newStatus } : s
			);
			if (selectedSegment && selectedSegment.segmentId === segment.segmentId) {
				selectedSegment = { ...selectedSegment, status: newStatus };
			}
		} catch (err) {
			alert('Nie udało się zmienić statusu toru: ' + (err instanceof Error ? err.message : err));
		} finally {
			togglingStatus = false;
		}
	}

	let activeTrains: TrainState[] = [];
	let isSimRunning = true;
	let simInterval: ReturnType<typeof setInterval> | null = null;
	const baseUrl = import.meta.env.VITE_API_URL ?? 'http://localhost:8000';

	async function pollSimulationTick() {
		if (!isSimRunning) return;
		try {
			const res = await tickSimulation(fetch, baseUrl, 1.0, 60.0);
			activeTrains = res.trains;
		} catch {
			// cichy ign
		}
	}

	onMount(async () => {
		try {
			const res = await fetchTrains(fetch, baseUrl);
			activeTrains = res.trains;
		} catch {
			// cichy ign
		}
		simInterval = setInterval(pollSimulationTick, 1000);
	});

	onDestroy(() => {
		if (simInterval) clearInterval(simInterval);
	});

	function getTrainPosition(t: TrainState): { x: number; y: number } | null {
		const source = positionById.get(t.currentStationId);
		const target = positionById.get(t.nextStationId || t.currentStationId);
		if (!source) return null;
		if (!target) return { x: source.x, y: source.y };
		return {
			x: source.x + (target.x - source.x) * t.progress,
			y: source.y + (target.y - source.y) * t.progress
		};
	}
</script>

<svelte:head>
	<title>Smart Railway System — live Memgraph</title>
	<meta
		name="description"
		content="Wizualizacja stacji i połączeń kolejowych pobierana na żywo z Memgraph."
	/>
</svelte:head>

<main class="page">
	<section class="hero">
		<div>
			<p class="eyebrow">Smart Railway System</p>
			<h1>Graf Memgraph na żywo</h1>
			<p class="lede">
				Interaktywny widok sieci stacji i odcinków kolejowych pobierany bezpośrednio z
				Memgraph. Kliknij stację albo segment, żeby zobaczyć szczegóły.
			</p>
		</div>

		<div class="hero-cards">
			<div class="metric">
				<span>Stacje</span>
				<strong>{stations.length || '—'}</strong>
			</div>
			<div class="metric">
				<span>Unikalne segmenty</span>
				<strong>{uniqueSegments.length || '—'}</strong>
			</div>
			<div class="metric">
				<span>Relacje w bazie</span>
				<strong>{graph.relationshipCount || '—'}</strong>
			</div>
		</div>
	</section>

	<section class="controls-grid-section">
		<RouteControlPanel {stations} bind:activeRoute onRouteFound={(r) => (activeRoute = r)} />
		<BreakdownControlPanel
			{stations}
			segments={uniqueSegments}
			onSegmentUpdated={(id, status) => {
				graph.segments = graph.segments.map((s) => (s.segmentId === id ? { ...s, status } : s));
			}}
			onResetAll={() => {
				graph.segments = graph.segments.map((s) => ({ ...s, status: 'active' }));
			}}
		/>
		<TrainControlPanel
			{stations}
			trains={activeTrains}
			isRunning={isSimRunning}
			onTrainsUpdated={(t) => (activeTrains = t)}
			onSelectTrainRoute={(t) => {
				if (t && t.route) {
					activeRoute = t.route;
				} else {
					activeRoute = null;
				}
			}}
			onToggleRunning={() => (isSimRunning = !isSimRunning)}
		/>
	</section>

	<section class="content">
		<div class="panel graph-panel">
			<div class="panel-header">
				<div>
					<p class="panel-label">Wizualizacja sieci</p>
					<h2>Połączenia kolejowe</h2>
				</div>
				<div class="legend">
					<span><i class="legend-node hub"></i>węzeł</span>
					<span><i class="legend-node pass"></i>przelotowa</span>
					<span><i class="legend-node end"></i>końcowa</span>
				</div>
			</div>

			{#if stations.length > 0 && bounds}
				<svg viewBox={`0 0 ${graphWidth} ${graphHeight}`} class="graph" role="img" aria-label="Graf stacji kolejowych">
					<defs>
						<filter id="glow" x="-40%" y="-40%" width="180%" height="180%">
							<feGaussianBlur stdDeviation="3" result="blur" />
							<feMerge>
								<feMergeNode in="blur" />
								<feMergeNode in="SourceGraphic" />
							</feMerge>
						</filter>
					</defs>

					{#each uniqueSegments as segment}
						{@const source = positionById.get(segment.source)}
						{@const target = positionById.get(segment.target)}
						{@const isActive = segment.status === 'active'}
						{@const isBlocked = segment.status === 'blocked'}
						{@const isSelected = selectedSegmentEdgeIds.has(segment.id)}
						{@const isOnRoute = routeSegmentIds.has(segment.segmentId)}
						{@const midX = source && target ? (source.x + target.x) / 2 : 0}
						{@const midY = source && target ? (source.y + target.y) / 2 : 0}
						{#if source && target}
							<line
								x1={source.x}
								y1={source.y}
								x2={target.x}
								y2={target.y}
								stroke={isBlocked ? '#ef4444' : isOnRoute ? '#10b981' : isSelected ? '#f59e0b' : '#2563eb'}
								stroke-width={isOnRoute ? edgeStrokeWidth(segment) + 3.5 : isSelected ? edgeStrokeWidth(segment) + 1.5 : edgeStrokeWidth(segment)}
								stroke-dasharray={isBlocked ? '8,6' : undefined}
								stroke-linecap="round"
								filter={isOnRoute ? 'url(#glow)' : undefined}
								opacity={isOnRoute ? 1 : selectedKind === 'segment' && !isSelected ? 0.18 : 0.72}
								class:dimmed={!isOnRoute && selectedKind === 'station' && !selectedStationIds.has(segment.source) && !selectedStationIds.has(segment.target)}
								on:click={() => pickSegment(segment.segmentId)}
								role="button"
								tabindex="0"
								aria-label={`Segment ${segment.segmentId} ${stationById.get(segment.source)?.name} do ${stationById.get(segment.target)?.name}`}
								on:keydown={(event) => handleKeydown(event, () => pickSegment(segment.segmentId))}
							/>
							<circle
								cx={midX}
								cy={midY}
								r="14"
								fill="transparent"
								opacity="0"
								on:click={() => pickSegment(segment.segmentId)}
								role="button"
								tabindex="0"
								aria-label={`Segment ${segment.segmentId} ${stationById.get(segment.source)?.name} do ${stationById.get(segment.target)?.name}`}
								on:keydown={(event) => handleKeydown(event, () => pickSegment(segment.segmentId))}
							/>
						{/if}
					{/each}

					{#each stations as station}
						{@const point = positionById.get(station.id)}
						{@const selected = selectedStation?.id === station.id}
						{@const isRouteStation = routeStationIds.has(station.id)}
						{@const dimmed = selectedKind === 'segment' && !selectedSegmentNodeIds.has(station.id)}
						{#if point}
							<g
								transform={`translate(${point.x}, ${point.y})`}
								class:selected={selected}
								class:dimmed={dimmed}
								on:click={() => pickStation(station.id)}
								role="button"
								tabindex="0"
								aria-label={`Stacja ${station.name}`}
								on:keydown={(event) => handleKeydown(event, () => pickStation(station.id))}
							>
								{#if isRouteStation}
									<circle
										r={stationRadius(station) + 7}
										stroke="#10b981"
										stroke-width="3"
										fill="none"
										filter="url(#glow)"
									/>
								{/if}
								<circle
									r={stationRadius(station)}
									fill={station.type === 'węzeł' ? '#2563eb' : station.type === 'końcowa' ? '#f59e0b' : '#10b981'}
									filter={selected || isRouteStation ? 'url(#glow)' : undefined}
								/>
								<circle r={stationRadius(station) + 5} fill="transparent" />
								<text class="station-code" y="-18">{station.code}</text>
								<text class="station-name" y={stationRadius(station) + 18}>{station.name}</text>
							</g>
						{/if}
					{/each}

					<!-- Rysowanie żywych pociągów na mapie -->
					{#each activeTrains as train}
						{@const pos = getTrainPosition(train)}
						{#if pos}
							<g
								transform={`translate(${pos.x}, ${pos.y})`}
								class="train-marker-g"
								on:click={() => {
									if (train.route) activeRoute = train.route;
								}}
								role="button"
								tabindex="0"
							>
								<!-- Glow wokół pociągu -->
								<circle r="16" fill={train.status === 'rerouted' ? '#f59e0b' : '#3b82f6'} opacity="0.3" filter="url(#glow)">
									<animate attributeName="r" values="14;18;14" dur="1.5s" repeatCount="indefinite" />
								</circle>
								<!-- Główne koło pociągu -->
								<circle r="11" fill={train.status === 'rerouted' ? '#f59e0b' : '#2563eb'} stroke="#ffffff" stroke-width="2.5" />
								<!-- Etykieta z nazwą -->
								<text y="-18" class="train-label" text-anchor="middle" fill="#ffffff">
									{train.name}
								</text>
							</g>
						{/if}
					{/each}
				</svg>
			{:else}
				<div class="empty-state">Brak danych z Memgraph.</div>
			{/if}
		</div>

		<aside class="panel details">
			<div class="panel-header">
				<div>
					<p class="panel-label">Szczegóły</p>
					<h2>
						{#if selectedKind === 'station'}
							{selectedStation?.name}
						{:else}
							{selectedSegment?.segmentId}
						{/if}
					</h2>
				</div>
			</div>

			{#if selectedKind === 'station' && selectedStation}
				<div class="detail-grid">
					<div>
						<span>Code</span>
						<strong>{selectedStation.code}</strong>
					</div>
					<div>
						<span>Typ</span>
						<strong>{formatStationType(selectedStation.type)}</strong>
					</div>
					<div>
						<span>Perony</span>
						<strong>{selectedStation.platforms}</strong>
					</div>
					<div>
						<span>Tory</span>
						<strong>{selectedStation.tracks}</strong>
					</div>
					<div>
						<span>Pociągi/dzień</span>
						<strong>{selectedStation.dailyTrains}</strong>
					</div>
					<div>
						<span>Połączenia</span>
						<strong>{degreeByStation.get(selectedStation.id) ?? 0}</strong>
					</div>
				</div>

				<div class="section">
					<h3>Najbliższe połączenia</h3>
					<ul class="connections">
						{#each connectedSegments as segment}
							<li>
								<button type="button" on:click={() => pickSegment(segment.segmentId)}>
									<div>
										<strong>{segment.segmentId}</strong>
										<span>{formatLine(segment)} · {segment.distKm} km</span>
									</div>
									<small>{stationById.get(segment.source)?.name} → {stationById.get(segment.target)?.name}</small>
								</button>
							</li>
						{/each}
					</ul>
				</div>
			{:else if selectedKind === 'segment' && selectedSegment}
				<div class="detail-grid">
					<div>
						<span>Linia</span>
						<strong>{selectedSegment.line}</strong>
					</div>
					<div>
						<span>Długość</span>
						<strong>{selectedSegment.distKm} km</strong>
					</div>
					<div>
						<span>Czas przejazdu</span>
						<strong>{selectedSegment.travelMin} min</strong>
					</div>
					<div>
						<span>Vmax</span>
						<strong>{selectedSegment.vmax} km/h</strong>
					</div>
					<div>
						<span>Tory</span>
						<strong>{selectedSegment.railTracks}</strong>
					</div>
					<div>
						<span>Status</span>
						<strong>{selectedSegment.status}</strong>
					</div>
				</div>

				<div class="status-toggle-section">
					<button
						type="button"
						class="status-toggle-btn"
						class:btn-block={selectedSegment.status === 'active'}
						class:btn-unblock={selectedSegment.status === 'blocked'}
						on:click={() => selectedSegment && toggleSegmentStatus(selectedSegment)}
						disabled={togglingStatus}
					>
						{#if togglingStatus}
							Zmiana statusu...
						{:else if selectedSegment.status === 'active'}
							🚧 Zablokuj odcinek (Symuluj awarię)
						{:else}
							✅ Odblokuj odcinek (Wznowienie ruchu)
						{/if}
					</button>
				</div>

				<div class="section">
					<h3>Łączy</h3>
					<ul class="connections">
						<li>
							<button type="button" on:click={() => pickStation(selectedSegment?.source ?? '')}>
								<div>
									<strong>{stationById.get(selectedSegment?.source ?? '')?.name}</strong>
									<span>{stationById.get(selectedSegment?.source ?? '')?.code}</span>
								</div>
								<small>Stacja początkowa</small>
							</button>
						</li>
						<li>
							<button type="button" on:click={() => pickStation(selectedSegment?.target ?? '')}>
								<div>
									<strong>{stationById.get(selectedSegment?.target ?? '')?.name}</strong>
									<span>{stationById.get(selectedSegment?.target ?? '')?.code}</span>
								</div>
								<small>Stacja końcowa</small>
							</button>
						</li>
					</ul>
				</div>
			{/if}
		</aside>
	</section>
</main>

<style>
	:global(body) {
		margin: 0;
		font-family:
			Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
		background:
			radial-gradient(circle at top, rgba(37, 99, 235, 0.2), transparent 35%),
			linear-gradient(180deg, #0f172a 0%, #111827 100%);
		color: #e5eefb;
	}

	.page {
		min-height: 100vh;
		padding: 32px;
		box-sizing: border-box;
	}

	.hero {
		display: flex;
		justify-content: space-between;
		gap: 24px;
		align-items: end;
		margin-bottom: 24px;
	}

	.eyebrow,
	.panel-label {
		margin: 0 0 8px;
		text-transform: uppercase;
		letter-spacing: 0.14em;
		font-size: 0.75rem;
		color: #93c5fd;
	}

	h1,
	h2,
	h3,
	p {
		margin: 0;
	}

	h1 {
		font-size: clamp(2rem, 4vw, 3.5rem);
		line-height: 1;
		margin-bottom: 12px;
	}

	.lede {
		max-width: 64ch;
		color: #cbd5e1;
		font-size: 1.05rem;
		line-height: 1.6;
	}

	.hero-cards {
		display: grid;
		grid-template-columns: repeat(3, minmax(120px, 1fr));
		gap: 12px;
		min-width: 360px;
	}

	.metric,
	.panel {
		background: rgba(15, 23, 42, 0.72);
		border: 1px solid rgba(148, 163, 184, 0.18);
		box-shadow: 0 24px 60px rgba(15, 23, 42, 0.35);
		backdrop-filter: blur(10px);
		border-radius: 20px;
	}

	.metric {
		padding: 16px;
	}

	.metric span,
	.detail-grid span,
	.connections small {
		display: block;
		color: #94a3b8;
		font-size: 0.85rem;
	}

	.metric strong {
		display: block;
		font-size: 1.6rem;
		margin-top: 8px;
	}

	.content {
		display: grid;
		grid-template-columns: minmax(0, 1.65fr) minmax(300px, 0.9fr);
		gap: 18px;
		align-items: start;
	}

	.controls-grid-section {
		display: grid;
		grid-template-columns: repeat(auto-fit, minmax(420px, 1fr));
		gap: 18px;
		margin-bottom: 24px;
	}


	.panel {
		padding: 20px;
	}

	.panel-header {
		display: flex;
		justify-content: space-between;
		align-items: flex-start;
		gap: 16px;
		margin-bottom: 16px;
	}

	.legend {
		display: flex;
		gap: 14px;
		flex-wrap: wrap;
		color: #cbd5e1;
		font-size: 0.9rem;
	}

	.legend span {
		display: inline-flex;
		align-items: center;
		gap: 8px;
	}

	.legend-node {
		width: 11px;
		height: 11px;
		border-radius: 999px;
		display: inline-block;
	}

	.legend-node.hub {
		background: #2563eb;
	}

	.legend-node.pass {
		background: #10b981;
	}

	.legend-node.end {
		background: #f59e0b;
	}

	.graph {
		width: 100%;
		height: auto;
		display: block;
	}

	.graph :global(line),
	.graph :global(g) {
		cursor: pointer;
	}

	.graph :global(g.selected circle:first-child) {
		stroke: #f8fafc;
		stroke-width: 4px;
	}

	.graph :global(g.dimmed),
	.graph :global(line.dimmed) {
		opacity: 0.18;
	}

	.station-code {
		fill: #f8fafc;
		font-size: 0.8rem;
		font-weight: 700;
		text-anchor: middle;
		paint-order: stroke;
		stroke: rgba(15, 23, 42, 0.7);
		stroke-width: 3px;
	}

	.station-name {
		fill: #e2e8f0;
		font-size: 0.72rem;
		text-anchor: middle;
		paint-order: stroke;
		stroke: rgba(15, 23, 42, 0.75);
		stroke-width: 3px;
	}

	.details {
		position: sticky;
		top: 18px;
	}

	.detail-grid {
		display: grid;
		grid-template-columns: repeat(2, minmax(0, 1fr));
		gap: 12px;
	}

	.detail-grid > div {
		background: rgba(30, 41, 59, 0.72);
		border-radius: 14px;
		padding: 12px;
	}

	.detail-grid strong {
		display: block;
		margin-top: 6px;
		font-size: 1rem;
	}

	.section {
		margin-top: 18px;
	}

	.section h3 {
		margin-bottom: 12px;
		font-size: 1rem;
	}

	.connections {
		list-style: none;
		padding: 0;
		margin: 0;
		display: grid;
		gap: 10px;
	}

	.connections button {
		width: 100%;
		text-align: left;
		border: 1px solid rgba(148, 163, 184, 0.14);
		background: rgba(30, 41, 59, 0.72);
		color: inherit;
		padding: 12px;
		border-radius: 14px;
		display: flex;
		justify-content: space-between;
		align-items: center;
		gap: 12px;
	}

	.connections button:hover {
		border-color: rgba(59, 130, 246, 0.5);
		transform: translateY(-1px);
	}

	.connections strong {
		display: block;
	}

	.connections span {
		display: block;
		color: #cbd5e1;
		font-size: 0.85rem;
		margin-top: 2px;
	}

	.empty-state {
		padding: 24px;
		border-radius: 14px;
		background: rgba(30, 41, 59, 0.72);
		color: #cbd5e1;
	}

	.status-toggle-section {
		margin-top: 16px;
	}

	.status-toggle-btn {
		width: 100%;
		padding: 12px;
		border-radius: 8px;
		font-weight: 600;
		font-size: 0.9rem;
		cursor: pointer;
		border: none;
		transition: all 0.2s;
		display: flex;
		align-items: center;
		justify-content: center;
		gap: 8px;
	}

	.btn-block {
		background: rgba(239, 68, 68, 0.2);
		border: 1px solid #ef4444;
		color: #fca5a5;
	}

	.btn-block:hover:not(:disabled) {
		background: rgba(239, 68, 68, 0.35);
		color: #ffffff;
	}

	.btn-unblock {
		background: rgba(16, 185, 129, 0.2);
		border: 1px solid #10b981;
		color: #6ee7b7;
	}

	.btn-unblock:hover:not(:disabled) {
		background: rgba(16, 185, 129, 0.35);
		color: #ffffff;
	}

	.train-marker-g {
		cursor: pointer;
		transition: transform 0.8s linear;
	}

	.train-label {
		font-size: 0.72rem;
		font-weight: 700;
		text-shadow: 0 1px 3px rgba(0, 0, 0, 0.85);
		pointer-events: none;
	}

	@media (max-width: 1100px) {
		.hero,
		.content {
			grid-template-columns: 1fr;
		}

		.hero {
			display: grid;
			align-items: start;
		}

		.hero-cards {
			min-width: 0;
		}

		.details {
			position: static;
		}
	}

	@media (max-width: 720px) {
		.page {
			padding: 16px;
		}

		.hero-cards,
		.detail-grid {
			grid-template-columns: 1fr;
		}
	}
</style>
