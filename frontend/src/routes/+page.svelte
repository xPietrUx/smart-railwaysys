<script lang="ts">
	import PublicNav from '$lib/components/site/PublicNav.svelte';
	import { onMount } from 'svelte';
	import type { PageData } from './$types';
	export let data: PageData;

	let scrollProgress = 0;
	let cursorX = 0;
	let cursorY = 0;
	let cursorVisible = false;
	let cursorHover = false;

	onMount(() => {
		const updateScrollProgress = () => {
			const maxScroll = document.documentElement.scrollHeight - window.innerHeight;
			scrollProgress = maxScroll > 0 ? window.scrollY / maxScroll : 0;
		};

		document.documentElement.classList.add('dot-scrollbar');
		updateScrollProgress();
		window.addEventListener('scroll', updateScrollProgress, { passive: true });

		return () => {
			window.removeEventListener('scroll', updateScrollProgress);
			document.documentElement.classList.remove('dot-scrollbar');
		};
	});

	onMount(() => {
		if (!window.matchMedia('(hover: hover) and (pointer: fine)').matches) return;

		const updateCursor = (event: PointerEvent) => {
			cursorX = event.clientX;
			cursorY = event.clientY;
			cursorVisible = true;
			cursorHover = event.target instanceof Element && Boolean(event.target.closest('a, button'));
		};
		const hideCursor = () => (cursorVisible = false);

		document.documentElement.classList.add('dot-cursor');
		window.addEventListener('pointermove', updateCursor);
		window.addEventListener('blur', hideCursor);

		return () => {
			document.documentElement.classList.remove('dot-cursor');
			window.removeEventListener('pointermove', updateCursor);
			window.removeEventListener('blur', hideCursor);
		};
	});
</script>

<svelte:head
	><title>Smart Railway — kolej pod pełną kontrolą</title><meta
		name="description"
		content="Inteligentny system monitorowania i zarządzania ruchem kolejowym w czasie rzeczywistym."
	/></svelte:head
>

