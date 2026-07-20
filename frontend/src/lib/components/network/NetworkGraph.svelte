<script lang="ts">
	import { SvelteMap } from 'svelte/reactivity';
	import type { RailEventNode } from '$lib/types/event';
	import type { DirectionalState, NetworkGraph, StationNode, TrackSegment } from '$lib/types/network';
	import type { TrainNode } from '$lib/types/train';

	export let graph: NetworkGraph;
	export let trains: TrainNode[] = [];
	export let events: RailEventNode[] = [];

	type Selected = { kind: 'station'; id: string } | { kind: 'segment'; id: string };

	const padding = 56;
	const graphWidth = 1000;
	const graphHeight = 740;
	const plotWidth = graphWidth - padding * 2;
	const plotHeight = graphHeight - padding * 2;
	const TRACK_OFFSET = 3.2;

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

	function formatLine(segment: TrackSegment) {
		return `Linia ${segment.line}`;
	}

	function formatStationType(type: string) {
		return type.charAt(0).toUpperCase() + type.slice(1);
	}

	function directionStatusLabel(status: string) {
		if (status === 'blocked') return 'Zablokowany';
		if (status === 'restricted') return 'Ograniczenie prędkości';
		return 'Aktywny';
	}

	function trainStatusLabel(status: string) {
		if (status === 'running') return 'w drodze';
		if (status === 'dwelling') return 'na przerwie';
		if (status === 'waiting') return 'zatrzymany';
		if (status === 'derailed') return 'wykolejony';
		return status;
	}

	function trainTypeLabel(type: string) {
		if (type === 'IC') return 'InterCity';
		if (type === 'REGIONAL') return 'Regionalny';
		if (type === 'FREIGHT') return 'Towarowy';
		return type;
	}

	function directionLabel(train: TrainNode) {
		return train.direction === 'outbound'
			? `${train.originStationId} → ${train.destinationStationId}`
			: `${train.destinationStationId} → ${train.originStationId}`;
	}

	function handleKeydown(event: KeyboardEvent, action: () => void) {
		if (event.key === 'Enter' || event.key === ' ') {
			event.preventDefault();
			action();
		}
	}

	function segmentColor(state: DirectionalState): string {
		if (state.status === 'blocked') return '#ef4444';
		if (state.status === 'restricted') return '#f59e0b';
		return '#2563eb';
	}

	function segmentDashArray(state: DirectionalState): string | undefined {
		if (state.status === 'blocked') return '7,5';
		if (state.status === 'restricted') return '1,4';
		return undefined;
	}

	function perpendicularOffset(
		source: { x: number; y: number },
		target: { x: number; y: number },
		amount: number
	) {
		const dx = target.x - source.x;
		const dy = target.y - source.y;
		const len = Math.hypot(dx, dy) || 1;
		return { px: (-dy / len) * amount, py: (dx / len) * amount };
	}

	function trainRadius(train: TrainNode) {
		if (train.type === 'IC') return 10.5;
		if (train.type === 'FREIGHT') return 8;
		return 9.2;
	}

	function trainColor(train: TrainNode) {
		if (train.status === 'derailed') return '#ef4444';
		if (train.status === 'waiting') return '#f59e0b';
		if (train.status === 'dwelling') return '#64748b';
		return '#2563eb';
	}

	function getTrainPosition(
		train: TrainNode,
		positionById: Map<string, { x: number; y: number }>
	): { x: number; y: number } | null {
		const current = positionById.get(train.currentStationId);
		if (!current) return null;
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
	$: degreeByStation = (() => {
		const map = new SvelteMap<string, number>();
		for (const segment of segments) {
			map.set(segment.source, (map.get(segment.source) ?? 0) + 1);
			map.set(segment.target, (map.get(segment.target) ?? 0) + 1);
		}
		return map;
	})();
	$: busiestStation = stations.reduce(
		(best, station) => {
			if (!best) return station;
			const currentDegree = degreeByStation.get(station.id) ?? 0;
			const bestDegree = degreeByStation.get(best.id) ?? 0;
			return currentDegree > bestDegree ? station : best;
		},
		null as StationNode | null
	);

	$: stationsWithSignalFailure = new Set(
		events
			.filter((event) => event.status === 'active' && event.type === 'signal_failure' && event.stationId)
			.map((event) => event.stationId as string)
	);

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

	// selectedState jest jedynym realnie mutowanym stanem (klik użytkownika /
	// auto-wybór poniżej) -- reszta to czyste pochodne przeliczane w blokach $:,
	// więc nie potrzebują własnej początkowej wartości.
	let selectedState: Selected | null = null;
	let selectedKind: Selected['kind'] | null;
	let selectedStation: StationNode | null;
	let selectedSegment: TrackSegment | null;
	let connectedSegments: TrackSegment[];
	let selectedStationIds: Set<string>;
	let selectedSegmentNodeIds: Set<string>;

	$: selectedKind = selectedState?.kind ?? null;
	$: if (
		stations.length > 0 &&
		(!selectedState || (selectedState.kind === 'station' && !stationById.has(selectedState.id)))
	) {
		selectedState = { kind: 'station', id: busiestStation?.id ?? stations[0].id };
	}
	$: selectedStation =
		selectedState?.kind === 'station' ? (stationById.get(selectedState.id) ?? null) : null;
	$: {
		if (selectedState?.kind === 'segment') {
			const segmentId = selectedState.id;
			selectedSegment = segments.find((segment) => segment.segmentId === segmentId) ?? null;
		} else {
			selectedSegment = null;
		}
	}
	$: connectedSegments = selectedStation
		? segments.filter(
				(segment) => segment.source === selectedStation?.id || segment.target === selectedStation?.id
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
	$: trainsOnSelectedSegment = selectedSegment
		? trains.filter((train) => train.currentSegmentId === selectedSegment?.segmentId)
		: [];

	function pickStation(id: string) {
		selectedState = { kind: 'station', id };
	}

	function pickSegment(id: string) {
		selectedState = { kind: 'segment', id };
	}
</script>

<div class="panel graph-panel">
	<div class="panel-header">
		<div>
			<p class="panel-label">Wizualizacja sieci</p>
			<h2>Połączenia kolejowe</h2>
		</div>
		<div class="legend">
			<span><i class="legend-shape hub"></i>węzeł</span>
			<span><i class="legend-shape through"></i>przelotowa</span>
			<span><i class="legend-shape terminus"></i>końcowa</span>
			<span><i class="legend-line active"></i>aktywny</span>
			<span><i class="legend-line restricted"></i>ograniczenie</span>
			<span><i class="legend-line blocked"></i>zablokowany</span>
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

			{#each segments as segment (segment.segmentId)}
				{@const source = positionById.get(segment.source)}
				{@const target = positionById.get(segment.target)}
				{@const isSelected = selectedState?.kind === 'segment' && selectedState.id === segment.segmentId}
				{@const isDouble = segment.railTracks >= 2}
				{@const dimmed =
					selectedKind === 'station' &&
					!selectedStationIds.has(segment.source) &&
					!selectedStationIds.has(segment.target)}
				{@const label = `Segment ${segment.segmentId}: ${stationById.get(segment.source)?.name} - ${stationById.get(segment.target)?.name}`}
				{#if source && target}
					{#if isDouble}
						{@const offset = perpendicularOffset(source, target, TRACK_OFFSET)}
						<line
							x1={source.x + offset.px}
							y1={source.y + offset.py}
							x2={target.x + offset.px}
							y2={target.y + offset.py}
							stroke={segmentColor(segment.forward)}
							stroke-width={isSelected ? 3.6 : 2.4}
							stroke-dasharray={segmentDashArray(segment.forward)}
							stroke-linecap="round"
							opacity={dimmed ? 0.18 : 0.85}
							on:click={() => pickSegment(segment.segmentId)}
							role="button"
							tabindex="0"
							aria-label={label}
							on:keydown={(event) => handleKeydown(event, () => pickSegment(segment.segmentId))}
						/>
						<line
							x1={source.x - offset.px}
							y1={source.y - offset.py}
							x2={target.x - offset.px}
							y2={target.y - offset.py}
							stroke={segmentColor(segment.backward)}
							stroke-width={isSelected ? 3.6 : 2.4}
							stroke-dasharray={segmentDashArray(segment.backward)}
							stroke-linecap="round"
							opacity={dimmed ? 0.18 : 0.85}
							on:click={() => pickSegment(segment.segmentId)}
							role="button"
							tabindex="0"
							aria-label={label}
							on:keydown={(event) => handleKeydown(event, () => pickSegment(segment.segmentId))}
						/>
					{:else}
						<line
							x1={source.x}
							y1={source.y}
							x2={target.x}
							y2={target.y}
							stroke={segmentColor(segment.forward)}
							stroke-width={isSelected ? 4.6 : 3.2}
							stroke-dasharray={segmentDashArray(segment.forward)}
							stroke-linecap="round"
							opacity={dimmed ? 0.18 : 0.85}
							on:click={() => pickSegment(segment.segmentId)}
							role="button"
							tabindex="0"
							aria-label={label}
							on:keydown={(event) => handleKeydown(event, () => pickSegment(segment.segmentId))}
						/>
					{/if}
				{/if}
			{/each}

			{#each stations as station (station.id)}
				{@const point = positionById.get(station.id)}
				{@const selected = selectedStation?.id === station.id}
				{@const dimmed = selectedKind === 'segment' && !selectedSegmentNodeIds.has(station.id)}
				{@const shape = stationShape(station.type)}
				{@const hasSignalFailure = stationsWithSignalFailure.has(station.id)}
				{#if point}
					<g
						transform={`translate(${point.x}, ${point.y})`}
						class:selected
						class:dimmed
						on:click={() => pickStation(station.id)}
						role="button"
						tabindex="0"
						aria-label={`Stacja ${station.name}`}
						on:keydown={(event) => handleKeydown(event, () => pickStation(station.id))}
					>
						{#if hasSignalFailure}
							<circle
								r={stationRadius(station) + 7}
								stroke="#f59e0b"
								stroke-width="2.5"
								fill="none"
								class="signal-ring"
							/>
						{/if}
						{#if shape === 'hub'}
							<rect
								x={-stationRadius(station) * 0.8}
								y={-stationRadius(station) * 0.8}
								width={stationRadius(station) * 1.6}
								height={stationRadius(station) * 1.6}
								rx="3"
								transform="rotate(45)"
								fill="#2563eb"
								filter={selected ? 'url(#glow)' : undefined}
							/>
						{:else if shape === 'terminus'}
							<circle r={stationRadius(station)} fill="#f59e0b" filter={selected ? 'url(#glow)' : undefined} />
							<circle r={stationRadius(station) * 0.4} fill="#0f172a" />
						{:else}
							<circle r={stationRadius(station)} fill="#10b981" filter={selected ? 'url(#glow)' : undefined} />
						{/if}
						<circle r={stationRadius(station) + 5} fill="transparent" />
						<text class="station-code" y="-18">{station.code}</text>
						<text class="station-name" y={stationRadius(station) + 18}>{station.name}</text>
					</g>
				{/if}
			{/each}

			{#each trains as train (train.id)}
				{@const pos = getTrainPosition(train, positionById)}
				{#if pos}
					<g
						transform={`translate(${pos.x}, ${pos.y})`}
						class="train-marker"
						class:running={train.status === 'running'}
						class:derailed={train.status === 'derailed'}
						on:click={() => pickStation(train.currentStationId)}
						role="button"
						tabindex="0"
						aria-label={`Pociąg ${train.name}, ${trainStatusLabel(train.status)}`}
						on:keydown={(event) => handleKeydown(event, () => pickStation(train.currentStationId))}
					>
						{#if train.status === 'running'}
							<circle r={trainRadius(train) + 5} fill={trainColor(train)} opacity="0.3" class="train-pulse" />
						{/if}
						<circle r={trainRadius(train)} fill={trainColor(train)} stroke="#ffffff" stroke-width="2" />
						{#if train.status === 'derailed'}
							<text y="4" text-anchor="middle" class="train-warning">!</text>
						{/if}
						<text y={-trainRadius(train) - 7} class="train-label" text-anchor="middle">{train.name}</text>
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
			<div><span>Kod</span><strong>{selectedStation.code}</strong></div>
			<div><span>Typ</span><strong>{formatStationType(selectedStation.type)}</strong></div>
			<div><span>Perony</span><strong>{selectedStation.platforms}</strong></div>
			<div><span>Tory</span><strong>{selectedStation.tracks}</strong></div>
			<div><span>Pociągi/dzień</span><strong>{selectedStation.dailyTrains}</strong></div>
			<div><span>Połączenia</span><strong>{degreeByStation.get(selectedStation.id) ?? 0}</strong></div>
		</div>

		{#if (trainsByStation.get(selectedStation.id) ?? []).length > 0}
			<div class="section">
				<h3>Pociągi na stacji</h3>
				<ul class="connections">
					{#each trainsByStation.get(selectedStation.id) ?? [] as train (train.id)}
						<li class="train-chip status-{train.status}">
							<div>
								<strong>{train.name}</strong>
								<span>{trainTypeLabel(train.type)} · {directionLabel(train)}</span>
							</div>
							<small>{trainStatusLabel(train.status)}</small>
						</li>
					{/each}
				</ul>
			</div>
		{/if}

		<div class="section">
			<h3>Najbliższe połączenia</h3>
			<ul class="connections">
				{#each connectedSegments as segment (segment.segmentId)}
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
			<div><span>Linia</span><strong>{selectedSegment.line}</strong></div>
			<div><span>Długość</span><strong>{selectedSegment.distKm} km</strong></div>
			<div><span>Czas przejazdu</span><strong>{selectedSegment.travelMin} min</strong></div>
			<div><span>Vmax</span><strong>{selectedSegment.vmax} km/h</strong></div>
			<div><span>Tory</span><strong>{selectedSegment.railTracks}</strong></div>
		</div>

		<div class="section">
			<h3>Stan wg kierunku</h3>
			<div class="direction-grid">
				<div class="direction-card status-{selectedSegment.forward.status}">
					<span>{stationById.get(selectedSegment.source)?.name} → {stationById.get(selectedSegment.target)?.name}</span>
					<strong>{directionStatusLabel(selectedSegment.forward.status)}</strong>
					{#if selectedSegment.forward.restrictedVmax}
						<small>do {selectedSegment.forward.restrictedVmax} km/h</small>
					{/if}
				</div>
				<div class="direction-card status-{selectedSegment.backward.status}">
					<span>{stationById.get(selectedSegment.target)?.name} → {stationById.get(selectedSegment.source)?.name}</span>
					<strong>{directionStatusLabel(selectedSegment.backward.status)}</strong>
					{#if selectedSegment.backward.restrictedVmax}
						<small>do {selectedSegment.backward.restrictedVmax} km/h</small>
					{/if}
				</div>
			</div>
		</div>

		{#if trainsOnSelectedSegment.length > 0}
			<div class="section">
				<h3>Pociągi na odcinku</h3>
				<ul class="connections">
					{#each trainsOnSelectedSegment as train (train.id)}
						<li class="train-chip status-{train.status}">
							<div>
								<strong>{train.name}</strong>
								<span>{trainTypeLabel(train.type)}</span>
							</div>
							<small>{Math.round(train.progress * 100)}%</small>
						</li>
					{/each}
				</ul>
			</div>
		{/if}

		<div class="section">
			<h3>Łączy</h3>
			<ul class="connections">
				<li>
					<button type="button" on:click={() => pickStation(selectedSegment?.source ?? '')}>
						<div>
							<strong>{stationById.get(selectedSegment?.source ?? '')?.name}</strong>
							<span>{selectedSegment?.source}</span>
						</div>
						<small>Stacja A</small>
					</button>
				</li>
				<li>
					<button type="button" on:click={() => pickStation(selectedSegment?.target ?? '')}>
						<div>
							<strong>{stationById.get(selectedSegment?.target ?? '')?.name}</strong>
							<span>{selectedSegment?.target}</span>
						</div>
						<small>Stacja B</small>
					</button>
				</li>
			</ul>
		</div>
	{/if}
</aside>

<style>
	.panel {
		background: rgba(15, 23, 42, 0.72);
		border: 1px solid rgba(148, 163, 184, 0.18);
		box-shadow: 0 24px 60px rgba(15, 23, 42, 0.35);
		backdrop-filter: blur(10px);
		border-radius: 20px;
		padding: 20px;
	}

	.panel-header {
		display: flex;
		justify-content: space-between;
		align-items: flex-start;
		gap: 16px;
		margin-bottom: 16px;
	}

	.panel-label {
		margin: 0 0 8px;
		text-transform: uppercase;
		letter-spacing: 0.14em;
		font-size: 0.75rem;
		color: #93c5fd;
	}

	h2,
	h3,
	p {
		margin: 0;
	}

	.legend {
		display: flex;
		gap: 12px;
		flex-wrap: wrap;
		color: #cbd5e1;
		font-size: 0.85rem;
	}

	.legend span {
		display: inline-flex;
		align-items: center;
		gap: 6px;
	}

	.legend-shape {
		width: 11px;
		height: 11px;
		display: inline-block;
	}

	.legend-shape.hub {
		background: #2563eb;
		transform: rotate(45deg);
		border-radius: 2px;
	}

	.legend-shape.through {
		background: #10b981;
		border-radius: 999px;
	}

	.legend-shape.terminus {
		background: #f59e0b;
		border-radius: 999px;
	}

	.legend-line {
		width: 16px;
		height: 3px;
		display: inline-block;
		border-radius: 2px;
	}

	.legend-line.active {
		background: #2563eb;
	}

	.legend-line.restricted {
		background: #f59e0b;
	}

	.legend-line.blocked {
		background: #ef4444;
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

	.graph :global(g.selected circle:first-child),
	.graph :global(g.selected rect) {
		stroke: #f8fafc;
		stroke-width: 3px;
	}

	.graph :global(g.dimmed) {
		opacity: 0.18;
	}

	.signal-ring {
		animation: signal-pulse 1.6s ease-in-out infinite;
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
		font-size: 0.68rem;
		text-anchor: middle;
		paint-order: stroke;
		stroke: rgba(15, 23, 42, 0.75);
		stroke-width: 3px;
	}

	.train-marker {
		transition: transform 0.9s linear;
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
		font-size: 0.62rem;
		font-weight: 700;
		fill: #f8fafc;
		paint-order: stroke;
		stroke: rgba(15, 23, 42, 0.85);
		stroke-width: 3px;
	}

	.train-warning {
		font-size: 0.62rem;
		font-weight: 800;
		fill: #ffffff;
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

	.detail-grid span,
	.connections small {
		display: block;
		color: #94a3b8;
		font-size: 0.85rem;
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

	.direction-grid {
		display: grid;
		grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
		gap: 10px;
	}

	.direction-card {
		border-radius: 14px;
		padding: 12px;
		background: rgba(30, 41, 59, 0.72);
		border: 1px solid rgba(148, 163, 184, 0.14);
	}

	.direction-card span {
		display: block;
		font-size: 0.78rem;
		color: #94a3b8;
	}

	.direction-card strong {
		display: block;
		margin-top: 6px;
		font-size: 0.95rem;
	}

	.direction-card small {
		display: block;
		margin-top: 4px;
		color: #fbbf24;
	}

	.direction-card.status-active strong {
		color: #6ee7b7;
	}

	.direction-card.status-restricted {
		border-color: rgba(245, 158, 11, 0.4);
	}

	.direction-card.status-restricted strong {
		color: #fbbf24;
	}

	.direction-card.status-blocked {
		border-color: rgba(239, 68, 68, 0.45);
	}

	.direction-card.status-blocked strong {
		color: #fca5a5;
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
		cursor: pointer;
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

	.train-chip {
		display: flex;
		justify-content: space-between;
		align-items: center;
		gap: 12px;
		padding: 12px;
		border-radius: 14px;
		background: rgba(30, 41, 59, 0.72);
		border: 1px solid rgba(148, 163, 184, 0.14);
	}

	.train-chip strong {
		display: block;
	}

	.train-chip span {
		display: block;
		color: #cbd5e1;
		font-size: 0.82rem;
		margin-top: 2px;
	}

	.train-chip small {
		font-weight: 700;
		white-space: nowrap;
	}

	.train-chip.status-waiting {
		border-color: rgba(245, 158, 11, 0.4);
	}

	.train-chip.status-waiting small {
		color: #fbbf24;
	}

	.train-chip.status-derailed {
		border-color: rgba(239, 68, 68, 0.45);
	}

	.train-chip.status-derailed small {
		color: #fca5a5;
	}

	.train-chip.status-dwelling small {
		color: #94a3b8;
	}

	.empty-state {
		padding: 24px;
		border-radius: 14px;
		background: rgba(30, 41, 59, 0.72);
		color: #cbd5e1;
	}

	@media (max-width: 1100px) {
		.details {
			position: static;
		}
	}

	@media (max-width: 720px) {
		.detail-grid {
			grid-template-columns: 1fr;
		}
	}
</style>
