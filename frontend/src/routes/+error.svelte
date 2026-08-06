<script lang="ts">
	import { onMount } from 'svelte';
	import { resolve } from '$app/paths';
	import { page } from '$app/stores';
	import LanguageSwitcher from '$lib/components/LanguageSwitcher.svelte';
	import { initLocale, t } from '$lib/i18n';

	onMount(initLocale);
</script>

<svelte:head>
	<title>{$t('error.status', { status: $page.status })} — Smart Railway System</title>
</svelte:head>

<main>
	<section class="error-card">
		<div class="switcher"><LanguageSwitcher /></div>
		<p>{$t('error.status', { status: $page.status })}</p>
		<h1>{$t('error.title')}</h1>
		<span>{$t('error.description')}</span>
		<a href={resolve('/')}>{$t('error.home')}</a>
	</section>
</main>

<style>
	:global(html),
	:global(body) {
		height: 100%;
	}

	:global(body) {
		margin: 0;
		font-family: Inter, ui-sans-serif, system-ui, sans-serif;
		background:
			radial-gradient(circle at top, rgba(37, 99, 235, 0.2), transparent 35%),
			linear-gradient(180deg, #0f172a 0%, #111827 100%);
		color: #e5eefb;
	}

	main {
		min-height: 100dvh;
		display: grid;
		place-items: center;
		padding: 24px;
		box-sizing: border-box;
	}

	.error-card {
		position: relative;
		width: min(460px, 100%);
		box-sizing: border-box;
		padding: 32px;
		border: 1px solid rgba(148, 163, 184, 0.22);
		border-radius: 18px;
		background: rgba(15, 23, 42, 0.86);
		box-shadow: 0 24px 60px rgba(15, 23, 42, 0.45);
		backdrop-filter: blur(12px);
	}

	.switcher {
		position: absolute;
		top: 16px;
		right: 16px;
	}

	p {
		margin: 0 0 8px;
		color: #93c5fd;
		font-size: 0.75rem;
		font-weight: 700;
		letter-spacing: 0.12em;
		text-transform: uppercase;
	}

	h1 {
		margin: 0 0 12px;
		font-size: 1.5rem;
	}

	span {
		display: block;
		color: #cbd5e1;
		line-height: 1.55;
	}

	a {
		display: inline-block;
		margin-top: 22px;
		padding: 9px 14px;
		border-radius: 10px;
		background: rgba(37, 99, 235, 0.7);
		color: #fff;
		font-size: 0.85rem;
		font-weight: 700;
		text-decoration: none;
	}

	a:hover {
		background: rgba(37, 99, 235, 0.9);
	}
</style>
