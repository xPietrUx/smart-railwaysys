<script lang="ts">
	import NetworkGraph from '$lib/components/network/NetworkGraph.svelte';
	import type { PageData } from './$types';

	export let data: PageData;
</script>

<NetworkGraph graph={data.graph} />
