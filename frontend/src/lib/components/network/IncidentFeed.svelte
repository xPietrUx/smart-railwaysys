<script lang="ts">
	import { onDestroy, onMount } from 'svelte';
	import { t } from '$lib/i18n';
	import { EVENT_ICON, eventLabel, formatEventMessage } from '$lib/services/labels';
	import type { RailEventNode } from '$lib/types/event';
	import type { StationNode } from '$lib/types/network';
	import type { Selected } from '$lib/types/selection';

	export let events: RailEventNode[];
	export let stations: StationNode[] = [];
	export let onSelect: (selected: Selected) => void = () => {};

	let nowSec = Date.now() / 1000;
	let interval: ReturnType<typeof setInterval>;

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
							<span class="icon">{EVENT_ICON[event.type] ?? '⚠️'}</span>
							<div class="incident-body">
								<strong>{eventLabel(event.type, $t)}</strong>
								<p>{formatEventMessage(event, $t, stationName)}</p>
								<small
									>{$t('incidents.resolvesIn', { time: countdownLabel(event.resolvesAt) })}</small
								>
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
								<span class="icon">{EVENT_ICON[event.type] ?? '⚠️'}</span>
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
	.panel {
		background: rgba(15, 23, 42, 0.82);
		border: 1px solid rgba(148, 163, 184, 0.18);
		box-shadow: 0 24px 60px rgba(15, 23, 42, 0.45);
		backdrop-filter: blur(12px);
		border-radius: 18px;
		padding: 18px;
		display: flex;
		flex-direction: column;
		min-height: 0;
	}

	.panel-header {
		margin-bottom: 12px;
		flex-shrink: 0;
	}

	.panel-label {
		margin: 0 0 6px;
		text-transform: uppercase;
		letter-spacing: 0.14em;
		font-size: 0.72rem;
		color: #93c5fd;
	}

	h2,
	h3 {
		margin: 0;
	}

	h2 {
		font-size: 1.2rem;
		display: flex;
		align-items: center;
		gap: 8px;
	}

	.count {
		background: rgba(239, 68, 68, 0.25);
		border: 1px solid rgba(239, 68, 68, 0.45);
		color: #fca5a5;
		border-radius: 999px;
		font-size: 0.78rem;
		font-weight: 700;
		padding: 2px 9px;
		line-height: 1.2;
	}

	.scroll-area {
		overflow-y: auto;
		min-height: 0;
	}

	.empty {
		margin: 0;
		color: #94a3b8;
		font-size: 0.9rem;
		line-height: 1.5;
	}

	.incident-list {
		list-style: none;
		margin: 0;
		padding: 0;
		display: grid;
		gap: 8px;
	}

	.incident {
		display: flex;
		gap: 10px;
		align-items: flex-start;
		padding: 10px 12px;
		border-radius: 12px;
		background: rgba(30, 41, 59, 0.72);
		border: 1px solid rgba(148, 163, 184, 0.14);
		width: 100%;
		text-align: left;
		color: inherit;
	}

	button.incident {
		cursor: pointer;
	}

	button.incident:hover {
		border-color: rgba(59, 130, 246, 0.55);
	}

	.active-incident.severity-major {
		border-color: rgba(239, 68, 68, 0.45);
		background: rgba(127, 29, 29, 0.22);
	}

	.active-incident.severity-major:hover {
		border-color: rgba(239, 68, 68, 0.75);
	}

	.active-incident.severity-minor {
		border-color: rgba(245, 158, 11, 0.4);
		background: rgba(120, 53, 15, 0.2);
	}

	.active-incident.severity-minor:hover {
		border-color: rgba(245, 158, 11, 0.7);
	}

	.icon {
		font-size: 1.25rem;
		line-height: 1;
	}

	.incident-body {
		min-width: 0;
	}

	.incident-body strong {
		display: block;
		font-size: 0.87rem;
	}

	.incident-body p {
		margin: 3px 0 0;
		font-size: 0.83rem;
		color: #cbd5e1;
		line-height: 1.4;
	}

	.incident-body small {
		display: block;
		margin-top: 5px;
		color: #fca5a5;
		font-size: 0.76rem;
		font-weight: 600;
	}

	.section {
		margin-top: 16px;
	}

	.section h3 {
		margin-bottom: 10px;
		font-size: 0.85rem;
		color: #94a3b8;
		text-transform: uppercase;
		letter-spacing: 0.08em;
	}

	.resolved .incident {
		opacity: 0.6;
	}
</style>
