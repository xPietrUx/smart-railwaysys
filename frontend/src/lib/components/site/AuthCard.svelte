<script lang="ts">
	export let mode: 'login' | 'register';
	export let error: string | undefined = undefined;
	export let email = '';

	$: register = mode === 'register';

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

		setTimeout(() => {
			formStatus = 'success';
		}, 1200);
	}
</script>

<section class="card">
	<h1>{register ? 'REJESTRACJA' : 'LOGOWANIE'}</h1>
	<p class="subtitle">
		{register ? 'MASZ JUŻ KONTO?' : 'NIE POSIADASZ KONTA?'}
		<button type="button" class="switch-mode-btn" on:click={toggleMode}>
			{register ? 'ZALOGUJ SIĘ' : 'ZAREJESTRUJ SIĘ'}
		</button>
	</p>

	{#if error || (formSubmittedAttempt && (!isEmailValid || !isPasswordValid || (register && !isConfirmValid)))}
		<div class="error-banner" role="alert">
			<span class="error-icon">!</span>
			<span>{error || 'Sprawdź i uzupełnij poprawnie formularz.'}</span>
		</div>
	{/if}

	<form method="POST" action={register ? '/rejestracja' : '/login'} on:submit={handleSubmit} novalidate>
		<div class="form-group">
			<label for="auth-email">E-MAIL</label>
			<input
				id="auth-email"
				name="email"
				type="email"
				autocomplete="email"
				bind:value={email}
				on:blur={() => (emailTouched = true)}
				class:is-invalid={showEmailError}
				class:is-valid={emailTouched && isEmailValid}
				placeholder="operator@smartrailway.pl"
				disabled={formStatus !== 'idle'}
				required
			/>
			{#if showEmailError}
				<span class="field-error-msg">Wprowadź poprawny adres e-mail.</span>
			{/if}
		</div>

		<div class="form-group">
			<label for="auth-password">HASŁO</label>
			<input
				id="auth-password"
				name="password"
				type="password"
				autocomplete={register ? 'new-password' : 'current-password'}
				bind:value={password}
				on:blur={() => (passwordTouched = true)}
				class:is-invalid={showPasswordError}
				class:is-valid={passwordTouched && isPasswordValid}
				placeholder="Minimum 8 znaków"
				disabled={formStatus !== 'idle'}
				required
			/>
			{#if showPasswordError}
				<span class="field-error-msg">Hasło musi mieć co najmniej 8 znaków.</span>
			{/if}
		</div>

		{#if register}
			<div class="form-group">
				<label for="auth-confirm">POWTÓRZ HASŁO</label>
				<input
					id="auth-confirm"
					name="passwordConfirm"
					type="password"
					autocomplete="new-password"
					bind:value={passwordConfirm}
					on:blur={() => (confirmTouched = true)}
					on:input={() => (confirmTouched = true)}
					class:is-invalid={showConfirmError}
					class:is-valid={confirmTouched && isConfirmValid && passwordConfirm.length >= 8}
					placeholder="Powtórz hasło"
					disabled={formStatus !== 'idle'}
					required
				/>
				{#if showConfirmError}
					<span class="field-error-msg">Hasła muszą być identyczne.</span>
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
			>
				{#if formStatus === 'submitting'}
					<span class="loading-spinner"></span>
					<span>TRWA WYSYŁANIE...</span>
				{:else if formStatus === 'success'}
					<span>✓ {register ? 'KONTO UTWORZONE!' : 'ZALOGOWANO!'}</span>
				{:else}
					<span>{register ? 'STWÓRZ KONTO' : 'ZALOGUJ SIĘ'}</span>
				{/if}
			</button>

			<button
				class="guest-btn"
				type="submit"
				formaction="/?/guest"
				formnovalidate
				disabled={formStatus !== 'idle'}
			>
				KONTYNUUJ<br />JAKO GOŚĆ
			</button>
		</div>
	</form>
</section>

<style>
	.card {
		position: relative;
		width: min(430px, calc(100vw - 40px));
		box-sizing: border-box;
		padding: 42px 42px 38px;
		background: #1b1b1b;
		border: 0;
		border-radius: 18px;
		box-shadow: 0 20px 50px rgba(0, 0, 0, 0.5);
		text-align: center;
		transition: background-color 350ms ease, color 350ms ease;
	}
	:global(html.light-mode) .card {
		background: #ffffff;
		box-shadow: 0 20px 50px rgba(0, 0, 0, 0.15);
	}

	.card h1 {
		text-transform: uppercase;
		letter-spacing: 0.08em;
		font-size: 1.25rem;
		font-weight: 300;
		margin: 0 0 8px;
		color: #ffffff;
	}
	:global(html.light-mode) .card h1 {
		color: #111827;
	}

	.subtitle {
		margin: 0 0 28px;
		color: #87979f;
		font-size: 0.72rem;
		text-transform: uppercase;
		letter-spacing: 0.06em;
		font-weight: 300;
	}
	:global(html.light-mode) .subtitle {
		color: #6b7280;
	}

	.switch-mode-btn {
		background: none;
		border: 0;
		padding: 0;
		margin-left: 4px;
		color: #ffffff;
		font: inherit;
		text-transform: uppercase;
		letter-spacing: 0.06em;
		text-decoration: underline;
		cursor: pointer;
		transition: opacity 180ms ease;
	}
	:global(html.light-mode) .switch-mode-btn {
		color: #111827;
	}
	.switch-mode-btn:hover {
		opacity: 0.65;
	}

	.error-banner {
		display: flex;
		align-items: center;
		gap: 10px;
		padding: 12px 14px;
		border-radius: 9px;
		background: rgba(239, 68, 68, 0.15);
		border-left: 3px solid #ef4444;
		color: #fca5a5;
		font-size: 0.82rem;
		font-weight: 300;
		margin-bottom: 20px;
		text-align: left;
		animation: shake 300ms ease-in-out;
	}
	:global(html.light-mode) .error-banner {
		background: #fee2e2;
		color: #991b1b;
	}
	.error-icon {
		display: grid;
		place-items: center;
		width: 18px;
		height: 18px;
		border-radius: 50%;
		background: #ef4444;
		color: #fff;
		font-size: 0.7rem;
		font-weight: 700;
		flex-shrink: 0;
	}

	@keyframes shake {
		0%, 100% { transform: translateX(0); }
		20%, 60% { transform: translateX(-4px); }
		40%, 80% { transform: translateX(4px); }
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
		font-size: 0.7rem;
		font-weight: 300;
	}
	:global(html.light-mode) .form-group label {
		color: #52606a;
	}

	.form-group input {
		width: 100%;
		padding: 12px 16px;
		border-radius: 9px;
		border: 1.5px solid transparent;
		background: rgba(255, 255, 255, 0.05);
		color: #f5f7f8;
		font-family: inherit;
		font-size: 0.95rem;
		font-weight: 300;
		box-sizing: border-box;
		outline: none;
		transition: border-color 200ms ease, background-color 200ms ease, box-shadow 200ms ease;
	}
	:global(html.light-mode) .form-group input {
		background: #e5e7eb;
		color: #1f2933;
	}

	.form-group input.is-invalid {
		border-color: #ef4444 !important;
		background: rgba(239, 68, 68, 0.06) !important;
		box-shadow: 0 0 0 3px rgba(239, 68, 68, 0.15);
	}
	:global(html.light-mode) .form-group input.is-invalid {
		background: #fef2f2 !important;
	}

	.form-group input.is-valid {
		border-color: #22c55e !important;
		background: rgba(34, 197, 94, 0.04) !important;
	}
	:global(html.light-mode) .form-group input.is-valid {
		background: #f0fdf4 !important;
	}

	.field-error-msg {
		font-size: 0.78rem;
		color: #fca5a5;
		font-weight: 300;
	}
	:global(html.light-mode) .field-error-msg {
		color: #dc2626;
	}

	.submit-row {
		display: flex;
		flex-direction: row-reverse;
		align-items: center;
		justify-content: space-between;
		gap: 16px;
		margin-top: 12px;
	}

	.submit-btn {
		display: inline-flex;
		align-items: center;
		justify-content: center;
		gap: 8px;
		border: 0;
		border-radius: 9px;
		background: #f4f1eb;
		color: #171717;
		padding: 12px 20px;
		text-transform: uppercase;
		letter-spacing: 0.07em;
		font-weight: 300;
		font-size: 0.72rem;
		cursor: pointer;
		transition: opacity 180ms ease, background-color 300ms ease, color 300ms ease;
	}
	:global(html.light-mode) .submit-btn {
		background: #111827;
		color: #ffffff;
	}
	.submit-btn:hover:not(:disabled) {
		opacity: 0.75;
	}
	.submit-btn.is-submitting {
		opacity: 0.7;
		cursor: wait;
	}
	.submit-btn.is-success {
		background: #22c55e !important;
		color: #ffffff !important;
		opacity: 1;
	}

	.loading-spinner {
		width: 12px;
		height: 12px;
		border: 2px solid rgba(0, 0, 0, 0.2);
		border-top-color: currentColor;
		border-radius: 50%;
		animation: spin 600ms linear infinite;
	}
	@keyframes spin {
		to { transform: rotate(360deg); }
	}

	.guest-btn {
		background: transparent;
		border: 0;
		color: #87979f;
		padding: 0;
		font-weight: 300;
		font-size: 0.72rem;
		line-height: 1.35;
		letter-spacing: 0.07em;
		text-transform: uppercase;
		cursor: pointer;
		text-align: left;
		transition: color 200ms ease;
	}
	.guest-btn:hover {
		color: #ffffff;
	}
	:global(html.light-mode) .guest-btn:hover {
		color: #111827;
	}

	@media (max-width: 480px) {
		.card {
			padding: 34px 24px;
		}
		.submit-row {
			align-items: stretch;
			flex-direction: column;
		}
		.submit-btn {
			width: 100%;
		}
		.guest-btn {
			text-align: center;
		}
	}
</style>