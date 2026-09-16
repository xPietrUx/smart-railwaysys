<script lang="ts">
    import { createEventDispatcher } from 'svelte';

    export let mode: 'login' | 'register';
    export let error: string | undefined = undefined;
    export let email = '';

    const dispatch = createEventDispatcher();

    $: register = mode === 'register';

    let formElement: HTMLFormElement;
    let password = '';
    let passwordConfirm = '';

    let emailTouched = false;
    let passwordTouched = false;
    let confirmTouched = false;

    let formSubmittedAttempt = false;
    let formStatus: 'idle' | 'submitting' | 'success' = 'idle';

    $: isEmailValid = /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email.trim());
    $: isPasswordValid = password.length >= 8;
    $: isConfirmValid = !register || (password === passwordConfirm && passwordConfirm.length >= 8);

    $: showEmailError = (emailTouched || formSubmittedAttempt) && !isEmailValid;
    $: showPasswordError = (passwordTouched || formSubmittedAttempt) && !isPasswordValid;
    $: showConfirmError = register && (confirmTouched || formSubmittedAttempt) && !isConfirmValid;

    function toggleMode(e: Event) {
        e.preventDefault();
        mode = register ? 'login' : 'register';
        error = undefined;
        emailTouched = false;
        passwordTouched = false;
        confirmTouched = false;
        formSubmittedAttempt = false;
        password = '';
        passwordConfirm = '';
        formStatus = 'idle';
    }

    function handleSubmit(e: SubmitEvent) {
        formSubmittedAttempt = true;

        if (!isEmailValid || !isPasswordValid || (register && !isConfirmValid)) {
            e.preventDefault();
            return;
        }

        formStatus = 'submitting';
    }

    function handleGuestSubmit(e: MouseEvent) {
        e.preventDefault();
        if (!formElement || formStatus !== 'idle') return;
        formStatus = 'submitting';
        formElement.action = '/?/guest';
        formElement.noValidate = true;
        formElement.submit();
    }
</script>

<svelte:head>
    <link
        rel="stylesheet"
        href="https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined:opsz,wght,FILL,GRAD@20..48,100..700,0..1,-50..200"
    />
</svelte:head>