<div class="landing">
	<PublicNav authenticated={data.authenticated} />
	<div class="scroll-dot" style={`--scroll-progress: ${scrollProgress}`} aria-hidden="true"></div>
	<div
		class="custom-cursor"
		class:is-visible={cursorVisible}
		style={`--cursor-x: ${cursorX}px; --cursor-y: ${cursorY}px`}
		aria-hidden="true"
	>
		<span class="cursor-dot" class:is-hovering={cursorHover}></span>
	</div>
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
		<section id="o-wa-gone" class="about">
			<p>O WA.GONE</p>
			<h2>Technologia, która utrzymuje kolej w ruchu.</h2>
		</section>
		<section id="dokumentacja" class="documentation">
			<p>DOKUMENTACJA</p>
			<h2>Poznaj architekturę i sposób działania systemu.</h2>
			<a href="https://github.com/xPietrUx/smart-railwaysys#readme" target="_blank" rel="noreferrer"
				>Przejdź do dokumentacji <b>→</b></a
			>
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
	:global(html.dot-scrollbar) {
		scrollbar-width: none;
	}
	:global(html.dot-scrollbar::-webkit-scrollbar) {
		display: none;
	}
	:global(body) {
		margin: 0;
		background: #333333;
		color: #f5f7f8;
		font-family: 'Inter Variable', sans-serif;
		transition:
			background-color 350ms ease,
			color 350ms ease;
	}
	:global(html.light-mode) :global(body),
	:global(html.light-mode) .landing {
		background: #f4f5f3;
		color: #1f2933;
	}
	.landing {
		min-height: 100vh;
		background: #333333;
		transition:
			background-color 350ms ease,
			color 350ms ease;
	}
	.scroll-dot {
		position: fixed;
		top: calc(50% - 60px);
		right: clamp(12px, 2vw, 28px);
		width: 7px;
		height: 7px;
		border-radius: 50%;
		background: #f4f1eb;
		transform: translateY(calc(var(--scroll-progress) * 120px));
		transition:
			background-color 350ms ease,
			transform 80ms linear;
		pointer-events: none;
		z-index: 30;
	}
	:global(html.light-mode) .scroll-dot {
		background: #1f2933;
	}
	.custom-cursor {
		position: fixed;
		top: 0;
		left: 0;
		width: 0;
		height: 0;
		z-index: 100;
		opacity: 0;
		pointer-events: none;
		transform: translate3d(var(--cursor-x), var(--cursor-y), 0);
		transition: opacity 120ms ease;
	}
	.custom-cursor.is-visible {
		opacity: 1;
	}
	.cursor-dot {
		display: block;
		width: 10px;
		height: 10px;
		border-radius: 50%;
		background: #fff;
		mix-blend-mode: difference;
		transform: translate(-50%, -50%) scale(1);
		transition: transform 180ms ease;
	}
	:global(html.light-mode) .cursor-dot {
		background: #111827;
		mix-blend-mode: normal;
	}
	.cursor-dot.is-hovering {
		transform: translate(-50%, -50%) scale(1.7);
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
		transition: color 350ms ease;
	}
	.hero-title {
		margin: 0;
		font-size: clamp(2.4rem, 6vw, 4.6rem);
		line-height: 1.02;
		letter-spacing: -0.01em;
		transition: color 350ms ease;
	}
	.hero-lead {
		margin: 22px 0 0;
		max-width: 480px;
		color: #87979f;
		line-height: 1.7;
		font-size: 1.02rem;
		transition: color 350ms ease;
	}
	:global(html.light-mode) .hero-eyebrow {
		color: #52606a;
	}
	:global(html.light-mode) .hero-lead {
		color: #52606a;
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
		transition: background-color 350ms ease;
	}
	:global(html.light-mode) .features {
		background: #d1d5db;
	}
	.features article {
		background: #292929;
		padding: 70px clamp(24px, 5vw, 70px);
		transition: opacity 180ms ease;
		transition-property: background-color, color, opacity;
		transition-duration: 350ms, 350ms, 180ms;
	}
	:global(html.light-mode) .features article {
		background: #ffffff;
	}
	.features article:hover {
		opacity: 0.72;
	}
	.features article > span {
		color: #dddddd;
		font-size: 0.7rem;
		transition: color 350ms ease;
	}
	.features h2 {
		font-size: 1.35rem;
		transition: color 350ms ease;
	}
	.features p {
		color: #87979f;
		line-height: 1.7;
		transition: color 350ms ease;
	}
	:global(html.light-mode) .features p {
		color: #52606a;
	}
	:global(html.light-mode) .features article > span,
	:global(html.light-mode) .about p,
	:global(html.light-mode) .documentation p {
		color: #52606a;
	}
	.about {
		text-align: center;
		padding: 120px 24px;
		background: #222222;
		transition:
			background-color 350ms ease,
			color 350ms ease;
	}
	:global(html.light-mode) .about {
		background: #e5e7eb;
	}
	.about p {
		color: #dddddd;
		letter-spacing: 0.18em;
		font-size: 0.7rem;
		transition: color 350ms ease;
	}
	.about h2 {
		font-size: clamp(2rem, 4vw, 4rem);
		max-width: 800px;
		margin: 20px auto;
		transition: color 350ms ease;
	}
	.documentation {
		padding: 100px 24px;
		text-align: center;
		background: #292929;
		transition:
			background-color 350ms ease,
			color 350ms ease;
	}
	:global(html.light-mode) .documentation {
		background: #ffffff;
	}
	.documentation p {
		color: #dddddd;
		letter-spacing: 0.18em;
		font-size: 0.7rem;
		transition: color 350ms ease;
	}
	.documentation h2 {
		max-width: 680px;
		margin: 20px auto 32px;
		font-size: clamp(1.8rem, 4vw, 3.2rem);
		transition: color 350ms ease;
	}
	.documentation a {
		color: #f4f1eb;
		font-size: 0.78rem;
		font-weight: 750;
		letter-spacing: 0.08em;
		text-transform: uppercase;
		transition: color 350ms ease;
	}
	:global(html.light-mode) .documentation a {
		color: #1f2933;
	}
	.documentation b {
		margin-left: 7px;
	}
	footer {
		padding: 30px clamp(24px, 8vw, 120px);
		display: flex;
		justify-content: space-between;
		color: #718089;
		font-size: 0.75rem;
		border-top: 1px solid #17242a;
		transition:
			background-color 350ms ease,
			color 350ms ease,
			border-color 350ms ease;
	}
	:global(html.light-mode) footer {
		border-top-color: #d1d5db;
		color: #52606a;
	}
	:global(html.light-mode) footer a {
		color: #374151;
	}
	footer a {
		color: #9fb0b7;
		transition: color 350ms ease;
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
	@media (prefers-reduced-motion: reduce) {
		:global(body),
		.landing,
		.hero-eyebrow,
		.hero-title,
		.hero-lead,
		.features,
		.features article,
		.features article > span,
		.features h2,
		.features p,
		.about,
		.about p,
		.about h2,
		.documentation,
		.documentation p,
		.documentation h2,
		.documentation a,
		footer,
		footer a {
			transition-duration: 0ms;
		}
		.scroll-dot {
			transition: none;
		}
		.cursor-dot {
			transition: none;
		}
	}
	@media (hover: hover) and (pointer: fine) {
		:global(html.dot-cursor),
		:global(html.dot-cursor body),
		:global(html.dot-cursor a),
		:global(html.dot-cursor button) {
			cursor: none;
		}
	}
	@media not all and (hover: hover) and (pointer: fine) {
		.custom-cursor {
			display: none;
		}
	}
</style>
