<script lang="ts">
	import { page } from '$app/stores';
	import LanguageSwitcher from '$lib/components/LanguageSwitcher.svelte';
	import { locale, t } from '$lib/i18n';
	import type { ConnectionStatus, LiveSnapshot } from '$lib/services/live';
	import { clearTrains, pauseSimulation, resumeSimulation } from '$lib/services/simulation';
	import type { HighlightFilter } from '$lib/types/selection';
	import type { TrainStatus } from '$lib/types/train';

	export let snapshot: LiveSnapshot;
	export let status: ConnectionStatus;
	export let apiBaseUrl: string;
	export let highlight: HighlightFilter | null = null;
	export let readOnly = false;

	function toggleTrainFilter(trainStatus: TrainStatus) {
		highlight =
			highlight?.kind === 'train-status' && highlight.status === trainStatus
				? null
				: { kind: 'train-status', status: trainStatus };
	}

	function toggleIncidentFilter() {
		highlight = highlight?.kind === 'incidents' ? null : { kind: 'incidents' };
	}

	$: activeTrainStatus = highlight?.kind === 'train-status' ? highlight.status : null;
	$: incidentsActive = highlight?.kind === 'incidents';

	$: debugMode = $page.url.searchParams.get('debug') === '1';

	$: runningCount = snapshot.trains.filter((t) => t.status === 'running').length;
	$: dwellingCount = snapshot.trains.filter((t) => t.status === 'dwelling').length;
	$: waitingCount = snapshot.trains.filter((t) => t.status === 'waiting').length;
	$: derailedCount = snapshot.trains.filter((t) => t.status === 'derailed').length;
	$: activeIncidents = snapshot.events.filter((e) => e.status === 'active').length;

	$: lastUpdateLabel = snapshot.timestamp
		? new Date(snapshot.timestamp * 1000).toLocaleTimeString($locale === 'pl' ? 'pl-PL' : 'en-GB')
		: '—';

	function connectionLabel(connectionStatus: ConnectionStatus): string {
		if (connectionStatus === 'connecting') return $t('connection.connecting');
		if (connectionStatus === 'open') return $t('connection.open');
		if (connectionStatus === 'reconnecting') return $t('connection.reconnecting');
		return $t('connection.polling');
	}

	const statusDotClass: Record<ConnectionStatus, string> = {
		connecting: 'dot-amber',
		open: 'dot-green',
		reconnecting: 'dot-amber',
		'polling-fallback': 'dot-red'
	};

	let triggering = false;
	async function triggerRandomEvent() {
		if (triggering) return;
		triggering = true;
		try {
			await fetch(`${apiBaseUrl}/api/simulation/events/trigger`, { method: 'POST' });
		} catch {
			// Cicho pomijamy błąd -- następny tick i tak pokaże aktualny stan sieci.
		} finally {
			triggering = false;
		}
	}

	// --- Sterowanie symulacją (pauza / wznowienie / czyszczenie floty) ---
	$: paused = snapshot.paused;

	let controlBusy = false;
	// Optymistyczny stan pauzy do czasu potwierdzenia następnym tickiem WS.
	let optimisticPaused: boolean | null = null;
	$: pausedView = optimisticPaused ?? paused;
	// Reaktywne użycie jest rozpoznawane przez Svelte, ale nie przez bazową regułę ESLint.
	// eslint-disable-next-line no-useless-assignment
	$: if (optimisticPaused !== null && paused === optimisticPaused) optimisticPaused = null;

	async function togglePause() {
		if (controlBusy) return;
		controlBusy = true;
		try {
			if (pausedView) {
				await resumeSimulation(fetch, apiBaseUrl);
				optimisticPaused = false;
			} else {
				await pauseSimulation(fetch, apiBaseUrl);
				optimisticPaused = true;
			}
		} catch {
			// 409 przy podwójnym kliknięciu -- następny tick pokaże właściwy stan.
		} finally {
			controlBusy = false;
		}
	}

	async function handleClearTrains() {
		if (controlBusy) return;
		controlBusy = true;
		try {
			await clearTrains(fetch, apiBaseUrl);
		} catch {
			// Cicho pomijamy -- kolejny tick pokaże aktualny stan floty.
		} finally {
			controlBusy = false;
		}
	}
</script>

