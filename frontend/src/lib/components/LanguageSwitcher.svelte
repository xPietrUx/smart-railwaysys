<script lang="ts">
	import { locale, setLocale, t, type Locale } from '$lib/i18n';

	function choose(nextLocale: Locale) {
		setLocale(nextLocale);
	}
</script>

<div class="language-switcher" role="group" aria-label={$t('language.label')}>
	<button
		type="button"
		class:active={$locale === 'pl'}
		aria-pressed={$locale === 'pl'}
		title={$t('language.polish')}
		on:click={() => choose('pl')}>PL</button
	>
	<button
		type="button"
		class:active={$locale === 'en'}
		aria-pressed={$locale === 'en'}
		title={$t('language.english')}
		on:click={() => choose('en')}>EN</button
	>
</div>

<style>
	.language-switcher {
		display: inline-flex;
		padding: 2px;
		border: 1px solid rgba(148, 163, 184, 0.25);
		border-radius: 9px;
		background: rgba(30, 41, 59, 0.72);
	}

	button {
		border: 0;
		border-radius: 6px;
		padding: 4px 7px;
		background: transparent;
		color: #94a3b8;
		font: inherit;
		font-size: 0.68rem;
		font-weight: 700;
		cursor: pointer;
	}

	button:hover {
		color: #e2e8f0;
	}

	button.active {
		background: rgba(37, 99, 235, 0.65);
		color: #fff;
	}
</style>
