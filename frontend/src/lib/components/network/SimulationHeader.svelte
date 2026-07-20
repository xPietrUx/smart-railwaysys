<script lang="ts">
	import { page } from '$app/stores';
	import type { ConnectionStatus, LiveSnapshot } from '$lib/services/live';
	import type { NetworkGraph } from '$lib/types/network';

	export let graph: NetworkGraph;
	export let snapshot: LiveSnapshot;
	export let status: ConnectionStatus;
	export let apiBaseUrl: string;

	$: debugMode = $page.url.searchParams.get('debug') === '1';

	$: runningCount = snapshot.trains.filter((t) => t.status === 'running').length;
	$: dwellingCount = snapshot.trains.filter((t) => t.status === 'dwelling').length;
	$: waitingCount = snapshot.trains.filter((t) => t.status === 'waiting').length;
	$: derailedCount = snapshot.trains.filter((t) => t.status === 'derailed').length;
	$: activeIncidents = snapshot.events.filter((e) => e.status === 'active').length;

	$: lastUpdateLabel = snapshot.timestamp
		? new Date(snapshot.timestamp * 1000).toLocaleTimeString('pl-PL')
		: '—';

	const statusLabels: Record<ConnectionStatus, string> = {
		connecting: 'Łączenie…',
		open: 'Na żywo',
		reconnecting: 'Ponowne łączenie…',
		'polling-fallback': 'Tryb odpytywania'
	};

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
</script>

<section class="hero">
	<div class="hero-title">
		<p class="eyebrow">Smart Railway System</p>
		<h1>Autonomiczna sieć kolejowa Śląska</h1>
		<p class="lede">
			Każdy pociąg kursuje samodzielnie między swoją stacją początkową i końcową, robi
			przerwę po dotarciu, a potem rusza w drogę powrotną. Losowe awarie linii, wykolejenia
			i ograniczenia prędkości pociągi obsługują same -- zatrzymują się albo automatycznie
			przeliczają trasę. Dane na żywo z Memgraph.
		</p>
	</div>

	<div class="status-strip">
		<span class="status-dot {statusDotClass[status]}"></span>
		<span class="status-label">{statusLabels[status]}</span>
		<span class="status-time">aktualizacja {lastUpdateLabel}</span>
	</div>

	<div class="hero-cards">
		<div class="metric">
			<span>Stacje</span>
			<strong>{graph.stations.length}</strong>
		</div>
		<div class="metric">
			<span>Odcinki</span>
			<strong>{graph.segments.length}</strong>
		</div>
		<div class="metric">
			<span>W drodze</span>
			<strong>{runningCount}</strong>
		</div>
		<div class="metric">
			<span>Na przerwie</span>
			<strong>{dwellingCount}</strong>
		</div>
		<div class="metric" class:metric-warning={waitingCount > 0}>
			<span>Zatrzymane</span>
			<strong>{waitingCount}</strong>
		</div>
		<div class="metric" class:metric-danger={derailedCount > 0}>
			<span>Wykolejone</span>
			<strong>{derailedCount}</strong>
		</div>
		<div class="metric" class:metric-danger={activeIncidents > 0}>
			<span>Aktywne incydenty</span>
			<strong>{activeIncidents}</strong>
		</div>
	</div>

	{#if debugMode}
		<div class="debug-panel">
			<button type="button" on:click={triggerRandomEvent} disabled={triggering}>
				{triggering ? 'Wywoływanie…' : '🎲 Wymuś losowe zdarzenie'}
			</button>
			<span class="debug-hint">tryb testowy (?debug=1) -- normalnie zdarzenia losują się same</span>
		</div>
	{/if}
</section>

<style>
	.hero {
		display: flex;
		flex-direction: column;
		gap: 18px;
		margin-bottom: 24px;
	}

	.eyebrow {
		margin: 0 0 8px;
		text-transform: uppercase;
		letter-spacing: 0.14em;
		font-size: 0.75rem;
		color: #93c5fd;
	}

	h1 {
		margin: 0 0 12px;
		font-size: clamp(2rem, 4vw, 3.2rem);
		line-height: 1.05;
	}

	.lede {
		margin: 0;
		max-width: 74ch;
		color: #cbd5e1;
		font-size: 1.02rem;
		line-height: 1.6;
	}

	.status-strip {
		display: flex;
		align-items: center;
		gap: 10px;
		font-size: 0.9rem;
		color: #cbd5e1;
	}

	.status-dot {
		width: 10px;
		height: 10px;
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

	.hero-cards {
		display: grid;
		grid-template-columns: repeat(auto-fit, minmax(120px, 1fr));
		gap: 12px;
	}

	.metric {
		background: rgba(15, 23, 42, 0.72);
		border: 1px solid rgba(148, 163, 184, 0.18);
		box-shadow: 0 24px 60px rgba(15, 23, 42, 0.35);
		backdrop-filter: blur(10px);
		border-radius: 20px;
		padding: 16px;
		transition:
			border-color 0.3s,
			background 0.3s;
	}

	.metric span {
		display: block;
		color: #94a3b8;
		font-size: 0.85rem;
	}

	.metric strong {
		display: block;
		font-size: 1.6rem;
		margin-top: 8px;
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

	.debug-panel {
		display: flex;
		align-items: center;
		gap: 12px;
		padding: 12px 16px;
		border-radius: 14px;
		border: 1px dashed rgba(148, 163, 184, 0.35);
		background: rgba(30, 41, 59, 0.5);
		width: fit-content;
	}

	.debug-panel button {
		padding: 8px 14px;
		border-radius: 10px;
		border: 1px solid rgba(148, 163, 184, 0.3);
		background: rgba(51, 65, 85, 0.8);
		color: #f8fafc;
		font-weight: 600;
		cursor: pointer;
	}

	.debug-panel button:hover:not(:disabled) {
		border-color: rgba(96, 165, 250, 0.6);
	}

	.debug-panel button:disabled {
		opacity: 0.6;
		cursor: default;
	}

	.debug-hint {
		font-size: 0.78rem;
		color: #64748b;
	}
</style>
