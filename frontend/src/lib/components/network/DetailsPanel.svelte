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
				×
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
					<strong>⚠️ {$t('details.delayedByIncident')}</strong>
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
	.panel {
		background: rgba(15, 23, 42, 0.82);
		border: 1px solid rgba(148, 163, 184, 0.18);
		box-shadow: 0 24px 60px rgba(15, 23, 42, 0.45);
		backdrop-filter: blur(12px);
		border-radius: 18px;
		padding: 18px;
	}

	.panel-header {
		display: flex;
		justify-content: space-between;
		align-items: flex-start;
		gap: 12px;
		margin-bottom: 12px;
	}

	.panel-label {
		margin: 0 0 6px;
		text-transform: uppercase;
		letter-spacing: 0.14em;
		font-size: 0.72rem;
		color: #93c5fd;
	}

	h2,
	h3,
	p {
		margin: 0;
	}

	h2 {
		font-size: 1.2rem;
	}

	.close {
		border: 1px solid rgba(148, 163, 184, 0.25);
		background: rgba(30, 41, 59, 0.72);
		color: #cbd5e1;
		width: 30px;
		height: 30px;
		border-radius: 9px;
		font-size: 1.15rem;
		line-height: 1;
		cursor: pointer;
		flex-shrink: 0;
	}

	.close:hover {
		border-color: rgba(239, 68, 68, 0.5);
		color: #f8fafc;
	}

	.detail-grid {
		display: grid;
		grid-template-columns: repeat(2, minmax(0, 1fr));
		gap: 10px;
	}

	.detail-grid > div {
		background: rgba(30, 41, 59, 0.72);
		border-radius: 12px;
		padding: 10px 12px;
	}

	.detail-grid span,
	.connections small {
		display: block;
		color: #94a3b8;
		font-size: 0.82rem;
	}

	.detail-grid strong {
		display: block;
		margin-top: 4px;
		font-size: 0.98rem;
	}

	.train-relation {
		margin: 0 0 12px;
		padding: 12px;
		border-radius: 12px;
		background: rgba(37, 99, 235, 0.16);
		border: 1px solid rgba(59, 130, 246, 0.35);
		font-weight: 700;
		font-size: 1rem;
		color: #bfdbfe;
	}

	.delay-card {
		margin-top: 12px;
		padding: 12px;
		border-radius: 12px;
		background: rgba(127, 29, 29, 0.25);
		border: 1px solid rgba(239, 68, 68, 0.45);
	}

	.delay-card strong {
		display: block;
		font-size: 0.9rem;
		color: #fca5a5;
	}

	.delay-card p {
		margin: 6px 0 0;
		font-size: 0.85rem;
		color: #fecaca;
		line-height: 1.4;
	}

	.route-list {
		list-style: none;
		margin: 0;
		padding: 0;
		display: grid;
		gap: 2px;
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
		width: 8px;
		height: 8px;
		border-radius: 999px;
		background: rgba(148, 163, 184, 0.5);
	}

	.route-list li.passed::before {
		background: rgba(148, 163, 184, 0.25);
	}

	.route-list li.current::before {
		background: #38bdf8;
		box-shadow: 0 0 8px #38bdf8;
	}

	.route-list button {
		background: none;
		border: none;
		color: #e2e8f0;
		font-size: 0.87rem;
		padding: 4px 0;
		cursor: pointer;
		text-align: left;
	}

	.route-list li.passed button {
		color: #64748b;
	}

	.route-list li.current button {
		color: #7dd3fc;
		font-weight: 700;
	}

	.route-list button:hover {
		text-decoration: underline;
	}

	.route-list small {
		color: #94a3b8;
		font-size: 0.74rem;
		white-space: nowrap;
	}

	.section {
		margin-top: 16px;
	}

	.section h3 {
		margin-bottom: 10px;
		font-size: 0.95rem;
	}

	.direction-grid {
		display: grid;
		grid-template-columns: 1fr;
		gap: 8px;
	}

	.direction-card {
		border-radius: 12px;
		padding: 10px 12px;
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
		margin-top: 4px;
		font-size: 0.92rem;
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
		gap: 8px;
	}

	.connections button {
		width: 100%;
		text-align: left;
		border: 1px solid rgba(148, 163, 184, 0.14);
		background: rgba(30, 41, 59, 0.72);
		color: inherit;
		padding: 10px 12px;
		border-radius: 12px;
		display: flex;
		justify-content: space-between;
		align-items: center;
		gap: 12px;
		cursor: pointer;
	}

	.connections button:hover {
		border-color: rgba(59, 130, 246, 0.5);
	}

	.connections strong {
		display: block;
	}

	.connections span {
		display: block;
		color: #cbd5e1;
		font-size: 0.84rem;
		margin-top: 2px;
	}

	.train-chip strong {
		display: block;
	}

	.train-chip span {
		display: block;
		color: #cbd5e1;
		font-size: 0.8rem;
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
</style>
