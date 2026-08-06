<script lang="ts">
	import PublicNav from '$lib/components/site/PublicNav.svelte';
	import type { PageData } from './$types';
	export let data: PageData;
</script>

<svelte:head
	><title>Smart Railway — kolej pod pełną kontrolą</title><meta
		name="description"
		content="Inteligentny system monitorowania i zarządzania ruchem kolejowym w czasie rzeczywistym."
	/></svelte:head
>

<div class="landing">
	<PublicNav authenticated={data.authenticated} />
	<main>
		<section class="hero" aria-label="Sekcja główna"></section>
		<section id="jak-to-dziala" class="features">
			<article>
				<span>01</span>
				<h2>Sieć na żywo</h2>
				<p>Pełny obraz ruchu i stanu infrastruktury w jednej, czytelnej mapie.</p>
			</article>
			<article>
				<span>02</span>
				<h2>Szybka reakcja</h2>
				<p>Incydenty trafiają do operatora natychmiast, wraz z kontekstem.</p>
			</article>
			<article>
				<span>03</span>
				<h2>Lepsze decyzje</h2>
				<p>Scenariusze i rozkłady pozwalają bezpiecznie planować kolejne kroki.</p>
			</article>
		</section>
		<section id="o-nas" class="about">
			<p>SMART RAILWAY SYSTEM</p>
			<h2>Technologia, która utrzymuje kolej w ruchu.</h2>
		</section>
		<footer id="kontakt">
			<span>© 2026 Smart Railway</span><a href="mailto:kontakt@smartrailway.pl"
				>kontakt@smartrailway.pl</a
			>
		</footer>
	</main>
</div>

<style>
	:global(html) {
		scroll-behavior: smooth;
	}
	:global(body) {
		margin: 0;
		background: #333333;
		color: #f5f7f8;
		font-family: 'Inter Variable', sans-serif;
	}
	.landing {
		min-height: 100vh;
		background: #333333;
	}
	.hero {
		min-height: calc(100vh - 76px);
	}
	.features {
		display: grid;
		grid-template-columns: repeat(3, 1fr);
		gap: 1px;
		background: #444444;
		padding: 1px;
	}
	.features article {
		background: #292929;
		padding: 70px clamp(24px, 5vw, 70px);
		transition: opacity 180ms ease;
	}
	.features article:hover {
		opacity: 0.72;
	}
	.features article > span {
		color: #dddddd;
		font-size: 0.7rem;
	}
	.features h2 {
		font-size: 1.35rem;
	}
	.features p {
		color: #87979f;
		line-height: 1.7;
	}
	.about {
		text-align: center;
		padding: 120px 24px;
		background: #222222;
	}
	.about p {
		color: #dddddd;
		letter-spacing: 0.18em;
		font-size: 0.7rem;
	}
	.about h2 {
		font-size: clamp(2rem, 4vw, 4rem);
		max-width: 800px;
		margin: 20px auto;
	}
	footer {
		padding: 30px clamp(24px, 8vw, 120px);
		display: flex;
		justify-content: space-between;
		color: #718089;
		font-size: 0.75rem;
		border-top: 1px solid #17242a;
	}
	footer a {
		color: #9fb0b7;
	}
	footer a:hover {
		opacity: 0.6;
	}
	@media (max-width: 900px) {
		.features {
			grid-template-columns: 1fr;
		}
	}
	@media (max-width: 560px) {
		.features article {
			padding: 45px 24px;
		}
	}
</style>
