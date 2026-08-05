<script lang="ts">
	import '@fontsource/inter/latin-ext-400.css';
	import '@fontsource/inter/latin-ext-300.css';
	import '@fontsource/inria-serif/latin-400-italic.css';
	import { createEventDispatcher, onMount } from 'svelte';

	const dispatch = createEventDispatcher<{ enter: void }>();
	const buttonLabel = Array.from('Wejdź');

	let progress = 0;
	let isReady = false;
	let isLeaving = false;

	onMount(() => {
		let animationFrame = 0;
		let destroyed = false;
		const previousScrollRestoration = history.scrollRestoration;

		history.scrollRestoration = 'manual';
		document.documentElement.classList.add('loading-locked');
		document.body.classList.add('loading-locked');
		window.scrollTo(0, 0);

		const start = async () => {
			await document.fonts?.ready;
			if (destroyed) return;

			const reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
			const duration = reduceMotion ? 350 : 2400;
			const startedAt = performance.now();

			const update = (now: number) => {
				const elapsed = Math.min((now - startedAt) / duration, 1);
				progress = Math.round(elapsed * 100);

				if (elapsed < 1) {
					animationFrame = requestAnimationFrame(update);
					return;
				}

				isReady = true;
			};

			animationFrame = requestAnimationFrame(update);
		};

		void start();

		return () => {
			destroyed = true;
			cancelAnimationFrame(animationFrame);
			document.documentElement.classList.remove('loading-locked');
			document.body.classList.remove('loading-locked');
			history.scrollRestoration = previousScrollRestoration;
			window.scrollTo(0, 0);
		};
	});

	function enterPage() {
		if (!isReady || isLeaving) return;
		if (document.activeElement instanceof HTMLElement) document.activeElement.blur();
		window.scrollTo(0, 0);
		isLeaving = true;
		window.setTimeout(() => dispatch('enter'), 650);
	}
</script>

<section
	class:leaving={isLeaving}
	class="loading-screen"
	aria-label="Ekran ładowania"
	aria-busy={!isReady}
>
	<div class="loading-center">
		<h1 class="logo" style:--load={`${progress}%`} aria-label="Wagon.e">
			<span class="logo-serif">Wag</span><span class="logo-sans">on.e</span>
		</h1>

		{#if isReady}
			<button class="enter-button" type="button" on:click={enterPage}>
				<span class="button-label" aria-hidden="true">
					{#each buttonLabel as character, index}
						<span class="letter" style:--letter-index={index}>{character}</span>
					{/each}
				</span>
				<span class="sr-only">Wejdź</span>
			</button>
		{/if}
	</div>

	<div
		class="progress"
		role="progressbar"
		aria-label="Postęp ładowania"
		aria-valuemin="0"
		aria-valuemax="100"
		aria-valuenow={progress}
	>
		{progress}
	</div>
</section>

<style>
	.loading-screen {
		position: fixed;
		inset: 0;
		z-index: 1000;
		display: grid;
		place-items: center;
		min-height: 100dvh;
		background: #191919;
		color: #f3f2ef;
		overflow: hidden;
	}

	.loading-screen.leaving {
		animation: screen-slide-up 650ms cubic-bezier(0.76, 0, 0.24, 1) forwards;
		pointer-events: none;
		will-change: transform;
	}

	.loading-center {
		display: flex;
		flex-direction: column;
		align-items: center;
		gap: 13px;
		transform: translateY(-2px);
	}

	.logo {
		--load: 0%;
		margin: -0.12em -0.16em -0.16em -0.2em;
		padding: 0.12em 0.16em 0.16em 0.2em;
		font-size: 28px;
		font-weight: 400;
		line-height: 1.08;
		letter-spacing: -0.035em;
		white-space: nowrap;
		background: linear-gradient(
			90deg,
			#f3f2ef 0%,
			#f3f2ef calc(var(--load) - 2%),
			rgba(243, 242, 239, 0.5) calc(var(--load) + 5%),
			rgba(243, 242, 239, 0.5) 100%
		);
		-webkit-background-clip: text;
		background-clip: text;
		color: transparent;
	}

	.logo-serif {
		font-family: 'Inria Serif', Georgia, serif;
		font-style: italic;
	}

	.logo-sans {
		font-family: 'Inter', Arial, sans-serif;
		font-size: 1em;
		font-weight: 300;
		font-style: normal;
		letter-spacing: -0.045em;
	}

	.enter-button {
		width: 94px;
		height: 29px;
		padding: 0 16px;
		border: 1px solid rgba(243, 242, 239, 0.85);
		border-radius: 999px;
		background: transparent;
		color: #f3f2ef;
		font:
			400 9px/1 'Inter',
			Arial,
			sans-serif;
		cursor: pointer;
		opacity: 0;
		animation: button-in 420ms cubic-bezier(0.22, 1, 0.36, 1) 100ms forwards;
	}

	.enter-button:focus-visible {
		outline: 1px solid #f3f2ef;
		outline-offset: 4px;
	}

	.button-label {
		display: flex;
		align-items: center;
		justify-content: center;
	}

	.letter {
		--letter-index: 0;
		display: inline-block;
		min-width: 0.24em;
	}

	.enter-button:hover .letter,
	.enter-button:focus-visible .letter {
		animation: letter-hop 440ms cubic-bezier(0.34, 1.56, 0.64, 1) both;
		animation-delay: calc(var(--letter-index) * 42ms);
	}

	.progress {
		position: absolute;
		right: clamp(25px, 2.2vw, 34px);
		bottom: clamp(20px, 2.5vh, 28px);
		min-width: 3ch;
		font:
			italic 400 15px/1 'Inria Serif',
			Georgia,
			serif;
		text-align: right;
		font-variant-numeric: tabular-nums;
	}

	.sr-only {
		position: absolute;
		width: 1px;
		height: 1px;
		padding: 0;
		margin: -1px;
		overflow: hidden;
		clip: rect(0, 0, 0, 0);
		white-space: nowrap;
		border: 0;
	}

	@keyframes button-in {
		from {
			opacity: 0;
			transform: translateY(5px);
		}
		to {
			opacity: 1;
			transform: translateY(0);
		}
	}

	@keyframes letter-hop {
		0%,
		100% {
			transform: translateY(0);
		}
		45% {
			transform: translateY(-4px);
		}
	}

	@keyframes screen-slide-up {
		0% {
			transform: translateY(0);
		}
		100% {
			transform: translateY(-100%);
		}
	}

	@media (max-width: 600px) {
		.loading-center {
			transform: none;
		}

		.progress {
			right: 20px;
			bottom: 20px;
		}
	}

	:global(html.loading-locked),
	:global(body.loading-locked) {
		overflow: hidden;
		overscroll-behavior: none;
	}

	@media (prefers-reduced-motion: reduce) {
		.loading-screen.leaving,
		.enter-button,
		.enter-button:hover .letter,
		.enter-button:focus-visible .letter {
			animation-duration: 1ms;
			animation-delay: 0ms;
		}
	}
</style>
