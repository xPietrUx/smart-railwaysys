<script lang="ts">
	import PublicNav from '$lib/components/site/PublicNav.svelte';
	import AuthCard from '$lib/components/site/AuthCard.svelte';
	import type { ActionData } from './$types';
	export let form: ActionData;
</script>

<svelte:head><title>Rejestracja — Smart Railway</title></svelte:head>
<div class="min-h-screen bg-[#333333] text-[#f5f7f8]">
	<PublicNav />
	<main
		class="grid min-h-[calc(100vh-76px)] place-items-center px-5 py-[50px] max-[820px]:min-h-[calc(100vh-66px)]"
	>
		<AuthCard mode="register" error={form?.error} email={form?.email} />
	</main>
</div>
