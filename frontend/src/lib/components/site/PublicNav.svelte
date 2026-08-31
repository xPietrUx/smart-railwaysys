<script lang="ts">
    import { page } from '$app/stores';
    import { onMount } from 'svelte';
    import { locale, setLocale } from '$lib/i18n';
	import { createEventDispatcher } from 'svelte';
	const dispatch = createEventDispatcher();

    export let authenticated = false;
    let menuOpen = false;
    let lightMode = false;
    let navElement: HTMLElement;
    $: path = $page.url.pathname;
    const navItems = [
        { label: 'Jak to działa', href: '/#jak-to-dziala' },
        { label: 'O wa.gone', href: '/#o-wa-gone' },
        { 
            label: 'Dokumentacja', 
            href: 'https://github.com/xPietrUx/smart-railwaysys#readme', 
            target: '_blank', 
            rel: 'noreferrer' 
        },
        { label: 'Kontakt', href: '/#kontakt' }
    ];
    $: actionLabel = authenticated ? 'Przejdź do systemu' : 'Zaloguj się';

    function closeMenu() {
        menuOpen = false;
    }

	function handleLoginClick(e: MouseEvent) {
		e.preventDefault();
		dispatch('openLogin');
	}

    function toggleLanguage() {
        setLocale($locale === 'pl' ? 'en' : 'pl');
    }

    function toggleLightMode() {
        lightMode = !lightMode;
        document.documentElement.classList.toggle('light-mode', lightMode);
        localStorage.setItem('smart-railway.theme', lightMode ? 'light' : 'dark');
    }

    onMount(() => {
        lightMode = localStorage.getItem('smart-railway.theme') === 'light';
        document.documentElement.classList.toggle('light-mode', lightMode);
    });

    onMount(() => {
        if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) return;

        let cancelled = false;
        let cleanup: (() => void) | undefined;

        void Promise.all([
            import('gsap'),
            import('gsap/SplitText'),
            import('gsap/ScrambleTextPlugin')
        ]).then(([gsapModule, splitTextModule, scrambleModule]) => {
            if (cancelled || !navElement) return;

            const { gsap } = gsapModule;
            const { SplitText } = splitTextModule;
            const { ScrambleTextPlugin } = scrambleModule;
            gsap.registerPlugin(SplitText, ScrambleTextPlugin);

            const effects = [...navElement.querySelectorAll<HTMLElement>('.scrambled-text')].map(
                (element) => {
                    const split = SplitText.create(element, {
                        type: 'chars',
                        charsClass: 'scrambled-char'
                    });

                    split.chars.forEach((character) => {
                        gsap.set(character, { attr: { 'data-content': character.textContent ?? '' } });
                    });

                    const handleMove = (event: PointerEvent) => {
                        const radius = 42;
                        const duration = 1.2;

                        split.chars.forEach((character) => {
                            const { left, top, width, height } = character.getBoundingClientRect();
                            const distance = Math.hypot(
                                event.clientX - (left + width / 2),
                                event.clientY - (top + height / 2)
                            );

                            if (distance < radius) {
                                gsap.to(character, {
                                    overwrite: true,
                                    duration: duration * (1 - distance / radius),
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
                        gsap.killTweensOf(split.chars);
                        split.chars.forEach((character) => {
                            character.textContent = character.getAttribute('data-content') ?? '';
                        });
                    };

                    element.addEventListener('pointermove', handleMove);
                    element.addEventListener('pointerleave', handleLeave);
                    return { element, split, handleMove, handleLeave };
                }
            );

            cleanup = () => {
                effects.forEach(({ element, split, handleMove, handleLeave }) => {
                    element.removeEventListener('pointermove', handleMove);
                    element.removeEventListener('pointerleave', handleLeave);
                    gsap.killTweensOf(split.chars);
                    split.revert();
                });
            };
        });

        return () => {
            cancelled = true;
            cleanup?.();
        };
    });
</script>

<header class="site-header">
    <a class="brand" href="/" aria-label="Strona główna">
        <img src={lightMode ? '/logo/logo_black.png' : '/logo/logo_white.png'} alt="wa.gone" />
    </a>
    <button
        class="menu"
        type="button"
        on:click={() => (menuOpen = !menuOpen)}
        aria-label="Otwórz menu"
        aria-expanded={menuOpen}>☰</button
    >
    <nav bind:this={navElement} class:open={menuOpen} aria-label="Główna nawigacja">
        {#each navItems as item}
            <a
                class:active={path === item.href}
                href={item.href}
                target={item.target ?? null}
                rel={item.rel ?? null}
                aria-label={item.label}
                on:click={closeMenu}
            >
                <span class="scrambled-text">{item.label}</span>
            </a>
        {/each}
    </nav>
    <div class="actions">
        <button
            class="icon-button"
            type="button"
            on:click={toggleLanguage}
            aria-label={$locale === 'pl' ? 'Zmień język na angielski' : 'Change language to Polish'}
            title={$locale === 'pl' ? 'English' : 'Polski'}
        >
            <span class="material-symbols-outlined" aria-hidden="true">language</span>
        </button>
        <button
            class="icon-button"
            type="button"
            on:click={toggleLightMode}
            aria-label={lightMode ? 'Włącz tryb ciemny' : 'Włącz tryb jasny'}
            title={lightMode ? 'Tryb ciemny' : 'Tryb jasny'}
        >
            <span class="material-symbols-outlined" class:is-light={lightMode} aria-hidden="true"
                >{lightMode ? 'dark_mode' : 'light_mode'}</span
            >
        </button>
        <a 
	class="login" 
	href={authenticated ? '/panel' : '/login'} 
	on:click={authenticated ? null : handleLoginClick}
>
	{actionLabel}
</a>
    </div>
</header>

<style>
    .site-header {
        height: 76px;
        padding: 0 clamp(20px, 5vw, 72px);
        display: flex;
        align-items: center;
        justify-content: center;
        position: sticky;
        top: 0;
        z-index: 20;
        border-bottom: 0;
        background: transparent;
        box-sizing: border-box;
        transition:
            color 300ms ease,
            background-color 300ms ease;
    }
    .brand {
        position: absolute;
        left: clamp(20px, 5vw, 72px);
        display: flex;
        align-items: center;
    }
    .brand img {
        display: block;
        width: 44px;
        height: auto;
    }
    nav {
        display: flex;
        align-items: center;
        justify-content: center;
        gap: 32px;
        flex-wrap: wrap;
    }
    nav a {
        color: #97a5ad;
        text-decoration: none;
        text-transform: uppercase;
        letter-spacing: 0.12em;
        font-size: 0.68rem;
        font-family: 'Inter Variable', Inter, sans-serif;
        font-style: normal;
        font-weight: 300;
        transition: color 300ms ease;
    }
    nav a.active {
        color: #fff;
    }
    nav a:hover {
        color: #fff;
    }
    .actions {
        display: flex;
        align-items: center;
        gap: 10px;
        position: absolute;
        right: clamp(20px, 5vw, 72px);
    }
    .login {
        color: #dddddd;
        background: #1c1c1c;
        text-decoration: none;
        padding: 10px 16px;
        border-radius: 8px;
        font-size: 0.72rem;
        font-weight: 500;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        transition:
            color 300ms ease,
            background-color 300ms ease,
            opacity 180ms ease;
    }
    .login b {
        margin-left: 7px;
    }
    .login:hover {
        opacity: 0.65;
    }
    .icon-button {
        display: grid;
        place-items: center;
        width: 36px;
        height: 36px;
        padding: 0;
        border: 0;
        background: transparent;
        color: #97a5ad;
        cursor: pointer;
        transition: color 300ms ease;
    }
    .icon-button:hover {
        color: #fff;
    }
    .material-symbols-outlined {
        font-size: 21px;
        font-variation-settings:
            'FILL' 0,
            'wght' 300,
            'GRAD' 0,
            'opsz' 24;
        transition: transform 300ms ease;
    }
    .material-symbols-outlined.is-light {
        transform: rotate(180deg);
    }
    :global(.scrambled-char) {
        display: inline-block;
        will-change: contents;
    }
    :global(html.light-mode) .site-header {
        border-bottom: 0;
    }
    :global(html.light-mode) nav a,
    :global(html.light-mode) .icon-button {
        color: #52606a;
    }
    :global(html.light-mode) nav a:hover,
    :global(html.light-mode) .icon-button:hover {
        color: #111827;
    }
    :global(html.light-mode) .login {
        background: #e5e7eb;
        color: #1f2937;
    }
    .menu {
        display: none;
        background: none;
        border: 0;
        color: white;
        font-size: 1.2rem;
        position: absolute;
        left: clamp(20px, 5vw, 72px);
    }
    @media (max-width: 1000px) {
        .site-header {
            height: 66px;
        }
        .menu {
            display: block;
            left: calc(clamp(20px, 5vw, 72px) + 52px);
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
            align-items: center;
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
        .brand img {
            width: 38px;
        }
    }
</style>
