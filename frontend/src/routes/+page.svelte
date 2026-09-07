<script lang="ts">
	import PublicNav from '$lib/components/site/PublicNav.svelte';
	import AuthCard from '$lib/components/site/AuthCard.svelte';
	import { onMount } from 'svelte';
	import { gsap } from 'gsap';
	import type { PageData, ActionData } from './$types';

	export let data: PageData;
	export let form: ActionData;

	const features = [
		{
			id: 'network',
			title: 'Sieć na żywo',
			copy: 'Pełny obraz ruchu i stanu infrastruktury w jednej, czytelnej mapie.'
		},
		{
			id: 'incidents',
			title: 'Szybka reakcja',
			copy: 'Incydenty trafiają do operatora natychmiast, wraz z kontekstem.'
		},
		{
			id: 'timetable',
			title: 'Rozkłady jazdy',
			copy: 'Rozkłady i symulacja pokazują, co dzieje się teraz i co będzie dalej.'
		},
		{
			id: 'scenarios',
			title: 'Scenariusze',
			copy: 'Bezpiecznie sprawdzaj kolejne kroki, zanim zmienisz rzeczywisty ruch.'
		}
	];

	const faqItems = [
		{
			question: 'Czym jest Smart Railway System?',
			answer: 'Smart Railway System to zaawansowana platforma dyspozytorska umożliwiająca podgląd i nadzór nad ruchem kolejowym w czasie rzeczywistym.'
		},
		{
			question: 'Jak działa tryb symulacji i scenariuszy?',
			answer: 'System pozwala operatorom na bezpieczne testowanie i wprowadzanie zmian w ruchu w środowisku symulowanym zanim zostaną one wyemitowane na rzeczywistą sieć kolejową.'
		},
		{
			question: 'Czy muszę zakładać konto, aby wypróbować system?',
			answer: 'Nie. Możesz skorzystać z przycisku „Wejdź jako gość”, aby natychmiast przejść do podglądu systemu w trybie demo.'
		},
		{
			question: 'Z jakimi systemami zewnętrznymi integruje się platforma?',
			answer: 'Platforma przetwarza dane z czujników infrastruktury, systemów sterowania ruchem (SRK) oraz baz rozkładów jazdy.'
		}
	];

	let showAuthModal = false;
	let isClosingAuthModal = false;
	let authMode: 'login' | 'register' = 'login';

	function openAuthModal(mode: 'login' | 'register' = 'login', e?: Event) {
		if (e) e.preventDefault();
		authMode = mode;
		isClosingAuthModal = false;
		showAuthModal = true;
	}

	function closeAuthModal() {
		if (!showAuthModal || isClosingAuthModal) return;
		isClosingAuthModal = true;

		setTimeout(() => {
			showAuthModal = false;
			isClosingAuthModal = false;
		}, 250);
	}

	function handleKeydown(e: KeyboardEvent) {
		if (e.key === 'Escape' && showAuthModal) {
			closeAuthModal();
		}
	}

	const expandRatio = 0.52;
	const duration = 0.6;
	const ease = 'power3.out';
	const tilt = 6;
	const parallax = 0.4;
	const gap = 16;
	const height = 480;

	let activeFeature = 0;
	let featuresRootRef: HTMLElement;
	let featurePanelRefs: HTMLElement[] = [];
	let featureMediaRefs: HTMLElement[] = [];
	let featureTextRefs: HTMLElement[] = [];
	let featureTl: gsap.core.Timeline | null = null;
	let featureMediaSize = 320;

	function applyFeatureLayout() {
		if (!featurePanelRefs.length) return;

		const prefersReduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
		const r = Math.min(Math.max(expandRatio, 0.2), 0.9);
		const count = features.length;
		const grow = count > 1 ? (r * (count - 1)) / (1 - r) : 1;
		const dur = !prefersReduced ? duration : 0;

		featureTl?.kill();
		featureTl = gsap.timeline();

		featurePanelRefs.forEach((panel, i) => {
			if (!panel) return;
			const isActive = i === activeFeature;
			const media = featureMediaRefs[i];
			const text = featureTextRefs[i];

			const rot = isActive ? 0 : i < activeFeature ? tilt : -tilt;

			featureTl!.to(panel, { flexGrow: isActive ? grow : 1, rotateY: rot, duration: dur, ease }, 0);

			if (media) {
				const drift = Math.max(-1.5, Math.min(1.5, activeFeature - i));
				const shift = drift * parallax * featureMediaSize * 0.06;

				featureTl!.to(
					media,
					{
						xPercent: -50,
						yPercent: -50,
						x: isActive ? 0 : shift,
						duration: dur,
						ease
					},
					0
				);
			}

			if (text) {
				if (isActive) {
					featureTl!.to(text, { opacity: 1, x: 0, duration: dur, ease }, 0);
				} else {
					featureTl!.to(text, { opacity: 0, x: -14, duration: dur * 0.6, ease }, 0);
				}
			}
		});
	}

	function setActiveFeature(index: number) {
		if (activeFeature !== index) {
			activeFeature = index;
			applyFeatureLayout();
		}
	}

	function handleFeatureKeyDown(index: number, e: KeyboardEvent) {
		const count = features.length;
		if (e.key === 'ArrowRight' || e.key === 'ArrowDown') {
			e.preventDefault();
			setActiveFeature((index + 1) % count);
		} else if (e.key === 'ArrowLeft' || e.key === 'ArrowUp') {
			e.preventDefault();
			setActiveFeature((index - 1 + count) % count);
		}
	}

	let openFaqIndex: number | null = null;
	let faqAnswerRefs: HTMLElement[] = [];

	function toggleFaq(index: number) {
		const prevIndex = openFaqIndex;
		openFaqIndex = openFaqIndex === index ? null : index;

		if (prevIndex !== null && faqAnswerRefs[prevIndex]) {
			gsap.to(faqAnswerRefs[prevIndex], {
				height: 0,
				opacity: 0,
				duration: 0.4,
				ease: 'power3.out'
			});
		}

		if (openFaqIndex !== null && faqAnswerRefs[openFaqIndex]) {
			const target = faqAnswerRefs[openFaqIndex];
			gsap.fromTo(
				target,
				{ height: 0, opacity: 0 },
				{
					height: 'auto',
					opacity: 1,
					duration: 0.5,
					ease: 'power3.out'
				}
			);
		}
	}

	let footerElement: HTMLElement;

	onMount(() => {
		const measure = () => {
			if (featuresRootRef) {
				const rect = featuresRootRef.getBoundingClientRect();
				const usable = Math.max(rect.width - gap * (features.length - 1), 120);
				featureMediaSize = Math.max(140, usable * Math.min(Math.max(expandRatio, 0.2), 0.9) * 1.22);
				featuresRootRef.style.setProperty('--ag-media-size', `${featureMediaSize}px`);
				applyFeatureLayout();
			}
		};

		measure();
		const ro = new ResizeObserver(measure);
		if (featuresRootRef) ro.observe(featuresRootRef);

		if (!window.matchMedia('(prefers-reduced-motion: reduce)').matches && footerElement) {
			Promise.all([
				import('gsap'),
				import('gsap/SplitText'),
				import('gsap/ScrambleTextPlugin')
			]).then(([gsapModule, splitTextModule, scrambleModule]) => {
				const { gsap: gsapInst } = gsapModule;
				const { SplitText } = splitTextModule;
				const { ScrambleTextPlugin } = scrambleModule;
				gsapInst.registerPlugin(SplitText, ScrambleTextPlugin);

				const elements = footerElement.querySelectorAll<HTMLElement>('.scrambled-text');
				elements.forEach((element) => {
					const split = SplitText.create(element, {
						type: 'chars',
						charsClass: 'scrambled-char'
					});

					split.chars.forEach((character) => {
						gsapInst.set(character, { attr: { 'data-content': character.textContent ?? '' } });
					});

					const handleMove = (event: PointerEvent) => {
						const radius = 42;
						const durationVal = 1.2;

						split.chars.forEach((character) => {
							const { left, top, width, height: h } = character.getBoundingClientRect();
							const distance = Math.hypot(
								event.clientX - (left + width / 2),
								event.clientY - (top + h / 2)
							);

							if (distance < radius) {
								gsapInst.to(character, {
									overwrite: true,
									duration: durationVal * (1 - distance / radius),
									scrambleText: {
										text: character.getAttribute('data-content') ?? '',
										chars: '.:',
										speed: 0.5
									},
									ease: 'none'
								});
							}
						});
					};

					const handleLeave = () => {
						gsapInst.killTweensOf(split.chars);
						split.chars.forEach((character) => {
							character.textContent = character.getAttribute('data-content') ?? '';
						});
					};

					element.addEventListener('pointermove', handleMove);
					element.addEventListener('pointerleave', handleLeave);
				});
			});
		}

		return () => {
			ro.disconnect();
			featureTl?.kill();
		};
	});

	let scrollProgress = 0;
	let cursorX = 0;
	let cursorY = 0;
	let cursorVisible = false;
	let cursorHover = false;

	let heroBoxX = 50;
	let heroBoxY = 50;
	let heroHovered = false;

	function handleHeroPointerMove(e: PointerEvent) {
		const target = e.currentTarget as HTMLElement;
		const rect = target.getBoundingClientRect();
		heroBoxX = e.clientX - rect.left;
		heroBoxY = e.clientY - rect.top;
		heroHovered = true;
	}

	function handleHeroPointerLeave() {
		heroHovered = false;
	}

	let contactName = '';
	let contactEmail = '';
	let contactMessage = '';
	let nameTouched = false;
	let emailTouched = false;
	let messageTouched = false;
	let formSubmittedAttempt = false;
	let formStatus: 'idle' | 'submitting' | 'success' = 'idle';

	$: isEmailValid = /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(contactEmail.trim());
	$: isNameValid = contactName.trim().length >= 2;
	$: isMessageValid = contactMessage.trim().length >= 5;

	$: showNameError = (nameTouched || formSubmittedAttempt) && !isNameValid;
	$: showEmailError = (emailTouched || formSubmittedAttempt) && !isEmailValid;
	$: showMessageError = (messageTouched || formSubmittedAttempt) && !isMessageValid;

	async function handleSubmitContact(event: SubmitEvent) {
		event.preventDefault();
		formSubmittedAttempt = true;

		if (!isNameValid || !isEmailValid || !isMessageValid) return;

		formStatus = 'submitting';

		setTimeout(() => {
			formStatus = 'success';
			contactName = '';
			contactEmail = '';
			contactMessage = '';
			nameTouched = false;
			emailTouched = false;
			messageTouched = false;
			formSubmittedAttempt = false;

			setTimeout(() => (formStatus = 'idle'), 4000);
		}, 1000);
	}

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
			cursorHover =
				event.target instanceof Element &&
				Boolean(event.target.closest('a, button, input, textarea'));
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