<section class="card" aria-labelledby="auth-heading">
    <h1 id="auth-heading">{register ? 'REJESTRACJA' : 'LOGOWANIE'}</h1>
    <p class="subtitle">
        {register ? 'MASZ JUŻ KONTO?' : 'NIE POSIADASZ KONTA?'}
        <button
            type="button"
            class="switch-mode-btn"
            on:click={toggleMode}
            tabindex="0"
        >
            {register ? 'ZALOGUJ SIĘ' : 'ZAREJESTRUJ SIĘ'}
        </button>
    </p>

    {#if error}
        <div class="global-err" role="alert" aria-live="assertive">
            <span class="material-symbols-outlined err-icon" aria-hidden="true">error</span>
            <span>{error}</span>
        </div>
    {/if}

    <form
        bind:this={formElement}
        method="POST"
        action={register ? '/rejestracja?/register' : '/login?/login'}
        on:submit={handleSubmit}
        novalidate
        aria-busy={formStatus === 'submitting'}
    >
        <div class="form-group">
            <label for="auth-email">E-MAIL</label>
            <div class="input-wrapper">
                <input
                    id="auth-email"
                    name="email"
                    type="email"
                    autocomplete="email"
                    bind:value={email}
                    on:blur={() => (emailTouched = true)}
                    on:input={() => {
                        if (error) error = undefined;
                    }}
                    class:is-invalid={showEmailError}
                    class:is-valid={emailTouched && isEmailValid}
                    placeholder="operator@smartrailway.pl"
                    disabled={formStatus !== 'idle'}
                    aria-invalid={showEmailError}
                    aria-describedby={showEmailError ? 'email-error' : undefined}
                    required
                    tabindex="0"
                />
                {#if emailTouched && isEmailValid}
                    <span class="material-symbols-outlined input-feedback ok" aria-hidden="true">check</span>
                {/if}
            </div>
            {#if showEmailError}
                <span id="email-error" class="field-error-msg" role="alert">
                    Wprowadź poprawny adres e-mail.
                </span>
            {/if}
        </div>

        <div class="form-group">
            <label for="auth-password">HASŁO</label>
            <div class="input-wrapper">
                <input
                    id="auth-password"
                    name="password"
                    type="password"
                    autocomplete={register ? 'new-password' : 'current-password'}
                    bind:value={password}
                    on:blur={() => (passwordTouched = true)}
                    on:input={() => {
                        if (error) error = undefined;
                    }}
                    class:is-invalid={showPasswordError}
                    class:is-valid={passwordTouched && isPasswordValid}
                    placeholder="Minimum 8 znaków"
                    disabled={formStatus !== 'idle'}
                    aria-invalid={showPasswordError}
                    aria-describedby={showPasswordError ? 'password-error' : undefined}
                    required
                    tabindex="0"
                />
                {#if passwordTouched && isPasswordValid}
                    <span class="material-symbols-outlined input-feedback ok" aria-hidden="true">check</span>
                {/if}
            </div>
            {#if showPasswordError}
                <span id="password-error" class="field-error-msg" role="alert">
                    Hasło musi mieć co najmniej 8 znaków.
                </span>
            {/if}
        </div>

        {#if register}
            <div class="form-group">
                <label for="auth-confirm">POWTÓRZ HASŁO</label>
                <div class="input-wrapper">
                    <input
                        id="auth-confirm"
                        name="passwordConfirm"
                        type="password"
                        autocomplete="new-password"
                        bind:value={passwordConfirm}
                        on:blur={() => (confirmTouched = true)}
                        on:input={() => {
                            confirmTouched = true;
                            if (error) error = undefined;
                        }}
                        class:is-invalid={showConfirmError}
                        class:is-valid={confirmTouched && isConfirmValid && passwordConfirm.length >= 8}
                        placeholder="Powtórz hasło"
                        disabled={formStatus !== 'idle'}
                        aria-invalid={showConfirmError}
                        aria-describedby={showConfirmError ? 'confirm-error' : undefined}
                        required
                        tabindex="0"
                    />
                    {#if confirmTouched && isConfirmValid && passwordConfirm.length >= 8}
                        <span class="material-symbols-outlined input-feedback ok" aria-hidden="true">check</span>
                    {/if}
                </div>
                {#if showConfirmError}
                    <span id="confirm-error" class="field-error-msg" role="alert">
                        Hasła muszą być identyczne.
                    </span>
                {/if}
            </div>
        {/if}

        <div class="submit-row">
            <button
                class="submit-btn"
                class:is-submitting={formStatus === 'submitting'}
                class:is-success={formStatus === 'success'}
                type="submit"
                disabled={formStatus !== 'idle'}
                tabindex="0"
            >
                {#if formStatus === 'submitting'}
                    <span class="loading-spinner" aria-hidden="true"></span>
                    <span>TRWA WYSYŁANIE...</span>
                {:else if formStatus === 'success'}
                    <span class="material-symbols-outlined btn-icon" aria-hidden="true">check</span>
                    <span>{register ? 'KONTO UTWORZONE!' : 'ZALOGOWANO!'}</span>
                {:else}
                    <span>{register ? 'STWÓRZ KONTO' : 'ZALOGUJ SIĘ'}</span>
                {/if}
            </button>

            <button
                class="guest-btn"
                type="button"
                on:click={handleGuestSubmit}
                disabled={formStatus !== 'idle'}
                tabindex="0"
            >
                KONTYNUUJ<br />JAKO GOŚĆ
            </button>
        </div>
    </form>
</section>

<style>
    .material-symbols-outlined {
        font-family: 'Material Symbols Outlined' !important;
        font-weight: normal;
        font-style: normal;
        font-size: 18px;
        line-height: 1;
        display: inline-block;
        white-space: nowrap;
        direction: ltr;
        -webkit-font-smoothing: antialiased;
        font-feature-settings: 'liga';
        font-variation-settings: 'FILL' 0, 'wght' 200, 'GRAD' 0, 'opsz' 24;
        user-select: none;
        vertical-align: middle;
    }

    .card {
        position: relative;
        width: min(440px, calc(100vw - 36px));
        box-sizing: border-box;
        padding: 44px 40px 38px;
        background: #141414;
        border: 0;
        border-radius: 16px;
        box-shadow: 0 24px 64px rgba(0, 0, 0, 0.65);
        text-align: center;
        font-family: 'Inter Variable', Inter, sans-serif;
        color: #f5f7f8;
        transition: background-color 200ms ease, box-shadow 200ms ease, color 200ms ease;
    }

    :global(html.light-mode) .card,
    :global([data-theme='light']) .card,
    :global(.light) .card {
        background: #ffffff;
        color: #111827;
        box-shadow: 0 24px 64px rgba(0, 0, 0, 0.08);
    }

    .card h1 {
        text-transform: uppercase;
        letter-spacing: 0.08em;
        font-size: 1.15rem;
        font-weight: 400;
        margin: 0 0 6px;
        color: inherit;
    }

    .subtitle {
        margin: 0 0 26px;
        color: #87979f;
        font-size: 0.7rem;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        font-weight: 300;
        display: flex;
        align-items: center;
        justify-content: center;
        gap: 6px;
    }

    :global(html.light-mode) .subtitle,
    :global([data-theme='light']) .subtitle,
    :global(.light) .subtitle {
        color: #64748b;
    }

    .switch-mode-btn {
        background: none;
        border: 0;
        padding: 0;
        color: #f5f7f8;
        font: inherit;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        font-weight: 400;
        text-decoration: underline;
        text-underline-offset: 3px;
        cursor: pointer;
        transition: opacity 150ms ease;
    }

    :global(html.light-mode) .switch-mode-btn,
    :global([data-theme='light']) .switch-mode-btn,
    :global(.light) .switch-mode-btn {
        color: #111827;
    }

    .switch-mode-btn:hover {
        opacity: 0.7;
    }

    .switch-mode-btn:focus-visible {
        outline: 2px solid rgba(255, 255, 255, 0.6);
        outline-offset: 3px;
        border-radius: 2px;
    }

    :global(html.light-mode) .switch-mode-btn:focus-visible {
        outline-color: rgba(17, 24, 39, 0.6);
    }

    /* Błąd globalny */
    .global-err {
        display: flex;
        align-items: center;
        justify-content: center;
        gap: 8px;
        padding: 10px 14px;
        border-radius: 8px;
        background: rgba(222, 132, 137, 0.12);
        color: #de8489;
        font-size: 0.74rem;
        font-weight: 300;
        letter-spacing: 0.04em;
        text-transform: uppercase;
        margin-bottom: 20px;
    }

    :global(html.light-mode) .global-err {
        background: rgba(201, 81, 88, 0.1);
        color: #c95158;
    }

    .err-icon {
        font-size: 18px;
        flex-shrink: 0;
    }

    form {
        text-align: left;
        display: flex;
        flex-direction: column;
        gap: 16px;
    }

    .form-group {
        display: flex;
        flex-direction: column;
        gap: 6px;
    }

    .form-group label {
        text-transform: uppercase;
        letter-spacing: 0.08em;
        color: #87979f;
        font-size: 0.68rem;
        font-weight: 300;
    }

    :global(html.light-mode) .form-group label,
    :global([data-theme='light']) .form-group label,
    :global(.light) .form-group label {
        color: #64748b;
    }

    .input-wrapper {
        position: relative;
        display: flex;
        align-items: center;
    }

    .form-group input {
        width: 100%;
        padding: 12px 38px 12px 14px;
        border-radius: 8px;
        border: 0;
        background: #1c1c1c;
        color: #f5f7f8;
        font-family: inherit;
        font-size: 0.85rem;
        font-weight: 300;
        letter-spacing: 0.02em;
        box-sizing: border-box;
        outline: none;
        transition: background-color 150ms ease, box-shadow 150ms ease;
    }

    :global(html.light-mode) .form-group input,
    :global([data-theme='light']) .form-group input,
    :global(.light) .form-group input {
        background: #f4f5f6;
        color: #111827;
    }

    .form-group input::placeholder {
        color: #55626b;
        font-weight: 300;
    }

    :global(html.light-mode) .form-group input::placeholder {
        color: #94a3b8;
    }

    .form-group input:focus-visible {
        box-shadow: inset 0 0 0 1px rgba(255, 255, 255, 0.4);
    }

    :global(html.light-mode) .form-group input:focus-visible {
        box-shadow: inset 0 0 0 1px rgba(17, 24, 39, 0.4);
    }

    .form-group input.is-invalid {
        background: rgba(222, 132, 137, 0.12) !important;
        box-shadow: inset 0 0 0 1px rgba(222, 132, 137, 0.5) !important;
        color: #de8489;
    }

    :global(html.light-mode) .form-group input.is-invalid {
        background: rgba(201, 81, 88, 0.08) !important;
        box-shadow: inset 0 0 0 1px rgba(201, 81, 88, 0.5) !important;
        color: #c95158;
    }

    .form-group input.is-valid {
        box-shadow: inset 0 0 0 1px rgba(108, 176, 159, 0.35);
    }

    .form-group input:disabled {
        opacity: 0.5;
        cursor: not-allowed;
    }

    .input-feedback {
        position: absolute;
        right: 12px;
        pointer-events: none;
    }

    .input-feedback.ok {
        color: #6cb09f;
        font-size: 17px;
    }

    .field-error-msg {
        font-size: 0.68rem;
        color: #de8489;
        font-weight: 300;
        letter-spacing: 0.02em;
        text-transform: uppercase;
    }

    :global(html.light-mode) .field-error-msg {
        color: #c95158;
    }

    .submit-row {
        display: flex;
        flex-direction: row-reverse;
        align-items: center;
        justify-content: space-between;
        gap: 16px;
        margin-top: 10px;
    }

    .submit-btn {
        display: inline-flex;
        align-items: center;
        justify-content: center;
        gap: 8px;
        border: 0;
        border-radius: 8px;
        background: #f4f1eb;
        color: #141414;
        padding: 12px 20px;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        font-weight: 400;
        font-size: 0.72rem;
        cursor: pointer;
        transition: opacity 150ms ease, transform 120ms ease, background-color 200ms ease;
    }

    :global(html.light-mode) .submit-btn,
    :global([data-theme='light']) .submit-btn,
    :global(.light) .submit-btn {
        background: #111827;
        color: #ffffff;
    }

    .submit-btn:hover:not(:disabled) {
        opacity: 0.85;
        transform: translateY(-1px);
    }

    .submit-btn:active:not(:disabled) {
        transform: translateY(0);
        opacity: 0.7;
    }

    .submit-btn:focus-visible {
        outline: 2px solid rgba(255, 255, 255, 0.6);
        outline-offset: 3px;
    }

    :global(html.light-mode) .submit-btn:focus-visible {
        outline-color: rgba(17, 24, 39, 0.6);
    }

    .submit-btn:disabled {
        opacity: 0.4;
        cursor: default;
    }

    .submit-btn.is-submitting {
        cursor: wait;
        opacity: 0.75;
    }

    .submit-btn.is-success {
        background: #6cb09f !important;
        color: #141414 !important;
        opacity: 1;
    }

    .btn-icon {
        font-size: 16px;
    }

    .loading-spinner {
        width: 12px;
        height: 12px;
        border: 2px solid rgba(20, 20, 20, 0.25);
        border-top-color: currentColor;
        border-radius: 50%;
        animation: spin 550ms linear infinite;
    }

    :global(html.light-mode) .loading-spinner {
        border-color: rgba(255, 255, 255, 0.3);
        border-top-color: currentColor;
    }

    @keyframes spin {
        to {
            transform: rotate(360deg);
        }
    }

    .guest-btn {
        background: transparent;
        border: 0;
        color: #87979f;
        padding: 4px 6px;
        border-radius: 6px;
        font-weight: 300;
        font-size: 0.68rem;
        line-height: 1.35;
        letter-spacing: 0.08em;
        text-transform: uppercase;
        cursor: pointer;
        text-align: left;
        transition: color 150ms ease, background-color 150ms ease;
    }

    .guest-btn:hover:not(:disabled) {
        color: #f5f7f8;
        background: rgba(255, 255, 255, 0.04);
    }

    :global(html.light-mode) .guest-btn:hover:not(:disabled) {
        color: #111827;
        background: rgba(0, 0, 0, 0.04);
    }

    .guest-btn:focus-visible {
        outline: 2px solid rgba(255, 255, 255, 0.6);
        outline-offset: 2px;
    }

    :global(html.light-mode) .guest-btn:focus-visible {
        outline-color: rgba(17, 24, 39, 0.6);
    }

    .guest-btn:disabled {
        opacity: 0.4;
        cursor: default;
    }

    @media (max-width: 480px) {
        .card {
            padding: 34px 22px;
        }

        .submit-row {
            flex-direction: column;
            align-items: stretch;
            gap: 12px;
        }

        .submit-btn {
            width: 100%;
        }

        .guest-btn {
            text-align: center;
        }
    }
</style>