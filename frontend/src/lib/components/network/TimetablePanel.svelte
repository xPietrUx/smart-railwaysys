<script lang="ts">
    import { onMount } from 'svelte';
    import { locale, localizedScenarioField, t } from '$lib/i18n';
    import { fetchScenarios, runScenario } from '$lib/services/scenarios';
    import type { ActiveScenarioInfo, Scenario } from '$lib/types/scenario';

    export let apiBaseUrl: string;
    /** Aktywny rozkład z żywego snapshotu (WebSocket). */
    export let scenario: ActiveScenarioInfo | null = null;
    /** Zmiana wartości wymusza przeładowanie listy (po zapisie/usunięciu w modalu). */
    export let refreshKey = 0;
    /** Otwiera modal szczegółów (edycja pociągów rozkładu). */
    export let onDetails: (scenario: Scenario) => void = () => {};
    /** Otwiera modal tworzenia nowego rozkładu. */
    export let onCreate: () => void = () => {};
    export let readOnly = false;

    const SCENARIO_ICONS: Record<string, string> = {
        ROZKLAD_BAZOWY: 'train',
        ROZKLAD_SZCZYT_GOP: 'location_city',
        ROZKLAD_EKSPRESY: 'bolt',
        ROZKLAD_TOWAROWY: 'local_shipping',
        ROZKLAD_BESKIDY: 'landscape',
        default: 'calendar_month'
    };

    let scenarios: Scenario[] = [];
    let listError = '';
    let actionError = '';
    let busyId: string | null = null;

    onMount(() => {
        void loadScenarios();
    });

    $: if (refreshKey > 0) {
        void loadScenarios();
    }

    async function loadScenarios() {
        listError = '';
        try {
            scenarios = await fetchScenarios(fetch, apiBaseUrl);
        } catch {
            listError = $t('timetable.loadError');
        }
    }

    async function handleRun(scenarioId: string) {
        if (busyId !== null) return;
        busyId = scenarioId;
        actionError = '';
        try {
            await runScenario(fetch, apiBaseUrl, scenarioId);
        } catch {
            actionError = $t('timetable.runError');
        } finally {
            busyId = null;
        }
    }

    function trainsCountLabel(count: number): string {
        if (count === 1) return $t('timetable.train.one', { count });
        if ($locale === 'en') return $t('timetable.train.many', { count });
        const lastDigit = count % 10;
        const lastTwo = count % 100;
        if (lastDigit >= 2 && lastDigit <= 4 && !(lastTwo >= 12 && lastTwo <= 14)) {
            return $t('timetable.train.few', { count });
        }
        return $t('timetable.train.many', { count });
    }
</script>

<svelte:head>
    <link
        rel="stylesheet"
        href="https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined:opsz,wght,FILL,GRAD@20..48,100..700,0..1,-50..200"
    />
</svelte:head>

