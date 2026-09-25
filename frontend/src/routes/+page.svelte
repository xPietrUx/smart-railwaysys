<script lang="ts">
    import PublicNav from '$lib/components/site/PublicNav.svelte';
    import AuthCard from '$lib/components/site/AuthCard.svelte';
    import { t } from '$lib/i18n';
    import { tick, onMount } from 'svelte';
    import { slide } from 'svelte/transition';
    import { cubicOut } from 'svelte/easing';
    import { page } from '$app/stores';
    import type { PageData, ActionData } from './$types';

    export let data: PageData;
    export let form: ActionData;

    type ViewSection = 'jak-to-dziala' | 'o-wa-gone' | 'kontakt';
    let currentView: ViewSection = 'o-wa-gone';

    // pliki ascii
    const CUSTOM_ASCII = ['', '', '', ''];

    $: features = [
        {
            id: 'network',
            tag: $t('landing.features.network.title'),
            copy: $t('landing.features.network.copy'),
            ascii: CUSTOM_ASCII[0]
        },
        {
            id: 'incidents',
            tag: $t('landing.features.incidents.title'),
            copy: $t('landing.features.incidents.copy'),
            ascii: CUSTOM_ASCII[1]
        },
        {
            id: 'timetable',
            tag: $t('landing.features.timetable.title'),
            copy: $t('landing.features.timetable.copy'),
            ascii: CUSTOM_ASCII[2]
        },
        {
            id: 'scenarios',
            tag: $t('landing.features.scenarios.title'),
            copy: $t('landing.features.scenarios.copy'),
            ascii: CUSTOM_ASCII[3]
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
        },
        {
            question: 'Jak zintegrować API z zewnętrznym systemem?',
            answer: 'Oferujemy standardowe endpointy REST oraz WebSocket ze strumieniem zdarzeń w czasie rzeczywistym.'
        }
    ];

    let activeFeature = 0;
    let openFaqIndex: number | null = 0;

    function nextFeature() {
        activeFeature = (activeFeature + 1) % features.length;
    }

    function prevFeature() {
        activeFeature = (activeFeature - 1 + features.length) % features.length;
    }

    function toggleFaq(index: number) {
        openFaqIndex = openFaqIndex === index ? null : index;
    }

    $: {
        const hash = $page.url.hash.replace('#', '');
        if (hash === 'jak-to-dziala' || hash === 'o-wa-gone' || hash === 'kontakt') {
            currentView = hash as ViewSection;
        }
    }

    function handleKeydown(e: KeyboardEvent) {
        if (currentView === 'o-wa-gone') {
            if (e.key === 'ArrowRight') nextFeature();
            if (e.key === 'ArrowLeft') prevFeature();
        }
    }

    onMount(() => {
        window.addEventListener('keydown', handleKeydown);
        return () => window.removeEventListener('keydown', handleKeydown);
    });

    let showAuthModal = false;
    let isClosingAuthModal = false;
    let authMode: 'login' | 'register' = 'login';
    let triggerElement: HTMLElement | null = null;
    let modalElement: HTMLElement | null = null;

    async function openAuthModal(mode: 'login' | 'register' = 'login', e?: CustomEvent | MouseEvent) {
        if (e && 'preventDefault' in e && typeof e.preventDefault === 'function') {
            e.preventDefault();
        }
        if (e && 'currentTarget' in e && e.currentTarget) {
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
        }
    }

    let contactName = '';
    let contactEmail = '';
    let contactMessage = '';
    let nameTouched = false;
    let emailTouched = false;
    let messageTouched = false;
    let formSubmittedAttempt = false;
    let formStatus: 'idle' | 'submitting' | 'success' | 'error' = 'idle';

    $: isEmailValid = /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(contactEmail.trim());
    $: isNameValid = contactName.trim().length >= 2;
    $: isMessageValid = contactMessage.trim().length >= 6;

    $: showNameError = (nameTouched || formSubmittedAttempt) && !isNameValid;
    $: showEmailError = (emailTouched || formSubmittedAttempt) && !isEmailValid;
    $: showMessageError = (messageTouched || formSubmittedAttempt) && !isMessageValid;

    function handleSubmitContact(event: SubmitEvent) {
        event.preventDefault();
        formSubmittedAttempt = true;

        if (!isNameValid || !isEmailValid || !isMessageValid) {
            formStatus = 'error';
            return;
        }

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
            setTimeout(() => {
                if (formStatus === 'success') formStatus = 'idle';
            }, 4500);
        }, 800);
    }
