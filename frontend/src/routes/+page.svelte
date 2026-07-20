<script lang="ts">
	import { onDestroy, onMount } from 'svelte';
	import IncidentFeed from '$lib/components/network/IncidentFeed.svelte';
	import NetworkGraph from '$lib/components/network/NetworkGraph.svelte';
	import SimulationHeader from '$lib/components/network/SimulationHeader.svelte';
	import { createLiveStore } from '$lib/services/live';
	import type { PageData } from './$types';

	export let data: PageData;

	const live = createLiveStore(fetch, data.apiBaseUrl, {
		trains: data.trains,
		events: data.events,
		timestamp: data.timestamp
	});
	const { snapshot, status } = live;

	onMount(() => live.connect());
	onDestroy(() => live.disconnect());
</script>

<svelte:head>
	<title>Smart Railway System — autonomiczna sieć kolejowa</title>
	<meta
		name="description"
		content="Autonomiczna symulacja pociągów na sieci kolejowej województwa śląskiego, na żywo z Memgraph."
	/>
</svelte:head>

<main class="page">
	<SimulationHeader graph={data.graph} snapshot={$snapshot} status={$status} apiBaseUrl={data.apiBaseUrl} />

	<section class="content">
		<NetworkGraph graph={data.graph} trains={$snapshot.trains} events={$snapshot.events} />
		<IncidentFeed events={$snapshot.events} />
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

	.content {
		display: grid;
		grid-template-columns: minmax(0, 1.7fr) minmax(300px, 0.9fr);
		gap: 18px;
		align-items: start;
	}

	.content :global(.graph-panel) {
		grid-column: 1;
		grid-row: 1 / -1;
	}

	.content :global(.details) {
		grid-column: 2;
		grid-row: 1;
	}

	.content :global(.incidents) {
		grid-column: 2;
		grid-row: 2;
	}

	@media (max-width: 1100px) {
		.content {
			grid-template-columns: 1fr;
		}

		.content :global(.graph-panel),
		.content :global(.details),
		.content :global(.incidents) {
			grid-column: 1;
			grid-row: auto;
		}
	}

	@media (max-width: 720px) {
		.page {
			padding: 16px;
		}
	}
</style>
