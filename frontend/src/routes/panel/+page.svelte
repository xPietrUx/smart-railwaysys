<script lang="ts">
	import { onDestroy, onMount } from 'svelte';
	import DetailsPanel from '$lib/components/network/DetailsPanel.svelte';
	import IncidentFeed from '$lib/components/network/IncidentFeed.svelte';
	import NetworkGraph from '$lib/components/network/NetworkGraph.svelte';
	import SimulationHeader from '$lib/components/network/SimulationHeader.svelte';
	import TimetableEditorModal from '$lib/components/network/TimetableEditorModal.svelte';
	import TimetablePanel from '$lib/components/network/TimetablePanel.svelte';
	import { createLiveStore } from '$lib/services/live';
	import { applyEventsToSegments } from '$lib/services/liveNetwork';
	import type { Scenario } from '$lib/types/scenario';
	import type { HighlightFilter, Selected } from '$lib/types/selection';
	import type { PageData } from './$types';

	export let data: PageData;

	const live = createLiveStore(fetch, data.apiBaseUrl, {
		trains: data.trains,
		events: data.events,
		scenario: null,
		paused: false,
		timestamp: data.timestamp
	});
	const { snapshot, status } = live;

	onMount(() => live.connect());
	onDestroy(() => live.disconnect());

	let selected: Selected | null = null;
	let highlight: HighlightFilter | null = null;
	let mapComponent: NetworkGraph | undefined;

	// Modal szczegółów rozkładu renderowany na poziomie strony (na środku mapy),
	// nie w docku — dock ma backdrop-filter, który uwięziłby position:fixed.
	let editorOpen = false;
	let editorScenario: Scenario | null = null;
	let scenariosRefreshKey = 0;

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

	// Stany torów (blokady, ograniczenia) wyliczane na żywo z aktywnych zdarzeń --
	// graf z SSR jest tylko migawką startową i sam by się nie aktualizował.
	$: liveGraph = {
		...data.graph,
		segments: applyEventsToSegments(data.graph.segments, $snapshot.events)
	};

	function handleWindowKeydown(event: KeyboardEvent) {
		if (event.key === 'Escape' && !editorOpen) {
			selected = null;
			highlight = null;
		}
	}

	function handleIncidentSelect(sel: Selected) {
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

<main class="stage">
	<div class="map-layer">
		<NetworkGraph
			bind:this={mapComponent}
			graph={liveGraph}
			trains={$snapshot.trains}
			events={$snapshot.events}
			bind:highlight
			bind:selected
		/>
	</div>

	<div class="topbar">
		<SimulationHeader
			snapshot={$snapshot}
			status={$status}
			apiBaseUrl={data.apiBaseUrl}
			bind:highlight
			readOnly={data.user.role === 'guest'}
		/>
	</div>

	<aside class="dock dock-left">
		<IncidentFeed events={$snapshot.events} onSelect={handleIncidentSelect} />
	</aside>

	<aside class="dock dock-right">
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
			readOnly={data.user.role === 'guest'}
		/>
	</aside>

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
	}

	:global(body) {
		margin: 0;
		font-family: 'Inter Variable', sans-serif;
		background:
			radial-gradient(circle at top, rgba(37, 99, 235, 0.2), transparent 35%),
			linear-gradient(180deg, #0f172a 0%, #111827 100%);
		color: #e5eefb;
	}

	.stage {
		position: relative;
		height: 100dvh;
		overflow: hidden;
	}

	.map-layer {
		position: absolute;
		inset: 0;
	}

	.topbar {
		position: absolute;
		top: 12px;
		left: 16px;
		right: 16px;
		z-index: 20;
		pointer-events: none;
	}

	.topbar :global(.bar) {
		pointer-events: auto;
	}

	.dock {
		position: absolute;
		top: 96px;
		bottom: 68px;
		z-index: 10;
		width: min(330px, 86vw);
		display: flex;
		flex-direction: column;
		align-items: stretch;
		gap: 12px;
		pointer-events: none;
	}

	/* flex-shrink + min-height pozwalają dwóm panelom (szczegóły + scenariusze)
	   podzielić się wysokością docka zamiast wystawać poza ekran. */
	.dock > :global(*) {
		pointer-events: auto;
		max-height: 100%;
		overflow-y: auto;
		flex: 0 1 auto;
		min-height: 0;
	}

	.dock-left {
		left: 16px;
	}

	.dock-right {
		right: 16px;
	}

	/* Gdy topbar zawija się do dwóch wierszy, panele muszą zacząć niżej. */
	@media (max-width: 1400px) {
		.dock {
			top: 132px;
		}
	}

	/* Wąskie ekrany: zwykły układ pionowy zamiast nakładek. */
	@media (max-width: 900px) {
		.stage {
			height: auto;
			min-height: 100dvh;
			overflow: visible;
			display: flex;
			flex-direction: column;
			gap: 12px;
			padding: 12px;
			box-sizing: border-box;
		}

		.map-layer {
			position: relative;
			inset: auto;
			height: 60vh;
			border-radius: 16px;
			overflow: hidden;
			border: 1px solid rgba(148, 163, 184, 0.18);
			order: 2;
		}

		.topbar {
			position: static;
			pointer-events: auto;
			order: 1;
		}

		.dock {
			position: static;
			width: auto;
			pointer-events: auto;
		}

		.dock > :global(*) {
			max-height: none;
			overflow-y: visible;
		}

		.dock-right {
			order: 3;
		}

		.dock-left {
			order: 4;
		}
	}
</style>