<svelte:window on:keydown={handleKeydown} />

<svelte:head>
	<title>Smart Railway — kolej pod pełną kontrolą</title>
	<meta
		name="description"
		content="Inteligentny system monitorowania i zarządzania ruchem kolejowym w czasie rzeczywistym."
	/>
</svelte:head>

<div class="landing">
	<PublicNav authenticated={data.authenticated} on:openLogin={() => openAuthModal('login')} />

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
		<section
			class="hero"
			on:pointermove={handleHeroPointerMove}
			on:pointerleave={handleHeroPointerLeave}
			aria-label="Interaktywna sekcja główna"
		>
			<div
				class="map-reveal-layer"
				class:is-active={heroHovered}
				style={`--reveal-x: ${heroBoxX}px; --reveal-y: ${heroBoxY}px;`}
			>
				<div class="map-grid-pattern"></div>
			</div>
		</section>

		<section id="jak-to-dziala" class="features" aria-labelledby="features-heading">
			<h2 id="features-heading">FUNKCJE</h2>

			<div
				bind:this={featuresRootRef}
				class="accordion-gallery"
				style={`gap: ${gap}px; height: ${height}px;`}
				role="list"
				aria-label="Galeria funkcji"
			>
				{#each features as feature, i}
					<div
						bind:this={featurePanelRefs[i]}
						class="accordion-panel"
						class:is-active={i === activeFeature}
						on:mouseenter={() => setActiveFeature(i)}
						on:focus={() => setActiveFeature(i)}
						on:keydown={(e) => handleFeatureKeyDown(i, e)}
						role="listitem"
						tabindex="0"
						aria-current={i === activeFeature ? 'true' : undefined}
						aria-label={feature.title}
					>
						<div class="panel-inner">
							<div bind:this={featureMediaRefs[i]} class="media-container">
								<div class="feature-image-placeholder"></div>
							</div>
						</div>

						<div class="label-container" aria-hidden="true">
							<div bind:this={featureTextRefs[i]} class="label-content">
								<h3>{feature.title}</h3>
								<p>{feature.copy}</p>
							</div>
						</div>
					</div>
				{/each}
			</div>
		</section>

		<section id="faq" class="faq" aria-labelledby="faq-heading">
			<p id="faq-heading" class="faq-eyebrow">FAQ</p>

			<div class="faq-list">
				{#each faqItems as item, index}
					<div class="faq-item" class:is-open={openFaqIndex === index}>
						<button
							class="faq-trigger"
							type="button"
							on:click={() => toggleFaq(index)}
							aria-expanded={openFaqIndex === index}
						>
							<span class="faq-question">{item.question}</span>
							<span class="faq-icon" aria-hidden="true">+</span>
						</button>
						<div
							bind:this={faqAnswerRefs[index]}
							class="faq-answer-wrapper"
						>
							<div class="faq-answer-inner">
								<p>{item.answer}</p>
							</div>
						</div>
					</div>
				{/each}
			</div>
		</section>

		<section id="kontakt" class="contact" aria-labelledby="contact-heading">
			<p id="contact-heading" class="contact-eyebrow">KONTAKT</p>

			<form class="contact-form" on:submit={handleSubmitContact} novalidate>
				<div class="form-group">
					<label for="name">Imię i nazwisko</label>
					<input
						type="text"
						id="name"
						bind:value={contactName}
						on:blur={() => (nameTouched = true)}
						class:is-invalid={showNameError}
						class:is-valid={nameTouched && isNameValid}
						placeholder="Jan Kowalski"
						disabled={formStatus !== 'idle'}
					/>
					{#if showNameError}
						<span class="field-error-msg">Imię i nazwisko musi mieć co najmniej 2 znaki.</span>
					{/if}
				</div>

				<div class="form-group">
					<label for="email">Adres e-mail</label>
					<input
						type="email"
						id="email"
						bind:value={contactEmail}
						on:blur={() => (emailTouched = true)}
						class:is-invalid={showEmailError}
						class:is-valid={emailTouched && isEmailValid}
						placeholder="jan@example.com"
						disabled={formStatus !== 'idle'}
					/>
					{#if showEmailError}
						<span class="field-error-msg">Wprowadź poprawny adres e-mail.</span>
					{/if}
				</div>

				<div class="form-group">
					<label for="message">Wiadomość</label>
					<textarea
						id="message"
						rows="5"
						bind:value={contactMessage}
						on:blur={() => (messageTouched = true)}
						class:is-invalid={showMessageError}
						class:is-valid={messageTouched && isMessageValid}
						placeholder="Twoja wiadomość..."
						disabled={formStatus !== 'idle'}
					></textarea>
					{#if showMessageError}
						<span class="field-error-msg">Wiadomość musi mieć co najmniej 5 znaków.</span>
					{/if}
				</div>

				<button
					type="submit"
					class="cta cta-primary submit-btn"
					class:is-submitting={formStatus === 'submitting'}
					class:is-success={formStatus === 'success'}
					disabled={formStatus !== 'idle'}
				>
					{#if formStatus === 'submitting'}
						<span class="loading-spinner"></span>
						<span>Wysyłanie...</span>
					{:else if formStatus === 'success'}
						<span>✓ Wiadomość wysłana!</span>
					{:else}
						<span>Wyślij wiadomość</span>
					{/if}
				</button>
			</form>
		</section>

		<footer bind:this={footerElement}>
			<div class="footer-inner">
				<span class="copyright">
					<span class="scrambled-text">© 2026 Smart Railway. Wszelkie prawa zastrzeżone.</span>
				</span>
				<a href="mailto:kontakt@smartrailway.pl" class="footer-link">
					<span class="scrambled-text">kontakt@smartrailway.pl</span>
				</a>
			</div>
		</footer>
	</main>

	{#if showAuthModal}
		<div
			class="modal-backdrop"
			class:is-closing={isClosingAuthModal}
			role="dialog"
			aria-modal="true"
			aria-label="Konto"
		>
			<div class="modal-card" class:is-closing={isClosingAuthModal}>
				<button class="modal-close" type="button" on:click={closeAuthModal} aria-label="Zamknij">✕</button>
				<AuthCard mode={authMode} error={form?.error} email={form?.email} />
			</div>
		</div>
	{/if}
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
		background: #111111;
		color: #f5f7f8;
		font-family: 'Inter Variable', Inter, sans-serif;
		font-size: 16px;
		font-weight: 300;
		transition: background-color 400ms cubic-bezier(0.16, 1, 0.3, 1), color 400ms cubic-bezier(0.16, 1, 0.3, 1);
	}

	:global(html.light-mode) :global(body),
	:global(html.light-mode) .landing {
		background: #f4f5f3;
		color: #1f2933;
	}
	.landing {
		min-height: 100vh;
		background: #111111;
		transition: background-color 400ms cubic-bezier(0.16, 1, 0.3, 1), color 400ms cubic-bezier(0.16, 1, 0.3, 1);
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
		pointer-events: none;
		z-index: 30;
		transition: transform 150ms cubic-bezier(0.16, 1, 0.3, 1), background-color 400ms cubic-bezier(0.16, 1, 0.3, 1);
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
		transition: opacity 180ms cubic-bezier(0.16, 1, 0.3, 1);
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
		transition: transform 250ms cubic-bezier(0.16, 1, 0.3, 1);
	}
	:global(html.light-mode) .cursor-dot {
		background: #111827;
		mix-blend-mode: normal;
	}
	.cursor-dot.is-hovering {
		transform: translate(-50%, -50%) scale(1.7);
	}

	.hero {
		position: relative;
		height: calc(100vh - 76px);
		width: 100%;
		background: #111111;
		overflow: hidden;
		transition: background-color 400ms cubic-bezier(0.16, 1, 0.3, 1);
	}
	:global(html.light-mode) .hero {
		background: #e5e7eb;
	}
	.map-reveal-layer {
		position: absolute;
		inset: 0;
		pointer-events: none;
		opacity: 0;
		transition: opacity 400ms cubic-bezier(0.16, 1, 0.3, 1);
		-webkit-mask-image: radial-gradient(
			circle 220px at var(--reveal-x) var(--reveal-y),
			black 20%,
			transparent 80%
		);
		mask-image: radial-gradient(
			circle 220px at var(--reveal-x) var(--reveal-y),
			black 20%,
			transparent 80%
		);
	}
	.map-reveal-layer.is-active {
		opacity: 1;
	}
	.map-grid-pattern {
		width: 100%;
		height: 100%;
		background-color: #1a1a1a;
		background-image: linear-gradient(rgba(255, 255, 255, 0.07) 1px, transparent 1px),
			linear-gradient(90deg, rgba(255, 255, 255, 0.07) 1px, transparent 1px);
		background-size: 32px 32px;
	}
	:global(html.light-mode) .map-grid-pattern {
		background-color: #ffffff;
		background-image: linear-gradient(rgba(0, 0, 0, 0.08) 1px, transparent 1px),
			linear-gradient(90deg, rgba(0, 0, 0, 0.08) 1px, transparent 1px);
	}

	.features {
		padding: 80px clamp(24px, 8vw, 120px) 110px;
		background: #111111;
		scroll-margin-top: 76px;
		transition: background-color 400ms cubic-bezier(0.16, 1, 0.3, 1);
	}
	:global(html.light-mode) .features {
		background: #f4f5f3;
	}
	.features h2 {
		margin: 0 auto 60px;
		text-align: center;
		font-size: 1rem;
		font-weight: 300;
		letter-spacing: 0.18em;
		text-transform: uppercase;
		color: #dddddd;
		transition: color 400ms cubic-bezier(0.16, 1, 0.3, 1);
	}
	:global(html.light-mode) .features h2 {
		color: #52606a;
	}
	.accordion-gallery {
		display: flex;
		flex-direction: row;
		width: 100%;
		max-width: 100%;
		perspective: 1400px;
	}
	.accordion-panel {
		position: relative;
		display: block;
		min-width: 0;
		min-height: 0;
		flex: 1 1 0%;
		cursor: pointer;
		overflow: hidden;
		background: rgba(255, 255, 255, 0.03);
		border-radius: 16px;
		outline: none;
		transform-style: preserve-3d;
		transform-origin: center;
		will-change: flex-grow, transform;
		box-shadow: 0 10px 30px -18px rgba(0, 0, 0, 0.8);
		border: 0;
		transition: background-color 400ms cubic-bezier(0.16, 1, 0.3, 1), box-shadow 400ms cubic-bezier(0.16, 1, 0.3, 1);
	}
	:global(html.light-mode) .accordion-panel {
		background: rgba(0, 0, 0, 0.04);
		box-shadow: 0 10px 30px -18px rgba(0, 0, 0, 0.12);
	}
	.panel-inner {
		position: absolute;
		inset: 0;
		overflow: hidden;
		border-radius: inherit;
	}
	.media-container {
		position: absolute;
		top: 50%;
		left: 50%;
		width: var(--ag-media-size, 320px);
		height: 100%;
		will-change: transform;
		display: flex;
		align-items: center;
		justify-content: center;
	}
	.feature-image-placeholder {
		width: 100%;
		height: 100%;
		background: transparent;
	}
	.label-container {
		pointer-events: none;
		position: absolute;
		bottom: 24px;
		left: 24px;
		right: 24px;
		z-index: 2;
		display: flex;
		justify-content: center;
	}
	.label-content {
		opacity: 0;
		display: flex;
		flex-direction: column;
		align-items: center;
		text-align: center;
		gap: 6px;
	}
	.label-content h3 {
		margin: 0;
		font-size: 1.1rem;
		font-weight: 500;
		letter-spacing: 0.04em;
		text-transform: uppercase;
		color: #ffffff;
		transition: color 400ms cubic-bezier(0.16, 1, 0.3, 1);
	}
	:global(html.light-mode) .label-content h3 {
		color: #111827;
	}
	.label-content p {
		margin: 0;
		font-size: 0.88rem;
		font-weight: 300;
		color: #97a5ad;
		line-height: 1.4;
		max-width: 34ch;
		transition: color 400ms cubic-bezier(0.16, 1, 0.3, 1);
	}
	:global(html.light-mode) .label-content p {
		color: #6b7280;
	}

	.faq {
		padding: 90px clamp(24px, 8vw, 120px);
		background: #1a1a1a;
		transition: background-color 400ms cubic-bezier(0.16, 1, 0.3, 1);
	}
	:global(html.light-mode) .faq {
		background: #e5e7eb;
	}
	.faq-eyebrow {
		text-align: center;
		margin: 0 0 40px;
		color: #dddddd;
		letter-spacing: 0.18em;
		font-size: 0.85rem;
		font-weight: 300;
		text-transform: uppercase;
		transition: color 400ms cubic-bezier(0.16, 1, 0.3, 1);
	}
	:global(html.light-mode) .faq-eyebrow {
		color: #52606a;
	}
	.faq-list {
		max-width: 800px;
		margin: 0 auto;
		display: flex;
		flex-direction: column;
		gap: 16px;
	}
	.faq-item {
		border: 0;
		border-radius: 12px;
		background: rgba(255, 255, 255, 0.03);
		overflow: hidden;
		transition: background-color 400ms cubic-bezier(0.16, 1, 0.3, 1);
	}
	:global(html.light-mode) .faq-item {
		background: rgba(255, 255, 255, 0.6);
	}
	.faq-trigger {
		width: 100%;
		padding: 22px 28px;
		display: flex;
		justify-content: space-between;
		align-items: center;
		background: none;
		border: 0;
		color: inherit;
		font-family: inherit;
		font-size: 1rem;
		font-weight: 300;
		text-align: left;
		cursor: pointer;
		transition: opacity 200ms cubic-bezier(0.16, 1, 0.3, 1);
	}
	.faq-trigger:hover {
		opacity: 0.7;
	}
	.faq-icon {
		font-size: 1.5rem;
		line-height: 1;
		font-weight: 300;
		margin-left: 16px;
		transition: transform 400ms cubic-bezier(0.16, 1, 0.3, 1);
	}
	.faq-item.is-open .faq-icon {
		transform: rotate(45deg);
	}
	.faq-answer-wrapper {
		height: 0;
		opacity: 0;
		overflow: hidden;
		will-change: height, opacity;
	}
	.faq-answer-inner {
		padding: 0 28px 24px;
	}
	.faq-answer-inner p {
		margin: 0;
		color: #87979f;
		font-weight: 300;
		line-height: 1.7;
		transition: color 400ms cubic-bezier(0.16, 1, 0.3, 1);
	}
	:global(html.light-mode) .faq-answer-inner p {
		color: #52606a;
	}

	.contact {
		padding: 90px clamp(24px, 8vw, 120px);
		background: #151515;
		transition: background-color 400ms cubic-bezier(0.16, 1, 0.3, 1);
	}
	:global(html.light-mode) .contact {
		background: #ffffff;
	}
	.contact-eyebrow {
		text-align: center;
		margin: 0 0 40px;
		color: #dddddd;
		letter-spacing: 0.18em;
		font-size: 0.85rem;
		font-weight: 300;
		text-transform: uppercase;
		transition: color 400ms cubic-bezier(0.16, 1, 0.3, 1);
	}
	:global(html.light-mode) .contact-eyebrow {
		color: #52606a;
	}
	.contact-form {
		max-width: 600px;
		margin: 0 auto;
		display: flex;
		flex-direction: column;
		gap: 20px;
	}
	.form-group {
		display: flex;
		flex-direction: column;
		gap: 8px;
	}
	.form-group label {
		font-size: 0.8rem;
		font-weight: 300;
		letter-spacing: 0.08em;
		text-transform: uppercase;
		color: #87979f;
		transition: color 400ms cubic-bezier(0.16, 1, 0.3, 1);
	}
	:global(html.light-mode) .form-group label {
		color: #52606a;
	}
	.form-group input,
	.form-group textarea {
		width: 100%;
		padding: 14px 18px;
		border-radius: 9px;
		border: 1.5px solid transparent;
		background: rgba(255, 255, 255, 0.05);
		color: #f5f7f8;
		font-family: inherit;
		font-size: 1rem;
		font-weight: 300;
		box-sizing: border-box;
		outline: none;
		transition: border-color 250ms ease, background-color 400ms cubic-bezier(0.16, 1, 0.3, 1), color 400ms cubic-bezier(0.16, 1, 0.3, 1);
	}
	:global(html.light-mode) .form-group input,
	:global(html.light-mode) .form-group textarea {
		background: #e5e7eb;
		color: #1f2933;
	}
	.form-group input.is-invalid,
	.form-group textarea.is-invalid {
		border-color: #ef4444 !important;
		background: rgba(239, 68, 68, 0.06) !important;
	}
	.form-group input.is-valid,
	.form-group textarea.is-valid {
		border-color: #22c55e !important;
	}
	.field-error-msg {
		font-size: 0.8rem;
		color: #fca5a5;
	}
	.cta {
		display: inline-flex;
		align-items: center;
		justify-content: center;
		border: 0;
		border-radius: 9px;
		padding: 14px 22px;
		font-family: inherit;
		font-size: 0.75rem;
		font-weight: 300;
		text-transform: uppercase;
		letter-spacing: 0.08em;
		cursor: pointer;
		transition: opacity 200ms cubic-bezier(0.16, 1, 0.3, 1), background-color 300ms ease, color 300ms ease;
	}
	.cta-primary {
		background: #f4f1eb;
		color: #171717;
	}
	.cta:hover {
		opacity: 0.8;
	}
	.submit-btn.is-success {
		background: #22c55e;
		color: #ffffff;
	}

	footer {
		padding: 40px clamp(24px, 8vw, 120px);
		background: #0d0d0d;
		border-top: 1px solid rgba(255, 255, 255, 0.05);
		transition: background-color 400ms cubic-bezier(0.16, 1, 0.3, 1), border-color 400ms cubic-bezier(0.16, 1, 0.3, 1);
	}
	:global(html.light-mode) footer {
		background: #f4f5f3;
		border-top-color: rgba(0, 0, 0, 0.08);
	}
	.footer-inner {
		max-width: 1200px;
		margin: 0 auto;
		display: flex;
		align-items: center;
		justify-content: space-between;
		gap: 20px;
	}
	.copyright {
		color: #718089;
		font-size: 0.85rem;
		font-family: 'Inter Variable', Inter, sans-serif;
		font-weight: 300;
		transition: color 400ms cubic-bezier(0.16, 1, 0.3, 1);
	}
	:global(html.light-mode) .copyright {
		color: #6b7280;
	}
	.footer-link {
		color: #f4f1eb;
		font-size: 0.85rem;
		text-decoration: none;
		font-family: 'Inter Variable', Inter, sans-serif;
		font-weight: 300;
		transition: color 400ms cubic-bezier(0.16, 1, 0.3, 1);
	}
	:global(html.light-mode) .footer-link {
		color: #1f2933;
	}
	.footer-link:hover {
		color: #ffffff;
	}
	:global(html.light-mode) .footer-link:hover {
		color: #111827;
	}
	:global(.scrambled-char) {
		display: inline-block;
		will-change: contents;
	}

	.modal-backdrop {
		position: fixed;
		inset: 0;
		z-index: 200;
		background: rgba(0, 0, 0, 0.45);
		backdrop-filter: blur(12px);
		-webkit-backdrop-filter: blur(12px);
		display: flex;
		align-items: center;
		justify-content: center;
		padding: 24px;
		pointer-events: none;
		animation: fadeIn 250ms cubic-bezier(0.16, 1, 0.3, 1) forwards;
	}
	.modal-backdrop.is-closing {
		animation: fadeOut 250ms cubic-bezier(0.16, 1, 0.3, 1) forwards;
	}

	.modal-card {
		position: relative;
		width: 100%;
		max-width: 440px;
		pointer-events: auto;
		animation: slideUp 300ms cubic-bezier(0.16, 1, 0.3, 1) forwards;
	}
	.modal-card.is-closing {
		animation: slideDown 250ms cubic-bezier(0.16, 1, 0.3, 1) forwards;
	}

	.modal-close {
		position: absolute;
		top: 18px;
		right: 32px;
		z-index: 20;
		background: none;
		border: 0;
		color: #87979f;
		font-size: 1.1rem;
		cursor: pointer;
		padding: 4px;
		line-height: 1;
		transition: color 200ms cubic-bezier(0.16, 1, 0.3, 1);
	}
	.modal-close:hover {
		color: #ffffff;
	}
	:global(html.light-mode) .modal-close:hover {
		color: #111827;
	}

	@keyframes fadeIn {
		from {
			opacity: 0;
		}
		to {
			opacity: 1;
		}
	}
	@keyframes fadeOut {
		from {
			opacity: 1;
		}
		to {
			opacity: 0;
		}
	}
	@keyframes slideUp {
		from {
			opacity: 0;
			transform: translateY(20px) scale(0.98);
		}
		to {
			opacity: 1;
			transform: translateY(0) scale(1);
		}
	}
	@keyframes slideDown {
		from {
			opacity: 1;
			transform: translateY(0) scale(1);
		}
		to {
			opacity: 0;
			transform: translateY(16px) scale(0.97);
		}
	}
</style>