<header class="bar">
	<div class="title">
		<p class="eyebrow">Smart Railway System</p>
		<h1>{$t('header.title')}</h1>
	</div>

	<div class="right">
		{#if readOnly}<span class="guest-badge">Tryb gościa · tylko podgląd</span>{/if}
		<div class="metrics">
			<button
				type="button"
				class="metric metric-ok"
				class:active={activeTrainStatus === 'running'}
				aria-pressed={activeTrainStatus === 'running'}
				on:click={() => toggleTrainFilter('running')}
				title={activeTrainStatus === 'running'
					? $t('header.filter.disable')
					: $t('header.filter.running')}
			>
				<span>{$t('header.metric.running')}</span>
				<strong>{runningCount}</strong>
				{#if activeTrainStatus === 'running'}<span class="clear-mark">×</span>{/if}
			</button>
			<button
				type="button"
				class="metric"
				class:active={activeTrainStatus === 'dwelling'}
				aria-pressed={activeTrainStatus === 'dwelling'}
				on:click={() => toggleTrainFilter('dwelling')}
				title={activeTrainStatus === 'dwelling'
					? $t('header.filter.disable')
					: $t('header.filter.dwelling')}
			>
				<span>{$t('header.metric.dwelling')}</span>
				<strong>{dwellingCount}</strong>
				{#if activeTrainStatus === 'dwelling'}<span class="clear-mark">×</span>{/if}
			</button>
			<button
				type="button"
				class="metric"
				class:metric-warning={waitingCount > 0}
				class:active={activeTrainStatus === 'waiting'}
				aria-pressed={activeTrainStatus === 'waiting'}
				on:click={() => toggleTrainFilter('waiting')}
				title={activeTrainStatus === 'waiting'
					? $t('header.filter.disable')
					: $t('header.filter.waiting')}
			>
				<span>{$t('header.metric.waiting')}</span>
				<strong>{waitingCount}</strong>
				{#if activeTrainStatus === 'waiting'}<span class="clear-mark">×</span>{/if}
			</button>
			<button
				type="button"
				class="metric"
				class:metric-danger={derailedCount > 0}
				class:active={activeTrainStatus === 'derailed'}
				aria-pressed={activeTrainStatus === 'derailed'}
				on:click={() => toggleTrainFilter('derailed')}
				title={activeTrainStatus === 'derailed'
					? $t('header.filter.disable')
					: $t('header.filter.derailed')}
			>
				<span>{$t('header.metric.derailed')}</span>
				<strong>{derailedCount}</strong>
				{#if activeTrainStatus === 'derailed'}<span class="clear-mark">×</span>{/if}
			</button>
			<button
				type="button"
				class="metric"
				class:metric-danger={activeIncidents > 0}
				class:active={incidentsActive}
				aria-pressed={incidentsActive}
				on:click={toggleIncidentFilter}
				title={incidentsActive ? $t('header.filter.disable') : $t('header.filter.incidents')}
			>
				<span>{$t('header.metric.incidents')}</span>
				<strong>{activeIncidents}</strong>
				{#if incidentsActive}<span class="clear-mark">×</span>{/if}
			</button>
		</div>

		<div class="sim-controls">
			<button
				type="button"
				class="ctrl-btn"
				class:ctrl-paused={pausedView}
				on:click={togglePause}
				disabled={controlBusy}
				title={pausedView ? $t('header.resumeTitle') : $t('header.pauseTitle')}
			>
				{pausedView ? `▶ ${$t('header.resume')}` : `⏸ ${$t('header.pause')}`}
			</button>
			<button
				type="button"
				class="ctrl-btn ctrl-danger"
				on:click={handleClearTrains}
				disabled={controlBusy || snapshot.trains.length === 0}
				title={$t('header.clearTrainsTitle')}
			>
				🗑 {$t('header.clearTrains')}
			</button>
		</div>

		<div class="status-strip" title={$t('header.connectionTitle', { time: lastUpdateLabel })}>
			{#if pausedView}
				<span class="status-dot dot-amber"></span>
				<span class="status-label">{$t('header.paused')}</span>
			{:else}
				<span class="status-dot {statusDotClass[status]}"></span>
				<span class="status-label">{connectionLabel(status)}</span>
			{/if}
			<span class="status-time">{lastUpdateLabel}</span>
		</div>

		{#if debugMode && !readOnly}
			<button type="button" class="debug-btn" on:click={triggerRandomEvent} disabled={triggering}>
				{triggering ? $t('header.triggering') : `🎲 ${$t('header.event')}`}
			</button>
		{/if}

		<LanguageSwitcher />
	</div>
</header>

<style>
	.bar {
		display: flex;
		justify-content: space-between;
		align-items: center;
		gap: 14px;
		flex-wrap: wrap;
		padding: 10px 16px;
		border-radius: 16px;
		background: rgba(15, 23, 42, 0.82);
		border: 1px solid rgba(148, 163, 184, 0.18);
		box-shadow: 0 24px 60px rgba(15, 23, 42, 0.45);
		backdrop-filter: blur(12px);
		font-family: 'Inter Variable', sans-serif;
		font-weight: 300;
	}
	.guest-badge {
		border: 1px solid rgba(203, 213, 225, 0.28);
		border-radius: 9px;
		color: #cbd5e1;
		padding: 6px 9px;
		font-size: 0.66rem;
		font-weight: 300;
		letter-spacing: 0.06em;
		text-transform: uppercase;
	}

	.eyebrow {
		margin: 0;
		text-transform: uppercase;
		letter-spacing: 0.14em;
		font-size: 0.62rem;
		color: #93c5fd;
	}

	h1 {
		margin: 0;
		font-size: 1.1rem;
		line-height: 1.25;
	}

	.right {
		display: flex;
		align-items: center;
		gap: 10px;
		flex-wrap: wrap;
	}

	.right form {
		margin: 0;
	}

	.logout-btn {
		border: 1px solid rgba(148, 163, 184, 0.28);
		border-radius: 9px;
		background: rgba(15, 23, 42, 0.45);
		color: #cbd5e1;
		padding: 7px 10px;
		font: inherit;
		font-size: 0.7rem;
		cursor: pointer;
	}

	.logout-btn:hover {
		border-color: #5eead4;
		color: #f8fafc;
	}

	.metrics {
		display: flex;
		flex-wrap: wrap;
		gap: 6px;
	}

	.metric {
		display: inline-flex;
		align-items: baseline;
		gap: 6px;
		background: rgba(30, 41, 59, 0.72);
		border: 1px solid rgba(148, 163, 184, 0.18);
		border-radius: 10px;
		padding: 5px 10px;
		font: inherit;
		color: inherit;
		cursor: pointer;
		transition:
			border-color 0.3s,
			background 0.3s,
			box-shadow 0.3s;
	}

	.metric:hover {
		border-color: rgba(96, 165, 250, 0.55);
	}

	.metric.active {
		border-color: rgba(96, 165, 250, 0.9);
		background: rgba(37, 99, 235, 0.28);
		box-shadow: 0 0 0 1px rgba(96, 165, 250, 0.5);
	}

	.clear-mark {
		color: #93c5fd;
		font-weight: 700;
		font-size: 0.85rem;
		line-height: 1;
		margin-left: 2px;
	}

	.metric.active:hover .clear-mark {
		color: #f8fafc;
	}

	.metric span {
		color: #94a3b8;
		font-size: 0.72rem;
	}

	.metric strong {
		font-size: 0.98rem;
		line-height: 1;
	}

	.metric-ok strong {
		color: #6ee7b7;
	}

	.metric-warning {
		border-color: rgba(245, 158, 11, 0.45);
	}

	.metric-warning strong {
		color: #fbbf24;
	}

	.metric-danger {
		border-color: rgba(239, 68, 68, 0.5);
		background: rgba(127, 29, 29, 0.28);
	}

	.metric-danger strong {
		color: #fca5a5;
	}

	.status-strip {
		display: flex;
		align-items: center;
		gap: 7px;
		font-size: 0.8rem;
		color: #cbd5e1;
		padding: 6px 12px;
		border-radius: 999px;
		background: rgba(30, 41, 59, 0.72);
		border: 1px solid rgba(148, 163, 184, 0.18);
		white-space: nowrap;
	}

	.status-dot {
		width: 8px;
		height: 8px;
		border-radius: 999px;
		display: inline-block;
		box-shadow: 0 0 8px currentColor;
	}

	.dot-green {
		background: #10b981;
		color: #10b981;
		animation: pulse-dot 2s ease-in-out infinite;
	}

	.dot-amber {
		background: #f59e0b;
		color: #f59e0b;
	}

	.dot-red {
		background: #ef4444;
		color: #ef4444;
	}

	@keyframes pulse-dot {
		0%,
		100% {
			opacity: 1;
		}
		50% {
			opacity: 0.4;
		}
	}

	.status-label {
		font-weight: 600;
		color: #e2e8f0;
	}

	.status-time {
		color: #64748b;
	}

	.sim-controls {
		display: flex;
		gap: 6px;
	}

	.ctrl-btn {
		padding: 6px 12px;
		border-radius: 10px;
		border: 1px solid rgba(148, 163, 184, 0.3);
		background: rgba(30, 41, 59, 0.72);
		color: #e2e8f0;
		font-weight: 600;
		font-size: 0.8rem;
		cursor: pointer;
		white-space: nowrap;
		transition:
			border-color 0.3s,
			background 0.3s;
	}

	.ctrl-btn:hover:not(:disabled) {
		border-color: rgba(96, 165, 250, 0.6);
	}

	.ctrl-btn:disabled {
		opacity: 0.5;
		cursor: default;
	}

	.ctrl-paused {
		border-color: rgba(245, 158, 11, 0.55);
		background: rgba(120, 53, 15, 0.35);
		color: #fbbf24;
	}

	.ctrl-danger:hover:not(:disabled) {
		border-color: rgba(239, 68, 68, 0.7);
		color: #fca5a5;
	}

	.debug-btn {
		padding: 6px 12px;
		border-radius: 10px;
		border: 1px dashed rgba(148, 163, 184, 0.4);
		background: rgba(51, 65, 85, 0.8);
		color: #f8fafc;
		font-weight: 600;
		font-size: 0.8rem;
		cursor: pointer;
	}

	.debug-btn:hover:not(:disabled) {
		border-color: rgba(96, 165, 250, 0.6);
	}

	.debug-btn:disabled {
		opacity: 0.6;
		cursor: default;
	}
</style>