</script>

<svelte:head>
    <link
        rel="stylesheet"
        href="https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined:opsz,wght,FILL,GRAD@20..48,100..700,0..1,-50..200"
    />
    <title>{$t('landing.head.title')}</title>
</svelte:head>

<div class="landing-viewport">
    <PublicNav authenticated={data.authenticated} on:openLogin={() => openAuthModal('login')} />

    <main class="viewport-stage" aria-hidden={showAuthModal}>
        {#if currentView === 'jak-to-dziala'}
            <section class="screen-view empty-screen">
                <!-- Sekcja pusta / początkowa makiety -->
            </section>
        {:else if currentView === 'o-wa-gone'}
            <section class="screen-view about-screen">
                <div class="about-grid">
                    <!-- Lewa strona: FAQ -->
                    <div class="faq-column">
                        <h2 class="column-title">FAQ</h2>
                        <div class="faq-accordion">
                            {#each faqItems as item, idx}
                                <div class="faq-card" class:is-expanded={openFaqIndex === idx}>
                                    <button 
                                        type="button" 
                                        class="faq-head" 
                                        on:click={() => toggleFaq(idx)}
                                        aria-expanded={openFaqIndex === idx}
                                    >
                                        <span>{item.question}</span>
                                    </button>
                                    {#if openFaqIndex === idx}
                                        <div 
                                            class="faq-body" 
                                            transition:slide={{ duration: 250, easing: cubicOut }}
                                        >
                                            <p>{item.answer}</p>
                                        </div>
                                    {/if}
                                </div>
                            {/each}
                        </div>
                    </div>

                    <!-- Prawa strona: Features ze sliderem -->
                    <div class="features-column">
                        <div class="feature-card">
                            <div class="ascii-container" aria-hidden="true">
                                <pre class="ascii-art">{features[activeFeature].ascii}</pre>
                            </div>
                            
                            <div class="feature-footer">
                                <p class="feature-desc">
                                    <strong>{features[activeFeature].tag}</strong> {features[activeFeature].copy}
                                </p>
                            </div>

                            <button 
                                type="button" 
                                class="slider-arrow next-btn" 
                                on:click={nextFeature}
                                aria-label="Następna funkcja"
                                title="Następna funkcja"
                            >
                                <span class="dot-indicator"></span>
                            </button>
                        </div>
                    </div>
                </div>
            </section>
        {:else if currentView === 'kontakt'}
            <section class="screen-view contact-screen">
                <div class="contact-card">
                    <h2 class="column-title">KONTAKT</h2>
                    <form class="contact-form" on:submit={handleSubmitContact} novalidate>
                        <div class="form-row">
                            <div class="field-wrap">
                                <input
                                    type="text"
                                    class:is-error={showNameError}
                                    bind:value={contactName}
                                    on:blur={() => (nameTouched = true)}
                                    placeholder={$t('landing.contact.namePlaceholder')}
                                    aria-invalid={showNameError ? 'true' : undefined}
                                />
                                {#if showNameError}
                                    <span class="field-hint" role="alert">Wpisz min. 2 znaki</span>
                                {/if}
                            </div>

                            <div class="field-wrap">
                                <input
                                    type="email"
                                    class:is-error={showEmailError}
                                    bind:value={contactEmail}
                                    on:blur={() => (emailTouched = true)}
                                    placeholder={$t('landing.contact.emailPlaceholder')}
                                    aria-invalid={showEmailError ? 'true' : undefined}
                                />
                                {#if showEmailError}
                                    <span class="field-hint" role="alert">Wprowadź poprawny adres e-mail.</span>
                                {/if}
                            </div>
                        </div>

                        <div class="field-wrap">
                            <textarea
                                rows="12"
                                class:is-error={showMessageError}
                                bind:value={contactMessage}
                                on:blur={() => (messageTouched = true)}
                                placeholder={$t('landing.contact.messagePlaceholder')}
                                aria-invalid={showMessageError ? 'true' : undefined}
                            ></textarea>
                            {#if showMessageError}
                                <span class="field-hint" role="alert">Wiadomość musi mieć min. 6 znaków</span>
                            {/if}
                        </div>

                        <div class="form-bottom-row">
                            <div class="feedback-area">
                                {#if formStatus === 'success'}
                                    <span class="feedback-msg success" role="status">
                                        <span class="material-symbols-outlined icon-status">check_circle</span>
                                        {$t('landing.contact.success')}
                                    </span>
                                {:else if formStatus === 'error' && (showNameError || showEmailError || showMessageError)}
                                    <span class="feedback-msg error" role="alert">
                                        <span class="material-symbols-outlined icon-status">error</span>
                                        Uzupełnij poprawnie wszystkie pola
                                    </span>
                                {/if}
                            </div>

                            <button 
                                type="submit" 
                                class="cta-submit" 
                                disabled={formStatus === 'submitting'}
                            >
                                {formStatus === 'submitting' ? 'WYSYŁANIE...' : 'WYŚLIJ WIADOMOŚĆ'}
                            </button>
                        </div>
                    </form>
                </div>
            </section>
        {/if}
    </main>

    <footer class="bottom-bar">
        <span>WA.GONE @2026</span>
    </footer>

    {#if showAuthModal}
        <!-- svelte-ignore a11y_click_events_have_key_events -->
        <div
            class="modal-backdrop"
            class:is-closing={isClosingAuthModal}
            role="dialog"
            tabindex="-1"
            aria-modal="true"
            aria-label={authMode === 'login' ? 'Logowanie' : 'Rejestracja'}
            bind:this={modalElement}
            on:click={handleBackdropClick}
            on:keydown={handleModalKeydown}
        >
            <div class="modal-card">
                <button
                    class="modal-close"
                    type="button"
                    on:click={closeAuthModal}
                    title="Zamknij"
                    aria-label="Zamknij"
                >
                    <span class="material-symbols-outlined" aria-hidden="true">close</span>
                </button>
                <AuthCard mode={authMode} error={form?.error} email={form?.email ?? ''} />
            </div>
        </div>
    {/if}
</div>

<style>
    :global(:root) {
        --viewport-bg: #141414;
        --card-bg: #111111;
        --text-primary: #f5f7f8;
        --text-muted: #838a90;
        --text-heading: #9ea4aa;
        --text-strong: #cfd4d8;
        --ascii-color: #4f5860;
        --input-bg: #0d0d0d;
        --btn-submit-bg: #f3eee7;
        --btn-submit-color: #111111;
        --dot-bg: #e2e2de;
        --footer-color: #4f555b;
        --focus-ring: rgba(255, 255, 255, 0.65);
        --error-color: #de8489;
        --success-color: #6cb09f;
        --backdrop-bg: rgba(0, 0, 0, 0.75);
    }

    :global(html.light-mode) {
        --viewport-bg: #f4f5f3;
        --card-bg: #ffffff;
        --text-primary: #111827;
        --text-muted: #52606a;
        --text-heading: #374151;
        --text-strong: #1f2937;
        --ascii-color: #718096;
        --input-bg: #eaedea;
        --btn-submit-bg: #111827;
        --btn-submit-color: #ffffff;
        --dot-bg: #111827;
        --footer-color: #94a3b8;
        --focus-ring: rgba(17, 24, 39, 0.65);
        --error-color: #c95158;
        --success-color: #2e8570;
        --backdrop-bg: rgba(0, 0, 0, 0.4);
    }

    :global(html, body) {
        margin: 0;
        padding: 0;
        width: 100%;
        height: 100%;
        overflow: hidden !important;
        background-color: var(--viewport-bg);
        color: var(--text-primary);
        font-family: 'Inter Variable', Inter, sans-serif;
        transition: background-color 200ms ease, color 200ms ease;
    }

    .landing-viewport {
        position: relative;
        width: 100vw;
        height: 100vh;
        display: flex;
        flex-direction: column;
        justify-content: space-between;
        background: var(--viewport-bg);
        box-sizing: border-box;
        overflow: hidden;
        transition: background-color 200ms ease;
    }

    .viewport-stage {
        flex: 1;
        position: relative;
        width: 100%;
        max-width: 1440px;
        margin: 0 auto;
        padding: 0 clamp(20px, 4vw, 56px);
        box-sizing: border-box;
        display: flex;
        align-items: center;
        justify-content: center;
        overflow: hidden;
    }

    .screen-view {
        width: 100%;
        height: 100%;
        display: flex;
        align-items: center;
        justify-content: center;
    }

    .about-grid {
        display: grid;
        grid-template-columns: 1fr 1fr;
        gap: 40px;
        width: 100%;
        max-height: 80vh;
        align-items: center;
    }

    .column-title {
        font-size: 0.82rem;
        font-weight: 500;
        letter-spacing: 0.14em;
        text-transform: uppercase;
        color: var(--text-heading);
        margin: 0 0 24px;
        text-align: center;
    }

    .faq-column {
        display: flex;
        flex-direction: column;
        height: 520px;
    }

    .faq-accordion {
        display: flex;
        flex-direction: column;
        gap: 10px;
        overflow-y: auto;
        padding-right: 6px;
    }

    .faq-card {
        background: var(--card-bg);
        border-radius: 12px;
        border: 0;
        box-shadow: none;
        overflow: hidden;
        transition: background-color 200ms ease;
    }

    .faq-head {
        width: 100%;
        background: none;
        border: 0;
        color: var(--text-strong);
        padding: 16px 20px;
        text-align: left;
        font-size: 0.85rem;
        font-family: inherit;
        cursor: pointer;
        display: flex;
        justify-content: space-between;
        align-items: center;
        border-radius: 12px;
        transition: color 150ms ease, background-color 150ms ease;
    }

    .faq-head:focus {
        outline: none;
    }

    .faq-head:focus-visible {
        outline: 2px solid var(--focus-ring);
        outline-offset: -2px;
        border-radius: 10px;
    }

    .faq-head:hover {
        color: var(--text-primary);
    }

    .faq-body {
        padding: 0 20px 18px;
    }

    .faq-body p {
        margin: 0;
        font-size: 0.8rem;
        line-height: 1.55;
        color: var(--text-muted);
    }

    .features-column {
        height: 520px;
        display: flex;
        align-items: center;
    }

    .feature-card {
        position: relative;
        width: 100%;
        height: 100%;
        background: var(--card-bg);
        border-radius: 14px;
        border: 0;
        box-shadow: none;
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: space-between;
        padding: 32px 36px;
        box-sizing: border-box;
        transition: background-color 200ms ease;
    }

    .ascii-container {
        flex: 1;
        display: flex;
        align-items: center;
        justify-content: center;
        width: 100%;
        overflow: hidden;
    }

    .ascii-art {
        margin: 0;
        font-family: 'JetBrains Mono', 'Fira Code', monospace;
        font-size: clamp(8px, 0.85vw, 12px);
        line-height: 1.15;
        color: var(--ascii-color);
        white-space: pre;
        letter-spacing: 0.08em;
        user-select: none;
    }

    .feature-footer {
        width: 100%;
        margin-top: 16px;
    }

    .feature-desc {
        margin: 0;
        font-size: 0.85rem;
        line-height: 1.5;
        color: var(--text-muted);
    }

    .feature-desc strong {
        color: var(--text-strong);
        font-weight: 500;
    }

    .slider-arrow {
        position: absolute;
        top: 50%;
        right: 18px;
        transform: translateY(-50%);
        background: none;
        border: 0;
        cursor: pointer;
        padding: 10px;
        display: flex;
        align-items: center;
        justify-content: center;
        border-radius: 50%;
        transition: opacity 150ms ease;
    }

    .slider-arrow:focus {
        outline: none;
    }

    .slider-arrow:focus-visible {
        outline: 2px solid var(--focus-ring);
        outline-offset: 2px;
    }

    .slider-arrow:hover {
        opacity: 0.75;
    }

    .dot-indicator {
        width: 10px;
        height: 10px;
        border-radius: 50%;
        background: var(--dot-bg);
        transition: background-color 200ms ease, transform 150ms ease;
    }

    .slider-arrow:hover .dot-indicator {
        transform: scale(1.15);
    }

    /* === FORMULARZ KONTAKTOWY === */
    .contact-card {
        width: 100%;
        max-width: 600px;
        box-sizing: border-box;
    }

    .contact-form {
        display: flex;
        flex-direction: column;
        gap: 12px;
    }

    .form-row {
        display: grid;
        grid-template-columns: 1fr 1fr;
        gap: 12px;
    }

    .field-wrap {
        display: flex;
        flex-direction: column;
        gap: 4px;
        width: 100%;
    }

    .contact-form input,
    .contact-form textarea {
        width: 100%;
        padding: 16px 20px;
        border-radius: 12px;
        border: 0 !important;
        box-shadow: none !important;
        background: var(--input-bg);
        color: var(--text-primary);
        font-family: inherit;
        font-size: 0.88rem;
        box-sizing: border-box;
        transition: background-color 200ms ease, color 200ms ease;
    }

    .contact-form textarea {
        resize: none;
        min-height: 240px;
    }

    .contact-form input.is-error,
    .contact-form textarea.is-error {
        background: rgba(222, 132, 137, 0.12) !important;
        color: #de8489 !important;
        border: 0 !important;
        box-shadow: none !important;
    }

    :global(html.light-mode) .contact-form input.is-error,
    :global(html.light-mode) .contact-form textarea.is-error {
        background: rgba(201, 81, 88, 0.12) !important;
        color: #c95158 !important;
    }

    .contact-form input:focus,
    .contact-form textarea:focus {
        outline: none;
    }

    .contact-form input:focus-visible,
    .contact-form textarea:focus-visible {
        outline: 2px solid var(--focus-ring);
        outline-offset: 2px;
    }

    .contact-form input.is-error:focus-visible,
    .contact-form textarea.is-error:focus-visible {
        outline-color: rgba(222, 132, 137, 0.65);
    }

    :global(html.light-mode) .contact-form input.is-error:focus-visible,
    :global(html.light-mode) .contact-form textarea.is-error:focus-visible {
        outline-color: rgba(201, 81, 88, 0.65);
    }

    .field-hint {
        font-size: 0.72rem;
        letter-spacing: 0.04em;
        text-transform: uppercase;
        color: #de8489;
        padding-left: 4px;
        margin-top: 4px;
        font-weight: 400;
    }

    :global(html.light-mode) .field-hint {
        color: #c95158;
    }

    .form-bottom-row {
        display: flex;
        align-items: center;
        justify-content: space-between;
        margin-top: 6px;
        gap: 16px;
    }

    .feedback-area {
        flex: 1;
        min-width: 0;
    }

    .feedback-msg {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        font-size: 0.76rem;
        letter-spacing: 0.04em;
        text-transform: uppercase;
        font-weight: 500;
    }

    .feedback-msg.success {
        color: var(--success-color);
    }

    .feedback-msg.error {
        color: var(--error-color);
    }

    .icon-status {
        font-size: 16px;
    }

    .cta-submit {
        background: var(--btn-submit-bg);
        color: var(--btn-submit-color);
        border: 0;
        box-shadow: none;
        border-radius: 10px;
        padding: 14px 28px;
        font-size: 0.78rem;
        font-weight: 600;
        letter-spacing: 0.06em;
        text-transform: uppercase;
        cursor: pointer;
        font-family: inherit;
        white-space: nowrap;
        transition: opacity 150ms ease, background-color 200ms ease, color 200ms ease;
    }

    .cta-submit:focus {
        outline: none;
    }

    .cta-submit:focus-visible {
        outline: 2px solid var(--focus-ring);
        outline-offset: 2px;
    }

    .cta-submit:hover:not(:disabled) {
        opacity: 0.88;
    }

    .cta-submit:disabled {
        opacity: 0.5;
        cursor: not-allowed;
    }

    .bottom-bar {
        padding: 18px 44px;
        display: flex;
        justify-content: center;
        align-items: center;
        font-size: 0.68rem;
        letter-spacing: 0.1em;
        color: var(--footer-color);
        flex-shrink: 0;
        transition: color 200ms ease;
    }

    .modal-backdrop {
        position: fixed;
        inset: 0;
        z-index: 200;
        background: var(--backdrop-bg);
        backdrop-filter: blur(6px);
        display: flex;
        align-items: center;
        justify-content: center;
        padding: 20px;
        outline: none;
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
        cursor: pointer;
        transition: opacity 150ms ease, color 150ms ease;
    }

    .modal-close:focus-visible {
        outline: 2px solid var(--focus-ring);
        outline-offset: 2px;
        border-radius: 6px;
    }

    .modal-close:hover {
        color: var(--text-primary);
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
        user-select: none;
    }

    @media (max-width: 900px) {
        .about-grid {
            grid-template-columns: 1fr;
            max-height: none;
            overflow-y: auto;
        }

        .features-column,
        .faq-column {
            height: auto;
        }

        .form-row {
            grid-template-columns: 1fr;
        }
    }
</style>