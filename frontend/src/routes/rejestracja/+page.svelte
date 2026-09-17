<script lang="ts">
    import PublicNav from '$lib/components/site/PublicNav.svelte';
    import AuthCard from '$lib/components/site/AuthCard.svelte';
    import type { ActionData } from './$types';

    export let form: ActionData;
</script>

<svelte:head>
    <title>Rejestracja — Smart Railway</title>
</svelte:head>

<div class="auth-layout">
    <PublicNav />
    <main class="auth-main">
        <AuthCard mode="register" error={form?.error} email={form?.email} />
    </main>
</div>

<style>
    .auth-layout {
        min-height: 100vh;
        background: #111111;
        color: #f5f7f8;
        transition: background-color 300ms ease, color 300ms ease;
    }

    :global(html.light-mode) .auth-layout {
        background: #f4f5f3;
        color: #1f2933;
    }

    .auth-main {
        display: grid;
        min-height: calc(100vh - 76px);
        place-items: center;
        padding: 50px 20px;
        box-sizing: border-box;
    }
</style>