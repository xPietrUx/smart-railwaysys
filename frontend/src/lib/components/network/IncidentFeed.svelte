<script lang="ts">
	import { onDestroy, onMount } from 'svelte';
	import type { RailEventNode, RailEventType } from '$lib/types/event';

	export let events: RailEventNode[];

	const TYPE_ICON: Record<RailEventType, string> = {
		line_failure: '⚡',
		derailment: '🚨',
		speed_restriction: '🐢',
		signal_failure: '🚦'
	};

	const TYPE_LABEL: Record<RailEventType, string> = {
		line_failure: 'Awaria linii',
		derailment: 'Wykolejenie',
		speed_restriction: 'Ograniczenie prędkości',
		signal_failure: 'Awaria sterowania ruchem'
	};

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
		if (remaining <= 0) return 'lada chwila';
		const minutes = Math.floor(remaining / 60);
		const seconds = remaining % 60;
		return minutes > 0 ? `${minutes} min ${seconds}s` : `${seconds}s`;
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

<aside class="panel incidents">
	<div class="panel-header">
		<div>
			<p class="panel-label">Na żywo</p>
			<h2>Incydenty</h2>
		</div>
	</div>

	{#if activeEvents.length === 0}
		<p class="empty">Brak aktywnych zdarzeń — sieć działa normalnie.</p>
	{:else}
		<ul class="incident-list">
			{#each activeEvents as event (event.id)}
				<li class="incident active-incident severity-{event.severity}">
					<span class="icon">{TYPE_ICON[event.type] ?? '⚠️'}</span>
					<div class="incident-body">
						<strong>{TYPE_LABEL[event.type] ?? event.type}</strong>
						<p>{event.message}</p>
						<small>przywrócenie za {countdownLabel(event.resolvesAt)}</small>
					</div>
				</li>
			{/each}
		</ul>
	{/if}

	{#if resolvedEvents.length > 0}
		<div class="section">
			<h3>Ostatnio rozwiązane</h3>
			<ul class="incident-list resolved">
				{#each resolvedEvents as event (event.id)}
					<li class="incident">
						<span class="icon">{TYPE_ICON[event.type] ?? '⚠️'}</span>
						<div class="incident-body">
							<strong>{TYPE_LABEL[event.type] ?? event.type}</strong>
							<p>{event.message}</p>
						</div>
					</li>
				{/each}
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

	.incidents {
		margin-top: 18px;
	}

	.panel-header {
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
	h3 {
		margin: 0;
	}

	h2 {
		font-size: 1.3rem;
	}

	.empty {
		color: #94a3b8;
		font-size: 0.92rem;
		line-height: 1.5;
	}

	.incident-list {
		list-style: none;
		margin: 0;
		padding: 0;
		display: grid;
		gap: 10px;
	}

	.incident {
		display: flex;
		gap: 10px;
		align-items: flex-start;
		padding: 12px;
		border-radius: 14px;
		background: rgba(30, 41, 59, 0.72);
		border: 1px solid rgba(148, 163, 184, 0.14);
	}

	.active-incident.severity-major {
		border-color: rgba(239, 68, 68, 0.45);
		background: rgba(127, 29, 29, 0.22);
	}

	.active-incident.severity-minor {
		border-color: rgba(245, 158, 11, 0.4);
		background: rgba(120, 53, 15, 0.2);
	}

	.icon {
		font-size: 1.3rem;
		line-height: 1;
	}

	.incident-body {
		min-width: 0;
	}

	.incident-body strong {
		display: block;
		font-size: 0.88rem;
	}

	.incident-body p {
		margin: 4px 0 0;
		font-size: 0.85rem;
		color: #cbd5e1;
		line-height: 1.4;
	}

	.incident-body small {
		display: block;
		margin-top: 6px;
		color: #fca5a5;
		font-size: 0.78rem;
		font-weight: 600;
	}

	.section {
		margin-top: 20px;
	}

	.section h3 {
		margin-bottom: 12px;
		font-size: 0.9rem;
		color: #94a3b8;
		text-transform: uppercase;
		letter-spacing: 0.08em;
	}

	.resolved .incident {
		opacity: 0.6;
	}

	.resolved .incident-body small {
		color: #64748b;
	}
</style>
