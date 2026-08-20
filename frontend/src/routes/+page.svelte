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
		<section class="hero" aria-label="Sekcja główna">
			<div class="hero-inner">
				<p class="hero-eyebrow">Smart Railway System</p>
				<h1 class="hero-title">Kolej pod pełną kontrolą.</h1>
				<p class="hero-lead">
					Podgląd sieci kolejowej Śląska na żywo — pociągi, incydenty i rozkłady w jednym miejscu.
				</p>
				<div class="hero-cta">
					{#if data.authenticated}
						<a class="cta cta-primary" data-sveltekit-preload-data="off" href="/panel"
							>Przejdź do systemu <b>→</b></a
						>
					{:else}
						<form method="POST" action="?/guest">
							<button class="cta cta-primary" type="submit">Wejdź jako gość <b>→</b></button>
						</form>
						<a class="cta cta-ghost" data-sveltekit-preload-data="off" href="/login">Zaloguj się</a>
					{/if}
				</div>
			</div>
		</section>
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
		display: flex;
		align-items: center;
		padding: 0 clamp(24px, 8vw, 120px);
		box-sizing: border-box;
	}
	.hero-inner {
		max-width: 640px;
	}
	.hero-eyebrow {
		margin: 0 0 14px;
		color: #dddddd;
		letter-spacing: 0.18em;
		font-size: 0.7rem;
		text-transform: uppercase;
	}
	.hero-title {
		margin: 0;
		font-size: clamp(2.4rem, 6vw, 4.6rem);
		line-height: 1.02;
		letter-spacing: -0.01em;
	}
	.hero-lead {
		margin: 22px 0 0;
		max-width: 480px;
		color: #87979f;
		line-height: 1.7;
		font-size: 1.02rem;
	}
	.hero-cta {
		display: flex;
		align-items: center;
		gap: 16px;
		margin-top: 40px;
		flex-wrap: wrap;
	}
	.hero-cta form {
		margin: 0;
	}
	.cta {
		display: inline-block;
		border: 0;
		border-radius: 9px;
		padding: 14px 22px;
		font: inherit;
		font-size: 0.72rem;
		font-weight: 750;
		text-transform: uppercase;
		letter-spacing: 0.08em;
		text-decoration: none;
		cursor: pointer;
		transition: opacity 180ms ease;
	}
	.cta:hover {
		opacity: 0.7;
	}
	.cta b {
		margin-left: 7px;
	}
	.cta-primary {
		background: #f4f1eb;
		color: #171717;
	}
	.cta-ghost {
		background: transparent;
		color: #cccccc;
		border: 1px solid #4a4a4a;
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
