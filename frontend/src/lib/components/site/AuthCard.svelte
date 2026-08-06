<script lang="ts">
	export let mode: 'login' | 'register';
	export let error: string | undefined = undefined;
	export let email = '';
	const register = mode === 'register';
	let password = '';
	let passwordConfirm = '';
	let confirmTouched = false;
	$: passwordsMismatch = register && confirmTouched && password !== passwordConfirm;
</script>

<section class="card">
	<h1>{register ? 'Rejestracja' : 'Logowanie'}</h1>
	<p>
		{register ? 'Masz już konto?' : 'Nie posiadasz konta?'}
		<a href={register ? '/login' : '/rejestracja'}>{register ? 'Zaloguj się' : 'Zarejestruj się'}</a
		>
	</p>
	{#if error}<div class="error" role="alert">{error}</div>{/if}
	<form method="POST" action={register ? '?/register' : '?/login'}>
		<label
			>E-mail<input
				name="email"
				type="email"
				autocomplete="email"
				value={email}
				placeholder="operator@smartrailway.pl"
				required
			/></label
		>
		<label
			>Hasło<input
				name="password"
				type="password"
				autocomplete={register ? 'new-password' : 'current-password'}
				minlength="8"
				placeholder="Minimum 8 znaków"
				required
				bind:value={password}
			/></label
		>
		{#if register}<label
				>Powtórz hasło<input
					name="passwordConfirm"
					type="password"
					autocomplete="new-password"
					minlength="8"
					required
					bind:value={passwordConfirm}
					on:input={() => (confirmTouched = true)}
					aria-invalid={passwordsMismatch}
					aria-describedby="password-feedback"
				/></label
			>{/if}
		{#if register}<p
				id="password-feedback"
				class:mismatch={passwordsMismatch}
				class="password-feedback"
				aria-live="polite"
			>
				{#if passwordsMismatch}Hasła nie są takie same.{:else if confirmTouched && passwordConfirm}Hasła
					są zgodne.{/if}
			</p>{/if}
		<div class="submit-row">
			<button class="guest-btn" type="submit" formaction="?/guest" formnovalidate
				>Kontynuuj<br />jako gość</button
			>
			<button class="submit-btn" type="submit" disabled={passwordsMismatch}
				>{register ? 'Stwórz konto' : 'Zaloguj się'} <b>→</b></button
			>
		</div>
	</form>
</section>

<style>
	.card {
		width: min(430px, calc(100vw - 40px));
		box-sizing: border-box;
		padding: 42px 46px 38px;
		background: #1b1b1b;
		border: 0;
		border-radius: 18px;
		box-shadow: none;
		text-align: center;
		transition: opacity 180ms ease;
	}
	.card:hover {
		opacity: 0.96;
	}
	.card h1 {
		text-transform: uppercase;
		letter-spacing: 0.06em;
		font-size: 1.35rem;
		margin: 0 0 7px;
	}
	.card > p {
		margin: 0 0 34px;
		color: #aaaaaa;
		font-size: 0.72rem;
		text-transform: uppercase;
		letter-spacing: 0.06em;
	}
	.card a {
		color: #ffffff;
		text-decoration: none;
	}
	.card a:hover {
		opacity: 0.65;
	}
	.error {
		background: #2b2b2b;
		border: 1px solid #777777;
		color: #ffffff;
		border-radius: 7px;
		padding: 10px;
		margin-bottom: 16px;
		font-size: 0.78rem;
		text-align: left;
	}
	form {
		text-align: left;
	}
	label {
		display: block;
		text-transform: uppercase;
		letter-spacing: 0.11em;
		color: #aaaaaa;
		font-size: 0.62rem;
		margin: 20px 0;
	}
	input {
		display: block;
		width: 100%;
		box-sizing: border-box;
		border: 0;
		border-bottom: 1px solid #3b494e;
		background: transparent;
		color: white;
		padding: 10px 1px 12px;
		margin-top: 5px;
		outline: 0;
		font: inherit;
		font-size: 0.84rem;
		text-transform: none;
		letter-spacing: 0;
	}
	input:hover {
		opacity: 0.75;
	}
	input:focus {
		border-color: #ffffff;
	}
	input[aria-invalid='true'] {
		border-color: #ffffff;
	}
	.password-feedback {
		min-height: 18px;
		margin: -12px 0 8px;
		color: #aaaaaa;
		font-size: 0.68rem;
	}
	.password-feedback.mismatch {
		color: #ffffff;
		font-weight: 600;
	}
	.submit-row {
		display: flex;
		align-items: center;
		justify-content: space-between;
		gap: 20px;
		margin-top: 38px;
	}
	.submit-row button {
		white-space: nowrap;
		border: 0;
		border-radius: 8px;
		background: #f4f1eb;
		color: #171717;
		padding: 12px 16px;
		text-transform: uppercase;
		letter-spacing: 0.07em;
		font-weight: 750;
		font-size: 0.66rem;
		cursor: pointer;
		transition: opacity 180ms ease;
	}
	.submit-row button:hover:not(:disabled) {
		opacity: 0.7;
	}
	.submit-row button:disabled {
		cursor: not-allowed;
		opacity: 0.45;
	}
	.submit-row .guest-btn {
		background: transparent;
		color: #cccccc;
		padding: 0;
		font-weight: 400;
		line-height: 1.35;
	}
	.submit-row .guest-btn:hover {
		opacity: 0.6;
	}
	.submit-row b {
		margin-left: 7px;
	}
	@media (max-width: 480px) {
		.card {
			padding: 34px 25px;
		}
		.submit-row {
			align-items: stretch;
			flex-direction: column;
		}
		.submit-row button {
			width: 100%;
		}
	}
</style>
