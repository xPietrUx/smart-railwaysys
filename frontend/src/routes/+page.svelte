<script lang="ts">
    import PublicNav from '$lib/components/site/PublicNav.svelte';
    import AuthCard from '$lib/components/site/AuthCard.svelte';
    import { t } from '$lib/i18n';
    import { onMount, tick } from 'svelte';
    import { gsap } from 'gsap';
    import { ScrollTrigger } from 'gsap/ScrollTrigger';
    import type { PageData, ActionData } from './$types';

    export let data: PageData;
    export let form: ActionData;

    $: features = [
        {
            id: 'network',
            title: $t('landing.features.network.title'),
            copy: $t('landing.features.network.copy')
        },
        {
            id: 'incidents',
            title: $t('landing.features.incidents.title'),
            copy: $t('landing.features.incidents.copy')
        },
        {
            id: 'timetable',
            title: $t('landing.features.timetable.title'),
            copy: $t('landing.features.timetable.copy')
        },
        {
            id: 'scenarios',
            title: $t('landing.features.scenarios.title'),
            copy: $t('landing.features.scenarios.copy')
        }
    ];

    $: faqItems = [
        {
            question: $t('landing.faq.q1.question'),
            answer: $t('landing.faq.q1.answer')
        },
        {
            question: $t('landing.faq.q2.question'),
            answer: $t('landing.faq.q2.answer')
        },
        {
            question: $t('landing.faq.q3.question'),
            answer: $t('landing.faq.q3.answer')
        },
        {
            question: $t('landing.faq.q4.question'),
            answer: $t('landing.faq.q4.answer')
        }
    ];

    let showAuthModal = false;
    let isClosingAuthModal = false;
    let authMode: 'login' | 'register' = 'login';
    let triggerElement: HTMLElement | null = null;
    let modalElement: HTMLElement | null = null;

    async function openAuthModal(mode: 'login' | 'register' = 'login', e?: Event) {
        if (e) {
            e.preventDefault();
            triggerElement = e.currentTarget as HTMLElement;
        } else {
            triggerElement = document.activeElement as HTMLElement;
        }
        authMode = mode;
        isClosingAuthModal = false;
        showAuthModal = true;
        await tick();
        const closeBtn = modalElement?.querySelector<HTMLButtonElement>('.modal-close');
        closeBtn?.focus();
    }

    function closeAuthModal() {
        if (!showAuthModal || isClosingAuthModal) return;
        isClosingAuthModal = true;
        setTimeout(() => {
            showAuthModal = false;
            isClosingAuthModal = false;
            triggerElement?.focus();
        }, 250);
    }

    function handleBackdropClick(e: MouseEvent) {
        if (e.target === e.currentTarget) closeAuthModal();
    }

    function handleModalKeydown(e: KeyboardEvent) {
        if (e.key === 'Escape') {
            e.stopPropagation();
            closeAuthModal();
            return;
        }
        if (e.key === 'Tab' && modalElement) {
            const focusables = modalElement.querySelectorAll<HTMLElement>(
                'button:not([disabled]), input:not([disabled]), [tabindex]:not([tabindex="-1"])'
            );
            if (!focusables.length) return;
            const first = focusables[0];
            const last = focusables[focusables.length - 1];

            if (e.shiftKey && document.activeElement === first) {
                e.preventDefault();
                last.focus();
            } else if (!e.shiftKey && document.activeElement === last) {
                e.preventDefault();
                first.focus();
            }
        }
    }

    const expandRatio = 0.52;
    const duration = 0.6;
    const ease = 'power3.out';
    const tilt = 6;
    const gap = 16;
    const height = 480;

    let activeFeature = 0;
    let featurePanelRefs: HTMLElement[] = [];
    let featureTextRefs: HTMLElement[] = [];
    let featureTl: gsap.core.Timeline | null = null;

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
            const text = featureTextRefs[i];
            const rot = isActive ? 0 : i < activeFeature ? tilt : -tilt;

            featureTl!.to(panel, { flexGrow: isActive ? grow : 1, rotateY: rot, duration: dur, ease }, 0);
            if (text) {
                featureTl!.to(text, { opacity: isActive ? 1 : 0, y: isActive ? 0 : 12, duration: dur, ease }, 0);
            }
        });
    }

    function setActiveFeature(index: number) {
        if (activeFeature !== index) {
            activeFeature = index;
            applyFeatureLayout();
        }
    }

    function handlePanelKeydown(e: KeyboardEvent, index: number) {
        if (e.key === 'Enter' || e.key === ' ') {
            e.preventDefault();
            setActiveFeature(index);
        }
    }

    let openFaqIndex: number | null = null;
    let faqAnswerRefs: HTMLElement[] = [];

    function toggleFaq(index: number) {
        const prevIndex = openFaqIndex;
        openFaqIndex = openFaqIndex === index ? null : index;

        if (prevIndex !== null && faqAnswerRefs[prevIndex]) {
            gsap.to(faqAnswerRefs[prevIndex], { height: 0, opacity: 0, duration: 0.4, ease: 'power3.out' });
        }
        if (openFaqIndex !== null && faqAnswerRefs[openFaqIndex]) {
            gsap.fromTo(
                faqAnswerRefs[openFaqIndex],
                { height: 0, opacity: 0 },
                { height: 'auto', opacity: 1, duration: 0.5, ease: 'power3.out' }
            );
        }
    }

    let footerElement: HTMLElement;
    let scrollProgress = 0;
    let isHeroVisible = false;

    let heroTrack: HTMLElement;
    let heroScreen: HTMLElement;
    let heroScaleBox: HTMLElement;
    let heroDot: HTMLElement;
    let heroContent: HTMLElement;
    let heroHint: HTMLElement;

    onMount(() => {
        gsap.registerPlugin(ScrollTrigger);

        const updateMetrics = () => {
            const maxScroll = document.documentElement.scrollHeight - window.innerHeight;
            scrollProgress = maxScroll > 0 ? window.scrollY / maxScroll : 0;
        };

        window.addEventListener('scroll', updateMetrics, { passive: true });
        window.addEventListener('resize', updateMetrics, { passive: true });
        updateMetrics();
        applyFeatureLayout();

        const st = ScrollTrigger.create({
            trigger: heroTrack,
            start: 'top top',
            end: 'bottom bottom',
            pin: heroScreen,
            scrub: true,
            onUpdate: (self) => {
                const progress = self.progress;

                gsap.set(heroHint, { opacity: Math.max(0, 1 - progress * 4) });

                const scaleValue = 1 + Math.pow(progress, 2.2) * 180;
                gsap.set(heroScaleBox, { scale: scaleValue });

                if (progress > 0.05) {
                    heroDot.style.animationPlayState = 'paused';
                } else {
                    heroDot.style.animationPlayState = 'running';
                }

                if (progress > 0.45) {
                    isHeroVisible = true;
                    const textProgress = (progress - 0.45) / 0.55;
                    gsap.set(heroContent, {
                        opacity: Math.min(1, textProgress * 1.5),
                        y: (1 - textProgress) * 40
                    });
                } else {
                    isHeroVisible = false;
                    gsap.set(heroContent, { opacity: 0, y: 40 });
                }
            }
        });

        return () => {
            window.removeEventListener('scroll', updateMetrics);
            window.removeEventListener('resize', updateMetrics);
            featureTl?.kill();
            st.kill();
        };
    });

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

    function handleSubmitContact(event: SubmitEvent) {
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
</script>

<svelte:head>
    <link
        rel="stylesheet"
        href="https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined:opsz,wght,FILL,GRAD@20..48,100..700,0..1,-50..200"
    />
    <title>{$t('landing.head.title')}</title>
</svelte:head>

<div class="landing">
    <PublicNav authenticated={data.authenticated} on:openLogin={(e) => openAuthModal('login', e)} />

    <div class="scroll-dot" style={`--scroll-progress: ${scrollProgress}`} aria-hidden="true"></div>

    <main id="main-content" aria-hidden={showAuthModal}>
        <section class="hero-scroll-track" bind:this={heroTrack} aria-label={$t('landing.hero.aria')}>
            <div class="hero-sticky-screen" bind:this={heroScreen}>
                <div class="hero-dot-scale-box" bind:this={heroScaleBox} aria-hidden="true">
                    <div class="hero-dot" bind:this={heroDot}></div>
                </div>

                <div class="hero-scroll-hint" bind:this={heroHint} aria-hidden="true">
                    <span>{$t('landing.hero.scrollHint')}</span>
                    <span class="material-symbols-outlined hint-icon">south</span>
                </div>

                <div class="sim-content" bind:this={heroContent} aria-hidden={!isHeroVisible}>
                    <p class="sim-eyebrow">{$t('landing.hero.eyebrow')}</p>
                    <h1 class="sim-title">{$t('landing.hero.title')}</h1>
                </div>
            </div>
        </section>

        <section id="jak-to-dziala" class="features" aria-labelledby="features-heading">
            <h2 id="features-heading">{$t('landing.features.heading')}</h2>

            <div
                class="accordion-gallery"
                style={`gap: ${gap}px; height: ${height}px;`}
                role="region"
                aria-label={$t('landing.features.aria')}
            >
                {#each features as feature, i}
                    <div
                        bind:this={featurePanelRefs[i]}
                        class="accordion-panel"
                        class:is-active={i === activeFeature}
                        on:mouseenter={() => setActiveFeature(i)}
                        on:focus={() => setActiveFeature(i)}
                        on:keydown={(e) => handlePanelKeydown(e, i)}
                        role="button"
                        tabindex="0"
                        aria-pressed={i === activeFeature}
                        aria-label={feature.title}
                    >
                        <div class="panel-content">
                            <div class="panel-number" aria-hidden="true">0{i + 1}</div>
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
            <p id="faq-heading" class="faq-eyebrow">{$t('landing.faq.heading')}</p>
            <div class="faq-list">
                {#each faqItems as item, index}
                    <div class="faq-item" class:is-open={openFaqIndex === index}>
                        <button
                            class="faq-trigger"
                            type="button"
                            on:click={() => toggleFaq(index)}
                            aria-expanded={openFaqIndex === index}
                            aria-controls={`faq-answer-${index}`}
                            id={`faq-btn-${index}`}
                        >
                            <span class="faq-question">{item.question}</span>
                            <span class="faq-icon" aria-hidden="true">+</span>
                        </button>
                        <div
                            bind:this={faqAnswerRefs[index]}
                            id={`faq-answer-${index}`}
                            role="region"
                            aria-labelledby={`faq-btn-${index}`}
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
            <p id="contact-heading" class="contact-eyebrow">{$t('landing.contact.heading')}</p>
            <form class="contact-form" on:submit={handleSubmitContact} novalidate>
                <div class="form-group">
                    <label for="contact-name">{$t('landing.contact.name')}</label>
                    <input
                        type="text"
                        id="contact-name"
                        bind:value={contactName}
                        on:blur={() => (nameTouched = true)}
                        placeholder={$t('landing.contact.namePlaceholder')}
                        aria-invalid={showNameError ? 'true' : undefined}
                        aria-describedby={showNameError ? 'name-error-msg' : undefined}
                    />
                    {#if showNameError}
                        <span id="name-error-msg" class="field-error-msg" role="alert">
                            {$t('landing.contact.nameError')}
                        </span>
                    {/if}
                </div>
                <div class="form-group">
                    <label for="contact-email">{$t('landing.contact.email')}</label>
                    <input
                        type="email"
                        id="contact-email"
                        bind:value={contactEmail}
                        on:blur={() => (emailTouched = true)}
                        placeholder={$t('landing.contact.emailPlaceholder')}
                        aria-invalid={showEmailError ? 'true' : undefined}
                        aria-describedby={showEmailError ? 'email-error-msg' : undefined}
                    />
                    {#if showEmailError}
                        <span id="email-error-msg" class="field-error-msg" role="alert">
                            {$t('landing.contact.emailError')}
                        </span>
                    {/if}
                </div>
                <div class="form-group">
                    <label for="contact-message">{$t('landing.contact.message')}</label>
                    <textarea
                        id="contact-message"
                        rows="5"
                        bind:value={contactMessage}
                        on:blur={() => (messageTouched = true)}
                        placeholder={$t('landing.contact.messagePlaceholder')}
                        aria-invalid={showMessageError ? 'true' : undefined}
                        aria-describedby={showMessageError ? 'message-error-msg' : undefined}
                    ></textarea>
                    {#if showMessageError}
                        <span id="message-error-msg" class="field-error-msg" role="alert">
                            {$t('landing.contact.messageError')}
                        </span>
                    {/if}
                </div>
                <button type="submit" class="cta cta-primary submit-btn">
                    <span>
                        {formStatus === 'submitting'
                            ? $t('landing.contact.sending')
                            : formStatus === 'success'
                              ? $t('landing.contact.success')
                              : $t('landing.contact.send')}
                    </span>
                </button>
            </form>
        </section>

        <footer bind:this={footerElement}>
            <div class="footer-inner">
                <span class="copyright">{$t('landing.footer.rights')}</span>
                <a href="mailto:kontakt@wagone.pl" class="footer-link">kontakt@wagone.pl</a>
            </div>
        </footer>
    </main>

    {#if showAuthModal}
        <!-- svelte-ignore a11y_click_events_have_key_events a11y_no_static_element_interactions -->
        <div
            class="modal-backdrop"
            class:is-closing={isClosingAuthModal}
            role="dialog"
            aria-modal="true"
            aria-label={authMode === 'login' ? 'Logowanie' : 'Rejestracja'}
            bind:this={modalElement}
            on:click={handleBackdropClick}
            on:keydown={handleModalKeydown}
        >
            <div class="modal-card" class:is-closing={isClosingAuthModal}>
                <button
                    class="modal-close"
                    type="button"
                    on:click={closeAuthModal}
                    title={$t('landing.modal.close')}
                    aria-label={$t('landing.modal.close')}
                >
                    <span class="material-symbols-outlined" aria-hidden="true">close</span>
                </button>
                <AuthCard mode={authMode} error={form?.error} email={form?.email} />
            </div>
        </div>
    {/if}
</div>

<style>
    :global(:root) {
        --bg-main: #111111;
        --bg-panel: rgba(255, 255, 255, 0.03);
        --bg-faq: rgba(255, 255, 255, 0.03);
        --bg-input: rgba(255, 255, 255, 0.04);
        --text-main: #f5f7f8;
        --text-muted: #97a5ad;
        --text-eyebrow: #dddddd;
        --hero-track-bg: #111111;
        --dot-color: #ffffff;
        --sim-title-color: #0f172a;
        --sim-desc-color: #4b5563;
        --sim-eyebrow-color: #6b7280;
        --cta-bg: #f4f1eb;
        --cta-color: #141414;
        --focus-ring: rgba(255, 255, 255, 0.7);
        --error-color: #de8489;
    }

    :global(html.light-mode),
    :global([data-theme='light']),
    :global(.light) {
        --bg-main: #ffffff;
        --bg-panel: rgba(0, 0, 0, 0.03);
        --bg-faq: rgba(0, 0, 0, 0.03);
        --bg-input: #f4f5f6;
        --text-main: #1f2933;
        --text-muted: #52606a;
        --text-eyebrow: #52606a;
        --hero-track-bg: #ffffff;
        --dot-color: #111111;
        --sim-title-color: #ffffff;
        --sim-desc-color: #4b5563;
        --sim-eyebrow-color: #6b7280;
        --cta-bg: #111827;
        --cta-color: #ffffff;
        --focus-ring: rgba(17, 24, 39, 0.7);
        --error-color: #c95158;
    }

    :global(html) {
        scrollbar-width: none;
    }
    :global(html::-webkit-scrollbar) {
        display: none;
    }

    :global(body) {
        margin: 0;
        background: var(--bg-main);
        color: var(--text-main);
        font-family: 'Inter Variable', Inter, sans-serif;
        font-size: 16px;
        font-weight: 300;
        overflow-x: hidden;
        transition: background-color 300ms ease, color 300ms ease;
    }

    button:focus,
    input:focus,
    textarea:focus,
    .accordion-panel:focus {
        outline: none;
    }

    button:focus-visible,
    input:focus-visible,
    textarea:focus-visible,
    a:focus-visible,
    .accordion-panel:focus-visible {
        outline: 2px solid var(--focus-ring);
        outline-offset: 2px;
    }

    .landing {
        min-height: 100vh;
        background: var(--bg-main);
        transition: background-color 300ms ease;
    }

    .scroll-dot {
        position: fixed;
        top: calc(50% - 60px);
        right: clamp(12px, 2vw, 28px);
        width: 7px;
        height: 7px;
        border-radius: 50%;
        background: var(--text-main);
        transform: translateY(calc(var(--scroll-progress) * 120px));
        pointer-events: none;
        z-index: 50;
        transition: background-color 300ms ease;
    }

    .hero-scroll-track {
        position: relative;
        width: 100%;
        height: 250vh;
        background: var(--hero-track-bg);
        transition: background-color 300ms ease;
    }

    .hero-sticky-screen {
        position: relative;
        width: 100%;
        height: 100vh;
        display: flex;
        align-items: center;
        justify-content: center;
        overflow: hidden;
    }

    .hero-dot-scale-box {
        position: absolute;
        top: 50%;
        left: 50%;
        width: 28px;
        height: 28px;
        margin-left: -14px;
        margin-top: -14px;
        border-radius: 50%;
        pointer-events: none;
        z-index: 2;
        transform-origin: center center;
        will-change: transform;
    }

    .hero-dot {
        width: 100%;
        height: 100%;
        border-radius: 50%;
        background: var(--dot-color);
        animation: pulse-dot 1.8s ease-in-out infinite;
        transition: background-color 300ms ease;
    }

    @keyframes pulse-dot {
        0%, 100% { opacity: 1; }
        50% { opacity: 0.35; }
    }

    .hero-scroll-hint {
        position: absolute;
        bottom: 36px;
        left: 50%;
        transform: translateX(-50%);
        display: flex;
        flex-direction: column;
        align-items: center;
        gap: 6px;
        font-size: 0.72rem;
        letter-spacing: 0.12em;
        text-transform: uppercase;
        color: var(--text-muted);
        z-index: 3;
        pointer-events: none;
    }

    .hint-icon {
        font-size: 16px !important;
        animation: bob 1.6s ease-in-out infinite;
    }

    @keyframes bob {
        0%, 100% { transform: translateY(0); }
        50% { transform: translateY(5px); }
    }

    .sim-content {
        position: relative;
        z-index: 5;
        max-width: 820px;
        padding: 0 24px;
        text-align: center;
        opacity: 0;
        pointer-events: auto;
    }

    .sim-eyebrow {
        margin: 0 0 16px;
        font-size: 0.8rem;
        letter-spacing: 0.18em;
        text-transform: uppercase;
        color: var(--sim-eyebrow-color);
        font-weight: 400;
        transition: color 300ms ease;
    }

    .sim-title {
        margin: 0 0 24px;
        font-size: clamp(2rem, 5vw, 3.6rem);
        font-weight: 500;
        line-height: 1.1;
        letter-spacing: -0.02em;
        text-transform: uppercase;
        color: var(--sim-title-color);
        transition: color 300ms ease;
    }

    .features {
        padding: 80px clamp(24px, 8vw, 120px) 110px;
        background: var(--bg-main);
        scroll-margin-top: 76px;
        transition: background-color 300ms ease;
    }

    .features h2 {
        margin: 0 auto 60px;
        text-align: center;
        font-size: 0.95rem;
        font-weight: 300;
        letter-spacing: 0.18em;
        text-transform: uppercase;
        color: var(--text-eyebrow);
        transition: color 300ms ease;
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
        display: flex;
        align-items: center;
        justify-content: center;
        min-width: 0;
        flex: 1 1 0%;
        cursor: pointer;
        overflow: hidden;
        background: var(--bg-panel);
        border-radius: 14px;
        transform-style: preserve-3d;
        transform-origin: center;
        will-change: flex-grow, transform;
        transition: background-color 300ms ease;
    }

    .panel-content {
        position: relative;
        width: 100%;
        height: 100%;
        padding: 36px 28px;
        box-sizing: border-box;
        display: flex;
        flex-direction: column;
        justify-content: space-between;
    }

    .panel-number {
        font-size: 0.82rem;
        letter-spacing: 0.12em;
        color: var(--text-muted);
    }

    .label-content {
        opacity: 0;
        display: flex;
        flex-direction: column;
        gap: 12px;
    }

    .label-content h3 {
        margin: 0;
        font-size: 1.25rem;
        font-weight: 400;
        letter-spacing: 0.04em;
        text-transform: uppercase;
        color: var(--text-main);
    }

    .label-content p {
        margin: 0;
        font-size: 0.92rem;
        color: var(--text-muted);
        line-height: 1.55;
        max-width: 40ch;
    }

    .faq {
        padding: 90px clamp(24px, 8vw, 120px);
        background: var(--bg-main);
        transition: background-color 300ms ease;
    }

    .faq-eyebrow {
        text-align: center;
        margin: 0 0 40px;
        color: var(--text-eyebrow);
        letter-spacing: 0.18em;
        font-size: 0.85rem;
        text-transform: uppercase;
    }

    .faq-list {
        max-width: 800px;
        margin: 0 auto;
        display: flex;
        flex-direction: column;
        gap: 14px;
    }

    .faq-item {
        border-radius: 12px;
        background: var(--bg-faq);
        overflow: hidden;
        transition: background-color 300ms ease;
    }

    .faq-trigger {
        width: 100%;
        padding: 20px 26px;
        display: flex;
        justify-content: space-between;
        align-items: center;
        background: none;
        border: 0;
        color: var(--text-main);
        font-size: 0.95rem;
        cursor: pointer;
        border-radius: 12px;
    }

    .faq-icon {
        font-size: 1.4rem;
        margin-left: 16px;
        transition: transform 300ms ease;
    }

    .faq-item.is-open .faq-icon {
        transform: rotate(45deg);
    }

    .faq-answer-wrapper {
        height: 0;
        opacity: 0;
        overflow: hidden;
    }

    .faq-answer-inner {
        padding: 0 26px 20px;
    }

    .faq-answer-inner p {
        margin: 0;
        color: var(--text-muted);
        line-height: 1.6;
        font-size: 0.88rem;
    }

    .contact {
        padding: 90px clamp(24px, 8vw, 120px);
        background: var(--bg-main);
        transition: background-color 300ms ease;
    }

    .contact-eyebrow {
        text-align: center;
        margin: 0 0 40px;
        color: var(--text-eyebrow);
        letter-spacing: 0.18em;
        font-size: 0.85rem;
        text-transform: uppercase;
    }

    .contact-form {
        max-width: 580px;
        margin: 0 auto;
        display: flex;
        flex-direction: column;
        gap: 18px;
    }

    .form-group {
        display: flex;
        flex-direction: column;
        gap: 6px;
    }

    .form-group label {
        font-size: 0.72rem;
        letter-spacing: 0.08em;
        text-transform: uppercase;
        color: var(--text-muted);
    }

    .form-group input,
    .form-group textarea {
        width: 100%;
        padding: 12px 16px;
        border-radius: 8px;
        border: 1px solid transparent;
        background: var(--bg-input);
        color: var(--text-main);
        font-family: inherit;
        font-size: 0.9rem;
        box-sizing: border-box;
        transition: background-color 300ms ease, color 300ms ease, border-color 300ms ease;
    }

    .form-group input[aria-invalid='true'],
    .form-group textarea[aria-invalid='true'] {
        border-color: var(--error-color);
    }

    .field-error-msg {
        font-size: 0.74rem;
        color: var(--error-color);
        letter-spacing: 0.02em;
    }

    .cta {
        display: inline-flex;
        align-items: center;
        justify-content: center;
        border: 0;
        border-radius: 8px;
        padding: 12px 20px;
        font-size: 0.74rem;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        cursor: pointer;
        transition: background-color 300ms ease, color 300ms ease, opacity 150ms ease;
    }

    .cta-primary {
        background: var(--cta-bg);
        color: var(--cta-color);
    }

    .cta-primary:hover {
        opacity: 0.9;
    }

    footer {
        padding: 36px clamp(24px, 8vw, 120px);
        background: var(--bg-main);
        border-top: 1px solid rgba(128, 128, 128, 0.15);
        transition: background-color 300ms ease;
    }

    .footer-inner {
        max-width: 1200px;
        margin: 0 auto;
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 20px;
    }

    .copyright,
    .footer-link {
        color: var(--text-muted);
        font-size: 0.8rem;
        text-decoration: none;
        border-radius: 4px;
    }

    .modal-backdrop {
        position: fixed;
        inset: 0;
        z-index: 200;
        background: rgba(0, 0, 0, 0.55);
        backdrop-filter: blur(4px);
        display: flex;
        align-items: center;
        justify-content: center;
        padding: 20px;
    }

    .modal-card {
        position: relative;
        width: 100%;
        max-width: 440px;
    }

    .modal-close {
        position: absolute;
        top: 18px;
        right: 28px;
        z-index: 20;
        background: none;
        border: 0;
        color: var(--text-muted);
        display: flex;
        align-items: center;
        justify-content: center;
        width: 28px;
        height: 28px;
        border-radius: 6px;
        cursor: pointer;
        padding: 0;
        transition: color 150ms ease, background-color 150ms ease;
    }

    .modal-close:hover {
        color: var(--text-main);
        background: rgba(255, 255, 255, 0.08);
    }

    .material-symbols-outlined {
        font-family: 'Material Symbols Outlined' !important;
        font-weight: normal;
        font-style: normal;
        font-size: 20px;
        line-height: 1;
        display: inline-block;
        white-space: nowrap;
        direction: ltr;
        -webkit-font-smoothing: antialiased;
        font-feature-settings: 'liga';
        font-variation-settings: 'FILL' 0, 'wght' 200, 'GRAD' 0, 'opsz' 24;
        user-select: none;
    }
</style>