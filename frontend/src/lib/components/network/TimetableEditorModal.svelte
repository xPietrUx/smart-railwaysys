<script lang="ts">
    import { locale, localizedScenarioField, t } from '$lib/i18n';
    import { trainTypeLabel } from '$lib/services/labels';
    import { createScenario, deleteScenario, updateScenario } from '$lib/services/scenarios';
    import type { NetworkGraph } from '$lib/types/network';
    import type { Scenario, TrainPlan, TrainPlanType } from '$lib/types/scenario';

    export let apiBaseUrl: string;
    export let graph: NetworkGraph;
    /** Edytowany scenariusz; null = tworzenie nowego. */
    export let scenario: Scenario | null = null;
    /** Wywoływane przy zamknięciu; changed=true, gdy coś zapisano/usunięto. */
    export let onClose: (changed: boolean) => void = () => {};

    const TRAIN_TYPES: TrainPlanType[] = ['REGIONAL', 'IC', 'FREIGHT'];

    $: stationOptions = graph.stations
        .slice()
        .sort((a, b) => a.name.localeCompare(b.name, $locale === 'pl' ? 'pl' : 'en'));

    let draftName = scenario?.name ?? '';
    let draftDescription = scenario?.description ?? '';
    let rows: TrainPlan[] = scenario ? scenario.trains.map((t) => ({ ...t })) : [newRow()];
    let saveError = '';
    let saving = false;
    let deleting = false;

    function newRow(): TrainPlan {
        const first = graph.stations[0]?.id ?? '';
        const second = graph.stations[1]?.id ?? first;
        return {
            name: $t('editor.defaultTrainName'),
            type: 'REGIONAL',
            fromStationId: first,
            toStationId: second,
            departS: 0
        };
    }

    function addRow() {
        if (rows.length >= 60) return;
        rows = [...rows, newRow()];
    }

    function removeRow(index: number) {
        rows = rows.filter((_, i) => i !== index);
    }

    async function handleSave() {
        if (saving || deleting) return;
        if (!draftName.trim()) {
            saveError = $t('editor.error.name');
            return;
        }
        if (rows.length === 0) {
            saveError = $t('editor.error.noTrains');
            return;
        }
        const badRow = rows.findIndex(
            (row) => !row.name.trim() || row.fromStationId === row.toStationId
        );
        if (badRow >= 0) {
            saveError = $t('editor.error.invalidTrain', { number: badRow + 1 });
            return;
        }
        saving = true;
        saveError = '';
        const payload = {
            name: draftName.trim(),
            description: draftDescription.trim(),
            trains: rows.map((row) => ({ ...row, name: row.name.trim() }))
        };
        try {
            if (scenario !== null) {
                await updateScenario(fetch, apiBaseUrl, scenario.id, payload);
            } else {
                await createScenario(fetch, apiBaseUrl, payload);
            }
            onClose(true);
        } catch {
            saveError = $t('editor.error.save');
        } finally {
            saving = false;
        }
    }

    async function handleDelete() {
        if (saving || deleting || scenario === null) return;
        deleting = true;
        saveError = '';
        try {
            await deleteScenario(fetch, apiBaseUrl, scenario.id);
            onClose(true);
        } catch {
            saveError = $t('editor.error.delete');
        } finally {
            deleting = false;
        }
    }

    function handleBackdropClick(event: MouseEvent) {
        if (event.target === event.currentTarget) onClose(false);
    }

    function handleKeydown(event: KeyboardEvent) {
        if (event.key === 'Escape') onClose(false);
    }
</script>

<svelte:head>
    <link
        rel="stylesheet"
        href="https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined:opsz,wght,FILL,GRAD@20..48,100..700,0..1,-50..200"
    />
</svelte:head>

<svelte:window on:keydown={handleKeydown} />

