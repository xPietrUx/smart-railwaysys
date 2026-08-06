<script lang="ts">
	import { page } from '$app/stores';
</script>

<svelte:head><title>Błąd — Smart Railway</title></svelte:head>

<main class="grid min-h-screen place-items-center bg-[#333333] px-5 text-white">
	<section class="w-full max-w-md rounded-2xl bg-[#1b1b1b] p-10 text-center">
		<p class="mb-3 text-xs tracking-[0.18em] text-[#aaaaaa] uppercase">Błąd {$page.status}</p>
		<h1 class="mb-4 text-xl font-light">Nie udało się otworzyć panelu</h1>
		<p class="mb-8 text-sm leading-6 text-[#aaaaaa]">
			{$page.error?.message ?? 'Spróbuj ponownie za chwilę.'}
		</p>
		<div class="flex justify-center gap-3">
			<a
				class="rounded-lg bg-white px-5 py-3 text-xs font-semibold tracking-wider text-black uppercase"
				href="/panel">Spróbuj ponownie</a
			>
			<a
				class="rounded-lg border border-[#555555] px-5 py-3 text-xs tracking-wider uppercase"
				href="/">Strona główna</a
			>
		</div>
	</section>
</main>
