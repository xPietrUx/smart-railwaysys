<script lang="ts">
	import { page } from '$app/stores';

	export let authenticated = false;
	let menuOpen = false;
	$: path = $page.url.pathname;
	const navItems = [
		{ label: 'Strona główna', href: '/' },
		{ label: 'Jak to działa', href: '/#jak-to-dziala' },
		{ label: 'O nas', href: '/#o-nas' },
		{ label: 'Kontakt', href: '/#kontakt' }
	];
	$: actionLabel = authenticated ? 'Przejdź do systemu' : 'Zaloguj się';
</script>

<header class="site-header">
	<button
		class="menu"
		type="button"
		on:click={() => (menuOpen = !menuOpen)}
		aria-label="Otwórz menu"
		aria-expanded={menuOpen}>☰</button
	>
	<nav class:open={menuOpen} aria-label="Główna nawigacja">
		{#each navItems as item}
			<a class:active={path === item.href} href={item.href} aria-label={item.label}>
				<span class="tech-text" aria-hidden="true"
					>{#each [...item.label] as letter, index}<i style={`--i:${index}`}
							>{letter === ' ' ? '\u00a0' : letter}</i
						>{/each}</span
				>
			</a>
		{/each}
	</nav>
	<div class="actions">
		<a class="login" data-sveltekit-preload-data="off" href={authenticated ? '/panel' : '/login'}
			><span class="tech-text" aria-hidden="true"
				>{#each [...actionLabel] as letter, index}<i style={`--i:${index}`}
						>{letter === ' ' ? '\u00a0' : letter}</i
					>{/each}</span
			><b>→</b></a
		>
	</div>
</header>

<style>
	.site-header {
		height: 76px;
		padding: 0 clamp(20px, 5vw, 72px);
		display: flex;
		align-items: center;
		gap: 38px;
		position: relative;
		z-index: 20;
		border-bottom: 1px solid rgba(255, 255, 255, 0.07);
		background: #333333;
		box-sizing: border-box;
	}
	nav {
		display: flex;
		gap: 32px;
		margin-right: auto;
	}
	nav a {
		color: #97a5ad;
		text-decoration: none;
		text-transform: uppercase;
		letter-spacing: 0.12em;
		font-size: 0.68rem;
		font-weight: 650;
		transition: opacity 180ms ease;
	}
	nav a.active {
		color: #fff;
	}
	nav a:hover {
		opacity: 0.55;
	}
	.actions {
		display: flex;
		align-items: center;
		gap: 20px;
	}
	.login {
		color: #dddddd;
		background: #1c1c1c;
		text-decoration: none;
		padding: 10px 16px;
		border-radius: 8px;
		font-size: 0.72rem;
		font-weight: 750;
		text-transform: uppercase;
		letter-spacing: 0.08em;
		transition: opacity 180ms ease;
	}
	.login b {
		margin-left: 7px;
	}
	.login:hover {
		opacity: 0.65;
	}
	.tech-text {
		display: inline-flex;
		overflow: hidden;
	}
	.tech-text i {
		font-style: normal;
		transition: opacity 180ms ease;
		transition-delay: calc(var(--i) * 12ms);
	}
	a:hover .tech-text i {
		opacity: 0.45;
	}
	a:hover .tech-text i:nth-child(even) {
		opacity: 0.75;
	}
	.menu {
		display: none;
		background: none;
		border: 0;
		color: white;
		font-size: 1.2rem;
	}
	@media (max-width: 820px) {
		.site-header {
			height: 66px;
			gap: 16px;
		}
		nav {
			margin-right: auto;
		}
		.menu {
			display: block;
			order: 2;
		}
		.actions {
			order: 3;
		}
		nav {
			display: none;
			position: absolute;
			top: 66px;
			left: 0;
			right: 0;
			padding: 22px;
			background: #292929;
			flex-direction: column;
			gap: 20px;
		}
		nav.open {
			display: flex;
		}
		.login {
			padding: 9px 11px;
			font-size: 0.62rem;
		}
		.login b {
			display: none;
		}
	}
</style>