<div class="panel">
    <div class="panel-header">
        <div>
            <p class="panel-label">{$t('timetable.label')}</p>
            <h2>{$t('timetable.title')}</h2>
        </div>
    </div>

    <div class="scroll-area">
        {#if scenario}
            <div class="active-box">
                <div class="active-title-row">
                    <span class="material-symbols-outlined active-icon" aria-hidden="true">play_arrow</span>
                    <strong>{localizedScenarioField(scenario.id, 'name', scenario.name, $t)}</strong>
                </div>
                <p>
                    {$t('timetable.active', {
                        spawned: scenario.spawnedTrains,
                        total: scenario.totalTrains
                    })}
                    {#if scenario.spawnedTrains < scenario.totalTrains}
                        · {$t('timetable.moreEntering')}
                    {/if}
                </p>
            </div>
        {/if}

        {#if actionError}
            <p class="error">{actionError}</p>
        {/if}

        {#if listError}
            <p class="error">{listError}</p>
            <button type="button" class="ghost-btn" on:click={loadScenarios}>
                {$t('timetable.retry')}
            </button>
        {:else}
            <ul class="scenario-list">
                {#each scenarios as item (item.id)}
                    <li class="scenario" class:active={scenario?.id === item.id}>
                        <div class="scenario-top">
                            <div class="scenario-title-group">
                                <span class="material-symbols-outlined icon" aria-hidden="true">
                                    {SCENARIO_ICONS[item.id] ?? SCENARIO_ICONS.default}
                                </span>
                                <strong>{localizedScenarioField(item.id, 'name', item.name, $t)}</strong>
                            </div>
                            {#if !readOnly}
                                <div class="scenario-actions">
                                    <button
                                        type="button"
                                        class="run-btn"
                                        on:click={() => handleRun(item.id)}
                                        disabled={busyId !== null}
                                        title={$t('timetable.runTitle')}
                                    >
                                        {#if busyId === item.id}
                                            <span class="material-symbols-outlined spinning" aria-hidden="true">progress_activity</span>
                                        {:else}
                                            <span class="material-symbols-outlined" aria-hidden="true">play_arrow</span>
                                        {/if}
                                    </button>
                                    <button
                                        type="button"
                                        class="details-btn"
                                        on:click={() => onDetails(item)}
                                        title={$t('timetable.detailsTitle')}
                                    >
                                        {$t('timetable.details')}
                                    </button>
                                </div>
                            {/if}
                        </div>
                        <div class="scenario-body">
                            {#if item.description}
                                <p>{localizedScenarioField(item.id, 'description', item.description, $t)}</p>
                            {/if}
                            <small>{trainsCountLabel(item.trains.length)}</small>
                        </div>
                    </li>
                {/each}
            </ul>

            {#if !readOnly}
                <button type="button" class="new-btn" on:click={onCreate}>
                    <span class="material-symbols-outlined btn-icon" aria-hidden="true">add</span>
                    <span>{$t('timetable.new')}</span>
                </button>
            {/if}
        {/if}
    </div>
</div>

<style>
    .material-symbols-outlined {
        font-family: 'Material Symbols Outlined' !important;
        font-weight: normal;
        font-style: normal;
        font-size: 19px;
        line-height: 1;
        letter-spacing: normal;
        text-transform: none;
        display: inline-block;
        white-space: nowrap;
        word-wrap: normal;
        direction: ltr;
        -webkit-font-smoothing: antialiased;
        text-rendering: optimizeLegibility;
        -moz-osx-font-smoothing: grayscale;
        font-feature-settings: 'liga';
        font-variation-settings:
            'FILL' 0,
            'wght' 200,
            'GRAD' 0,
            'opsz' 24;
        user-select: none;
        vertical-align: middle;
    }

    .panel {
        background: rgba(20, 20, 20, 0.94);
        backdrop-filter: blur(16px);
        -webkit-backdrop-filter: blur(16px);
        border: 0;
        box-shadow: 0 20px 48px rgba(0, 0, 0, 0.6);
        border-radius: 14px;
        padding: 20px;
        display: flex;
        flex-direction: column;
        min-height: 0;
        font-family: 'Inter Variable', Inter, sans-serif;
        color: #f5f7f8;
    }

    .panel-header {
        margin-bottom: 14px;
        flex-shrink: 0;
    }

    .panel-label {
        margin: 0 0 4px;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        font-size: 0.66rem;
        font-weight: 300;
        color: #97a5ad;
    }

    h2 {
        margin: 0;
        font-size: 1.1rem;
        font-weight: 400;
        letter-spacing: 0.04em;
        text-transform: uppercase;
        color: #ffffff;
    }

    .scroll-area {
        overflow-y: auto;
        min-height: 0;
    }

    .active-box {
        margin-bottom: 14px;
        padding: 12px;
        border-radius: 10px;
        background: rgba(255, 255, 255, 0.05);
    }

    .active-title-row {
        display: flex;
        align-items: center;
        gap: 6px;
    }

    .active-icon {
        font-size: 16px;
        color: #6cb09f;
    }

    .active-box strong {
        font-size: 0.78rem;
        font-weight: 400;
        letter-spacing: 0.06em;
        text-transform: uppercase;
        color: #f5f7f8;
    }

    .active-box p {
        margin: 4px 0 0 22px;
        font-size: 0.72rem;
        font-weight: 300;
        letter-spacing: 0.04em;
        color: #97a5ad;
        text-transform: uppercase;
    }

    .error {
        margin: 0 0 10px;
        padding: 8px 12px;
        border-radius: 8px;
        background: rgba(222, 132, 137, 0.15);
        color: #de8489;
        font-size: 0.74rem;
        font-weight: 300;
        letter-spacing: 0.02em;
        text-transform: uppercase;
        line-height: 1.4;
    }

    .scenario-list {
        list-style: none;
        margin: 0 0 14px;
        padding: 0;
        display: grid;
        gap: 8px;
    }

    .scenario {
        display: flex;
        flex-direction: column;
        gap: 6px;
        padding: 12px;
        border-radius: 10px;
        background: rgba(255, 255, 255, 0.03);
        transition: background-color 150ms ease;
    }

    .scenario.active {
        background: rgba(255, 255, 255, 0.07);
    }

    .scenario-top {
        display: flex;
        align-items: flex-start;
        justify-content: space-between;
        gap: 10px;
    }

    .scenario-title-group {
        display: flex;
        align-items: flex-start;
        gap: 8px;
        min-width: 0;
        flex: 1;
    }

    .icon {
        font-size: 18px;
        color: #97a5ad;
        flex-shrink: 0;
        margin-top: 1px;
    }

    .scenario-title-group strong {
        font-size: 0.78rem;
        font-weight: 400;
        letter-spacing: 0.06em;
        text-transform: uppercase;
        color: #f5f7f8;
        /* Usunięto nowrap, aby tekst ładnie się zawijał w razie potrzeby */
        word-break: break-word;
        line-height: 1.3;
    }

    .scenario-body {
        width: 100%;
    }

    .scenario-body p {
        margin: 0;
        font-size: 0.74rem;
        font-weight: 300;
        color: #97a5ad;
        line-height: 1.4;
        letter-spacing: 0.02em;
    }

    .scenario-body small {
        display: block;
        margin-top: 4px;
        color: #55626b;
        font-size: 0.68rem;
        font-weight: 300;
        letter-spacing: 0.04em;
        text-transform: uppercase;
    }

    .scenario-actions {
        display: flex;
        flex-direction: row;
        gap: 6px;
        align-items: center;
        flex-shrink: 0;
    }

    .run-btn {
        width: 28px;
        height: 28px;
        padding: 0;
        border-radius: 6px;
        border: 0;
        background: rgba(108, 176, 159, 0.15);
        color: #6cb09f;
        display: flex;
        align-items: center;
        justify-content: center;
        cursor: pointer;
        transition: background-color 150ms ease;
    }

    .run-btn .material-symbols-outlined {
        font-size: 15px;
    }

    .run-btn:hover:not(:disabled) {
        background: rgba(108, 176, 159, 0.28);
    }

    .run-btn:disabled {
        opacity: 0.4;
        cursor: default;
    }

    .details-btn {
        padding: 5px 9px;
        border-radius: 6px;
        border: 0;
        background: rgba(255, 255, 255, 0.04);
        color: #97a5ad;
        font-family: inherit;
        font-size: 0.68rem;
        font-weight: 400;
        letter-spacing: 0.06em;
        text-transform: uppercase;
        cursor: pointer;
        white-space: nowrap;
        transition: background-color 150ms ease, color 150ms ease;
    }

    .details-btn:hover {
        background: rgba(255, 255, 255, 0.08);
        color: #ffffff;
    }

    .new-btn {
        width: 100%;
        padding: 10px 14px;
        border-radius: 10px;
        border: 0;
        background: rgba(255, 255, 255, 0.04);
        color: #97a5ad;
        font-family: inherit;
        font-weight: 400;
        font-size: 0.72rem;
        letter-spacing: 0.06em;
        text-transform: uppercase;
        cursor: pointer;
        display: inline-flex;
        align-items: center;
        justify-content: center;
        gap: 6px;
        transition: background-color 150ms ease, color 150ms ease;
    }

    .new-btn:hover {
        background: rgba(255, 255, 255, 0.08);
        color: #ffffff;
    }

    .new-btn .btn-icon {
        font-size: 16px;
    }

    .ghost-btn {
        width: 100%;
        padding: 8px 12px;
        border-radius: 8px;
        border: 0;
        background: rgba(255, 255, 255, 0.04);
        color: #97a5ad;
        font-family: inherit;
        font-size: 0.72rem;
        font-weight: 300;
        letter-spacing: 0.06em;
        text-transform: uppercase;
        cursor: pointer;
        transition: background-color 150ms ease, color 150ms ease;
    }

    .ghost-btn:hover {
        background: rgba(255, 255, 255, 0.08);
        color: #ffffff;
    }
</style>