<!-- svelte-ignore a11y_click_events_have_key_events a11y_no_static_element_interactions -->
<div class="overlay" on:click={handleBackdropClick}>
    <div class="modal" role="dialog" aria-modal="true" aria-label={$t('editor.dialogAria')}>
        <div class="modal-header">
            <div>
                <p class="modal-label">
                    {scenario !== null ? $t('editor.details') : $t('editor.newTimetable')}
                </p>
                <h2>
                    {scenario !== null
                        ? localizedScenarioField(scenario.id, 'name', scenario.name, $t)
                        : $t('editor.newScenario')}
                </h2>
            </div>
            <button
                type="button"
                class="close-btn"
                on:click={() => onClose(false)}
                title={$t('editor.close')}
            >
                <span class="material-symbols-outlined" aria-hidden="true">close</span>
            </button>
        </div>

        <div class="modal-body">
            <div class="meta-fields">
                <label class="field">
                    <span>{$t('editor.name')}</span>
                    <input
                        type="text"
                        maxlength="80"
                        bind:value={draftName}
                        placeholder={$t('editor.namePlaceholder')}
                    />
                </label>
                <label class="field">
                    <span>{$t('editor.description')}</span>
                    <input
                        type="text"
                        maxlength="300"
                        bind:value={draftDescription}
                        placeholder={$t('editor.descriptionPlaceholder')}
                    />
                </label>
            </div>

            <div class="trains-head">
                <h3>{$t('editor.trains', { count: rows.length })}</h3>
                <button type="button" class="add-btn" on:click={addRow} disabled={rows.length >= 60}>
                    <span class="material-symbols-outlined btn-icon" aria-hidden="true">add</span>
                    <span>{$t('editor.addTrain')}</span>
                </button>
            </div>

            <div class="trains-table">
                <div class="row head">
                    <span>{$t('editor.name')}</span>
                    <span>{$t('editor.type')}</span>
                    <span>{$t('editor.fromStation')}</span>
                    <span>{$t('editor.toStation')}</span>
                    <span>{$t('editor.departAfter')}</span>
                    <span></span>
                </div>
                {#each rows as row, index (index)}
                    <div class="row">
                        <input type="text" maxlength="80" bind:value={row.name} />
                        <select bind:value={row.type}>
                            {#each TRAIN_TYPES as trainType (trainType)}
                                <option value={trainType}>{trainTypeLabel(trainType, $t)}</option>
                            {/each}
                        </select>
                        <select bind:value={row.fromStationId}>
                            {#each stationOptions as station (station.id)}
                                <option value={station.id}>{station.name}</option>
                            {/each}
                        </select>
                        <select bind:value={row.toStationId}>
                            {#each stationOptions as station (station.id)}
                                <option value={station.id}>{station.name}</option>
                            {/each}
                        </select>
                        <input type="number" min="0" max="600" step="5" bind:value={row.departS} />
                        <button
                            type="button"
                            class="remove-btn"
                            on:click={() => removeRow(index)}
                            title={$t('editor.removeTrainTitle')}
                        >
                            <span class="material-symbols-outlined" aria-hidden="true">close</span>
                        </button>
                    </div>
                {/each}
            </div>

            {#if saveError}
                <p class="error">{saveError}</p>
            {/if}
        </div>

        <div class="modal-footer">
            {#if scenario !== null}
                <button
                    type="button"
                    class="danger-btn"
                    on:click={handleDelete}
                    disabled={deleting || saving}
                >
                    {#if deleting}
                        <span>{$t('editor.deleting')}</span>
                    {:else}
                        <span class="material-symbols-outlined btn-icon" aria-hidden="true">delete</span>
                        <span>{$t('editor.deleteScenario')}</span>
                    {/if}
                </button>
            {:else}
                <span></span>
            {/if}
            <div class="footer-right">
                <button type="button" class="ghost-btn" on:click={() => onClose(false)}>
                    {$t('editor.cancel')}
                </button>
                <button type="button" class="save-btn" on:click={handleSave} disabled={saving || deleting}>
                    {#if saving}
                        <span>{$t('editor.saving')}</span>
                    {:else}
                        <span class="material-symbols-outlined btn-icon" aria-hidden="true">save</span>
                        <span>{scenario !== null ? $t('editor.saveChanges') : $t('editor.createScenario')}</span>
                    {/if}
                </button>
            </div>
        </div>
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

    .overlay {
        position: absolute;
        inset: 0;
        z-index: 60;
        background: rgba(0, 0, 0, 0.7);
        backdrop-filter: blur(8px);
        -webkit-backdrop-filter: blur(8px);
        display: flex;
        align-items: center;
        justify-content: center;
        padding: 20px;
        box-sizing: border-box;
    }

    .modal {
        width: min(820px, 94vw);
        max-height: min(86vh, 740px);
        display: flex;
        flex-direction: column;
        background: rgba(20, 20, 20, 0.96);
        border: 0;
        border-radius: 14px;
        box-shadow: 0 24px 60px rgba(0, 0, 0, 0.7);
        font-family: 'Inter Variable', Inter, sans-serif;
        font-weight: 300;
        color: #f5f7f8;
        box-sizing: border-box;
    }

    .modal-header {
        display: flex;
        justify-content: space-between;
        align-items: flex-start;
        gap: 12px;
        padding: 20px 24px 14px;
    }

    .modal-label {
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

    h3 {
        margin: 0;
        font-size: 0.72rem;
        font-weight: 300;
        color: #97a5ad;
        text-transform: uppercase;
        letter-spacing: 0.08em;
    }

    .close-btn {
        border: 0;
        background: transparent;
        color: #97a5ad;
        width: 24px;
        height: 24px;
        padding: 0;
        display: flex;
        align-items: center;
        justify-content: center;
        cursor: pointer;
        flex-shrink: 0;
        transition: color 150ms ease;
    }

    .close-btn:hover {
        color: #ffffff;
    }

    .close-btn .material-symbols-outlined {
        font-size: 19px;
    }

    .modal-body {
        padding: 8px 24px 20px;
        overflow-y: auto;
        min-height: 0;
    }

    .meta-fields {
        display: grid;
        grid-template-columns: 1fr 1fr;
        gap: 12px;
        margin-bottom: 18px;
    }

    .field {
        display: grid;
        gap: 6px;
    }

    .field span {
        font-size: 0.68rem;
        font-weight: 300;
        letter-spacing: 0.06em;
        text-transform: uppercase;
        color: #97a5ad;
    }

    input,
    select {
        width: 100%;
        box-sizing: border-box;
        height: 38px;
        padding: 0 12px;
        border-radius: 8px;
        border: 0;
        background: rgba(255, 255, 255, 0.04);
        color: #f5f7f8;
        font-family: inherit;
        font-size: 0.78rem;
        font-weight: 300;
        letter-spacing: 0.04em;
        text-transform: uppercase;
        outline: none;
        transition: background-color 150ms ease;
    }

    input::placeholder {
        color: #64748b;
        text-transform: uppercase;
        font-weight: 300;
        letter-spacing: 0.04em;
    }

    input:focus,
    select:focus {
        background: rgba(255, 255, 255, 0.08);
    }

    select option {
        background: #1a1a1a;
        color: #f5f7f8;
    }

    .trains-head {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 10px;
    }

    .add-btn {
        padding: 6px 12px;
        border-radius: 8px;
        border: 0;
        background: rgba(255, 255, 255, 0.04);
        color: #97a5ad;
        font-family: inherit;
        font-size: 0.72rem;
        font-weight: 400;
        letter-spacing: 0.06em;
        text-transform: uppercase;
        cursor: pointer;
        display: inline-flex;
        align-items: center;
        gap: 6px;
        transition: background-color 150ms ease, color 150ms ease;
    }

    .add-btn:hover:not(:disabled) {
        background: rgba(255, 255, 255, 0.08);
        color: #ffffff;
    }

    .add-btn:disabled {
        opacity: 0.35;
        cursor: default;
    }

    .add-btn .btn-icon {
        font-size: 16px;
    }

    .trains-table {
        display: grid;
        gap: 6px;
    }

    .row {
        display: grid;
        grid-template-columns: 1.4fr 1fr 1.1fr 1.1fr 0.8fr 28px;
        gap: 8px;
        align-items: center;
    }

    .row.head {
        font-size: 0.66rem;
        font-weight: 300;
        color: #64748b;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        padding: 0 4px;
    }

    .remove-btn {
        border: 0;
        background: transparent;
        color: #97a5ad;
        width: 28px;
        height: 28px;
        padding: 0;
        display: flex;
        align-items: center;
        justify-content: center;
        cursor: pointer;
        transition: color 150ms ease;
    }

    .remove-btn:hover {
        color: #de8489;
    }

    .remove-btn .material-symbols-outlined {
        font-size: 18px;
    }

    .error {
        margin: 14px 0 0;
        padding: 8px 12px;
        border-radius: 8px;
        background: rgba(222, 132, 137, 0.15);
        border: 0;
        color: #de8489;
        font-size: 0.74rem;
        font-weight: 300;
        letter-spacing: 0.02em;
        text-transform: uppercase;
        line-height: 1.4;
    }

    .modal-footer {
        display: flex;
        justify-content: space-between;
        align-items: center;
        gap: 10px;
        padding: 16px 24px 20px;
    }

    .footer-right {
        display: flex;
        gap: 8px;
    }

    .save-btn {
        padding: 8px 16px;
        border-radius: 8px;
        border: 0;
        background: #f4f1eb;
        color: #141414;
        font-family: inherit;
        font-weight: 500;
        font-size: 0.74rem;
        letter-spacing: 0.06em;
        text-transform: uppercase;
        cursor: pointer;
        display: inline-flex;
        align-items: center;
        gap: 6px;
        transition: opacity 150ms ease;
    }

    .save-btn:hover:not(:disabled) {
        opacity: 0.85;
    }

    .save-btn:disabled {
        opacity: 0.4;
        cursor: default;
    }

    .save-btn .btn-icon {
        font-size: 16px;
    }

    .danger-btn {
        padding: 8px 14px;
        border-radius: 8px;
        border: 0;
        background: rgba(222, 132, 137, 0.12);
        color: #de8489;
        font-family: inherit;
        font-weight: 400;
        font-size: 0.72rem;
        letter-spacing: 0.06em;
        text-transform: uppercase;
        cursor: pointer;
        display: inline-flex;
        align-items: center;
        gap: 6px;
        transition: background-color 150ms ease;
    }

    .danger-btn:hover:not(:disabled) {
        background: rgba(222, 132, 137, 0.22);
    }

    .danger-btn:disabled {
        opacity: 0.4;
        cursor: default;
    }

    .danger-btn .btn-icon {
        font-size: 16px;
    }

    .ghost-btn {
        padding: 8px 14px;
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

    @media (max-width: 700px) {
        .meta-fields {
            grid-template-columns: 1fr;
        }

        .row {
            grid-template-columns: 1fr 1fr;
        }

        .row.head {
            display: none;
        }
    }
</style>