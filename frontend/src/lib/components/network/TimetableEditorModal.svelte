<script lang="ts">
    import { locale, localizedScenarioField, t } from '$lib/i18n';
    import { trainTypeLabel } from '$lib/services/labels';
    import { createScenario, deleteScenario, updateScenario } from '$lib/services/scenarios';
    import type { NetworkGraph } from '$lib/types/network';
    import type { Scenario, TrainPlan, TrainPlanType } from '$lib/types/scenario';

    export let apiBaseUrl: string;
    export let graph: NetworkGraph;
    export let scenario: Scenario | null = null;
    export let onClose: (changed: boolean) => void = () => {};

    const TRAIN_TYPES: TrainPlanType[] = ['REGIONAL', 'IC', 'FREIGHT'];

    $: stationOptions = graph.stations
        .slice()
        .sort((a, b) => a.name.localeCompare(b.name, $locale === 'pl' ? 'pl' : 'en'));

    let draftName = scenario?.name ?? '';
    let draftDescription = scenario?.description ?? '';
    let rows: TrainPlan[] = scenario ? scenario.trains.map((t) => ({ ...t })) : [newRow(1)];
    let saveError = '';
    let saving = false;
    let deleting = false;
    let showConfirmDelete = false;

    function newRow(trainNumber: number): TrainPlan {
        const first = graph.stations[0]?.id ?? '';
        const second = graph.stations[1]?.id ?? first;
        
        const baseName = $t('editor.defaultTrainName');
        const defaultName = baseName ? `${baseName} ${trainNumber}` : `Pociąg ${trainNumber}`;

        return {
            name: defaultName,
            type: 'REGIONAL',
            fromStationId: first,
            toStationId: second,
            departS: 0
        };
    }

    function addRow() {
        if (rows.length >= 60) return;
        const nextNumber = rows.length + 1;
        rows = [...rows, newRow(nextNumber)];
    }

    function removeRow(index: number) {
        rows = rows.filter((_, i) => i !== index);
    }

    function stepDepart(index: number, delta: number) {
        const current = Number(rows[index].departS) || 0;
        rows[index].departS = Math.max(0, Math.min(600, current + delta));
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

    function promptDelete() {
        if (saving || deleting || scenario === null) return;
        showConfirmDelete = true;
    }

    async function confirmDelete() {
        if (saving || deleting || scenario === null) return;
        deleting = true;
        saveError = '';
        try {
            await deleteScenario(fetch, apiBaseUrl, scenario.id);
            showConfirmDelete = false;
            onClose(true);
        } catch {
            saveError = $t('editor.error.delete');
            showConfirmDelete = false;
        } finally {
            deleting = false;
        }
    }

    function handleBackdropClick(event: MouseEvent) {
        if (event.target === event.currentTarget && !showConfirmDelete) onClose(false);
    }

    function handleKeydown(event: KeyboardEvent) {
        if (event.key === 'Escape') {
            if (showConfirmDelete) {
                showConfirmDelete = false;
            } else {
                onClose(false);
            }
        }
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
                aria-label={$t('editor.close')}
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

            <div class="table-container">
                <div class="row head">
                    <span>{$t('editor.name')}</span>
                    <span>{$t('editor.type')}</span>
                    <span>{$t('editor.fromStation')}</span>
                    <span>{$t('editor.toStation')}</span>
                    <span>{$t('editor.departAfter')}</span>
                    <span></span>
                </div>

                {#if rows.length === 0}
                    <div class="empty-state" role="status">
                        <span class="material-symbols-outlined empty-icon" aria-hidden="true">train</span>
                        <p>{$t('editor.error.noTrains')}</p>
                        <button type="button" class="add-btn" on:click={addRow}>
                            <span class="material-symbols-outlined btn-icon" aria-hidden="true">add</span>
                            <span>{$t('editor.addTrain')}</span>
                        </button>
                    </div>
                {:else}
                    <div class="trains-rows">
                        {#each rows as row, index (index)}
                            {@const isSameStation = row.fromStationId && row.fromStationId === row.toStationId}
                            <div class="row" class:has-row-error={isSameStation || !row.name.trim()}>
                                <div class="input-cell">
                                    <input
                                        type="text"
                                        maxlength="80"
                                        bind:value={row.name}
                                        class:cell-error={!row.name.trim()}
                                        placeholder={$t('editor.defaultTrainName')}
                                    />
                                </div>

                                <div class="select-cell">
                                    <select bind:value={row.type}>
                                        {#each TRAIN_TYPES as trainType (trainType)}
                                            <option value={trainType}>{trainTypeLabel(trainType, $t)}</option>
                                        {/each}
                                    </select>
                                    <span class="material-symbols-outlined select-arrow" aria-hidden="true">expand_more</span>
                                </div>

                                <div class="select-cell">
                                    <select bind:value={row.fromStationId} class:cell-error={isSameStation}>
                                        {#each stationOptions as station (station.id)}
                                            <option value={station.id}>{station.name}</option>
                                        {/each}
                                    </select>
                                    <span class="material-symbols-outlined select-arrow" aria-hidden="true">expand_more</span>
                                </div>

                                <div class="select-cell">
                                    <select bind:value={row.toStationId} class:cell-error={isSameStation}>
                                        {#each stationOptions as station (station.id)}
                                            <option value={station.id}>{station.name}</option>
                                        {/each}
                                    </select>
                                    <span class="material-symbols-outlined select-arrow" aria-hidden="true">expand_more</span>
                                </div>

                                <div class="stepper">
                                    <button
                                        type="button"
                                        class="stepper-btn"
                                        on:click={() => stepDepart(index, -5)}
                                        disabled={Number(row.departS) <= 0}
                                        title="Odejmij 5s"
                                        aria-label="Odejmij 5s"
                                    >
                                        <span class="material-symbols-outlined" aria-hidden="true">remove</span>
                                    </button>
                                    <input
                                        type="number"
                                        min="0"
                                        max="600"
                                        step="5"
                                        bind:value={row.departS}
                                        class="stepper-input"
                                    />
                                    <span class="stepper-unit">s</span>
                                    <button
                                        type="button"
                                        class="stepper-btn"
                                        on:click={() => stepDepart(index, 5)}
                                        disabled={Number(row.departS) >= 600}
                                        title="Dodaj 5s"
                                        aria-label="Dodaj 5s"
                                    >
                                        <span class="material-symbols-outlined" aria-hidden="true">add</span>
                                    </button>
                                </div>

                                <button
                                    type="button"
                                    class="remove-btn"
                                    on:click={() => removeRow(index)}
                                    title={$t('editor.removeTrainTitle')}
                                    aria-label={$t('editor.removeTrainTitle')}
                                >
                                    <span class="material-symbols-outlined" aria-hidden="true">close</span>
                                </button>
                            </div>
                        {/each}
                    </div>
                {/if}
            </div>

            {#if saveError}
                <div class="error" role="alert">
                    <span class="material-symbols-outlined error-icon" aria-hidden="true">error</span>
                    <span>{saveError}</span>
                </div>
            {/if}
        </div>

        <div class="modal-footer">
            {#if scenario !== null}
                <button
                    type="button"
                    class="danger-btn"
                    on:click={promptDelete}
                    disabled={deleting || saving}
                >
                    <span>{$t('editor.deleteScenario')}</span>
                </button>
            {:else}
                <span></span>
            {/if}
            <div class="footer-right">
                <button type="button" class="ghost-btn" on:click={() => onClose(false)} disabled={saving || deleting}>
                    {$t('editor.cancel')}
                </button>
                <button type="button" class="save-btn" on:click={handleSave} disabled={saving || deleting}>
                    <span>{saving ? $t('editor.saving') : scenario !== null ? $t('editor.saveChanges') : $t('editor.createScenario')}</span>
                </button>
            </div>
        </div>
    </div>

    {#if showConfirmDelete}
        <!-- svelte-ignore a11y_click_events_have_key_events a11y_no_static_element_interactions -->
        <div class="confirm-backdrop" on:click|stopPropagation>
            <div class="confirm-modal" role="alertdialog" aria-modal="true">
                <h4>Usunąć scenariusz?</h4>
                <p>Ta operacja trwale skasuje rozkład jazdy oraz wszystkie przypisane pociągi.</p>
                <div class="confirm-actions">
                    <button type="button" class="ghost-btn" on:click={() => (showConfirmDelete = false)} disabled={deleting}>
                        {$t('editor.cancel')}
                    </button>
                    <button type="button" class="danger-btn-solid" on:click={confirmDelete} disabled={deleting}>
                        {deleting ? $t('editor.deleting') : $t('editor.deleteScenario')}
                    </button>
                </div>
            </div>
        </div>
    {/if}
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
        position: fixed;
        inset: 0;
        z-index: 200;
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
        --modal-bg: rgba(20, 20, 20, 0.96);
        --modal-shadow: 0 24px 60px rgba(0, 0, 0, 0.7);
        --modal-title: #ffffff;
        --modal-text: #f5f7f8;
        --modal-muted: #97a5ad;
        --modal-submuted: #64748b;
        --input-bg: rgba(255, 255, 255, 0.04);
        --input-bg-focus: rgba(255, 255, 255, 0.08);
        --option-bg: #1a1a1a;
        --option-color: #f5f7f8;
        --save-btn-bg: #f4f1eb;
        --save-btn-color: #141414;
        --ghost-btn-bg: rgba(255, 255, 255, 0.04);
        --ghost-btn-hover: rgba(255, 255, 255, 0.08);
        --danger-btn-bg: rgba(222, 132, 137, 0.12);
        --danger-btn-hover: rgba(222, 132, 137, 0.22);
        --danger-color: #de8489;
        --focus-ring: rgba(255, 255, 255, 0.65);
        --sticky-head-bg: rgba(20, 20, 20, 0.98);

        width: 880px;
        height: 680px;
        max-width: calc(100vw - 32px);
        max-height: calc(100vh - 32px);

        display: flex;
        flex-direction: column;
        background: var(--modal-bg);
        border-radius: 14px;
        box-shadow: var(--modal-shadow);
        font-family: 'Inter Variable', Inter, sans-serif;
        font-weight: 300;
        color: var(--modal-text);
        box-sizing: border-box;
        position: relative;
        overflow: hidden;
        transition: background-color 200ms ease, border-color 200ms ease, color 200ms ease;
    }

    :global(html.light-mode) .modal,
    :global([data-theme='light']) .modal,
    :global(.light) .modal {
        --modal-bg: rgba(244, 245, 243, 0.98);
        --modal-shadow: 0 24px 60px rgba(0, 0, 0, 0.12);
        --modal-title: #111827;
        --modal-text: #1f2933;
        --modal-muted: #52606a;
        --modal-submuted: #8c9ba5;
        --input-bg: rgba(0, 0, 0, 0.04);
        --input-bg-focus: rgba(0, 0, 0, 0.07);
        --option-bg: #ffffff;
        --option-color: #1f2937;
        --save-btn-bg: #111827;
        --save-btn-color: #ffffff;
        --ghost-btn-bg: rgba(0, 0, 0, 0.04);
        --ghost-btn-hover: rgba(0, 0, 0, 0.08);
        --danger-btn-bg: rgba(201, 81, 88, 0.12);
        --danger-btn-hover: rgba(201, 81, 88, 0.2);
        --danger-color: #c95158;
        --focus-ring: rgba(17, 24, 39, 0.65);
        --sticky-head-bg: rgba(244, 245, 243, 0.98);
    }

    button:focus,
    input:focus,
    select:focus {
        outline: none;
    }

    button:focus-visible,
    input:focus-visible,
    select:focus-visible {
        outline: 2px solid var(--focus-ring);
        outline-offset: 2px;
    }

    .modal-header {
        display: flex;
        justify-content: space-between;
        align-items: flex-start;
        gap: 12px;
        padding: 20px 24px 14px;
        flex-shrink: 0;
    }

    .modal-label {
        margin: 0 0 4px;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        font-size: 0.66rem;
        font-weight: 300;
        color: var(--modal-muted);
    }

    h2 {
        margin: 0;
        font-size: 1.1rem;
        font-weight: 400;
        letter-spacing: 0.04em;
        text-transform: uppercase;
        color: var(--modal-title);
    }

    h3 {
        margin: 0;
        font-size: 0.72rem;
        font-weight: 300;
        color: var(--modal-muted);
        text-transform: uppercase;
        letter-spacing: 0.08em;
    }

    .close-btn {
        border: 0;
        background: transparent;
        color: var(--modal-muted);
        width: 28px;
        height: 28px;
        border-radius: 6px;
        padding: 0;
        display: flex;
        align-items: center;
        justify-content: center;
        cursor: pointer;
        flex-shrink: 0;
        transition: color 150ms ease, background-color 150ms ease;
    }

    .close-btn:hover {
        color: var(--modal-title);
        background: var(--ghost-btn-bg);
    }

    .close-btn .material-symbols-outlined {
        font-size: 19px;
    }

    .modal-body {
        padding: 8px 24px 10px;
        overflow: hidden;
        flex: 1;
        min-height: 0;
        display: flex;
        flex-direction: column;
        justify-content: flex-start;
    }

    .meta-fields {
        display: grid;
        grid-template-columns: 1fr 1fr;
        gap: 12px;
        margin-bottom: 14px;
        flex-shrink: 0;
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
        color: var(--modal-muted);
    }

    .field input {
        width: 100%;
        box-sizing: border-box;
        height: 38px;
        padding: 0 12px;
        border-radius: 8px;
        border: 0;
        background: var(--input-bg);
        color: var(--modal-text);
        font-family: inherit;
        font-size: 0.78rem;
        font-weight: 300;
        letter-spacing: 0.04em;
        text-transform: uppercase;
        transition: background-color 150ms ease;
    }

    .field input:focus {
        background: var(--input-bg-focus);
    }

    .trains-head {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 10px;
        flex-shrink: 0;
    }

    .add-btn {
        padding: 6px 12px;
        border-radius: 8px;
        border: 0;
        background: var(--ghost-btn-bg);
        color: var(--modal-muted);
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
        background: var(--ghost-btn-hover);
        color: var(--modal-title);
    }

    .add-btn:disabled {
        opacity: 0.35;
        cursor: default;
    }

    .add-btn .btn-icon {
        font-size: 16px;
    }

    .table-container {
        position: relative;
        display: flex;
        flex-direction: column;
        justify-content: flex-start;
        flex: 1;
        min-height: 0;
        overflow: hidden;
    }

    .trains-rows {
        display: grid;
        grid-auto-rows: max-content;
        align-content: start;
        gap: 6px;
        margin-top: 4px;
        overflow-y: auto;
        flex: 1;
        min-height: 0;
        padding-right: 4px;
        scrollbar-width: thin;
        scrollbar-color: rgba(255, 255, 255, 0.15) transparent;
    }

    :global(html.light-mode) .trains-rows {
        scrollbar-color: rgba(0, 0, 0, 0.15) transparent;
    }

    .trains-rows::-webkit-scrollbar {
        width: 5px;
    }

    .trains-rows::-webkit-scrollbar-thumb {
        background: rgba(255, 255, 255, 0.15);
        border-radius: 999px;
    }

    :global(html.light-mode) .trains-rows::-webkit-scrollbar-thumb {
        background: rgba(0, 0, 0, 0.15);
    }

    .row {
        display: grid;
        grid-template-columns: 1.4fr 1.1fr 1.25fr 1.25fr 130px 28px;
        gap: 8px;
        align-items: center;
        height: 38px;
    }

    .row.head {
        position: sticky;
        top: 0;
        z-index: 10;
        background: var(--sticky-head-bg);
        font-size: 0.66rem;
        font-weight: 400;
        color: var(--modal-submuted);
        text-transform: uppercase;
        letter-spacing: 0.08em;
        padding: 6px 4px;
        margin-bottom: 2px;
        height: auto;
        flex-shrink: 0;
    }

    .input-cell {
        width: 100%;
    }

    .input-cell input {
        width: 100%;
        box-sizing: border-box;
        height: 38px;
        padding: 0 12px;
        border-radius: 8px;
        border: 0;
        background: var(--input-bg);
        color: var(--modal-text);
        font-family: inherit;
        font-size: 0.78rem;
        font-weight: 300;
        letter-spacing: 0.04em;
        text-transform: uppercase;
    }

    .input-cell input:focus {
        background: var(--input-bg-focus);
    }

    .select-cell {
        position: relative;
        width: 100%;
        display: flex;
        align-items: center;
    }

    .select-cell select {
        width: 100%;
        box-sizing: border-box;
        height: 38px;
        padding: 0 28px 0 12px;
        border-radius: 8px;
        border: 0;
        background: var(--input-bg);
        color: var(--modal-text);
        font-family: inherit;
        font-size: 0.78rem;
        font-weight: 300;
        letter-spacing: 0.04em;
        text-transform: uppercase;
        cursor: pointer;
        appearance: none;
        -webkit-appearance: none;
        -moz-appearance: none;
    }

    .select-cell select:focus {
        background: var(--input-bg-focus);
    }

    .select-cell select option {
        background: var(--option-bg);
        color: var(--option-color);
        padding: 8px 12px;
    }

    .select-arrow {
        position: absolute;
        right: 8px;
        pointer-events: none;
        font-size: 18px;
        color: var(--modal-muted);
    }

    .stepper {
        display: flex;
        align-items: center;
        height: 38px;
        border-radius: 8px;
        background: var(--input-bg);
        padding: 0 4px;
        box-sizing: border-box;
    }

    .stepper-btn {
        width: 26px;
        height: 26px;
        border-radius: 6px;
        border: 0;
        background: transparent;
        color: var(--modal-muted);
        display: flex;
        align-items: center;
        justify-content: center;
        cursor: pointer;
        padding: 0;
        transition: background-color 150ms ease, color 150ms ease;
    }

    .stepper-btn:hover:not(:disabled) {
        background: var(--ghost-btn-hover);
        color: var(--modal-title);
    }

    .stepper-btn:disabled {
        opacity: 0.3;
        cursor: default;
    }

    .stepper-btn .material-symbols-outlined {
        font-size: 15px;
    }

    .stepper-input {
        flex: 1;
        width: 100%;
        min-width: 0;
        height: 100%;
        border: 0;
        background: transparent;
        color: var(--modal-text);
        font-family: inherit;
        font-size: 0.78rem;
        font-weight: 400;
        text-align: center;
        padding: 0;
        -moz-appearance: textfield;
        appearance: textfield;
    }

    .stepper-input::-webkit-outer-spin-button,
    .stepper-input::-webkit-inner-spin-button {
        -webkit-appearance: none;
        margin: 0;
    }

    .stepper-unit {
        font-size: 0.7rem;
        color: var(--modal-submuted);
        margin-right: 4px;
        user-select: none;
    }

    .cell-error {
        background: rgba(222, 132, 137, 0.15) !important;
        color: var(--danger-color) !important;
    }

    .remove-btn {
        border: 0;
        background: transparent;
        color: var(--modal-muted);
        width: 28px;
        height: 28px;
        border-radius: 6px;
        padding: 0;
        display: flex;
        align-items: center;
        justify-content: center;
        cursor: pointer;
        transition: color 150ms ease, background-color 150ms ease;
    }

    .remove-btn:hover {
        color: var(--danger-color);
        background: var(--danger-btn-bg);
    }

    .remove-btn .material-symbols-outlined {
        font-size: 18px;
    }

    .empty-state {
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        flex: 1;
        padding: 20px;
        gap: 10px;
        color: var(--modal-submuted);
        text-align: center;
    }

    .empty-icon {
        font-size: 34px;
        opacity: 0.6;
    }

    .empty-state p {
        margin: 0;
        font-size: 0.78rem;
        text-transform: uppercase;
        letter-spacing: 0.04em;
    }

    .error {
        margin: 10px 0 0;
        padding: 10px 14px;
        border-radius: 8px;
        background: var(--danger-btn-bg);
        border: 0;
        color: var(--danger-color);
        font-size: 0.74rem;
        font-weight: 400;
        letter-spacing: 0.02em;
        text-transform: uppercase;
        line-height: 1.4;
        display: flex;
        align-items: center;
        gap: 8px;
        flex-shrink: 0;
    }

    .error-icon {
        font-size: 18px;
        flex-shrink: 0;
    }

    .modal-footer {
        display: flex;
        justify-content: space-between;
        align-items: center;
        gap: 10px;
        padding: 16px 24px 20px;
        flex-shrink: 0;
    }

    .footer-right {
        display: flex;
        gap: 8px;
    }

    .save-btn {
        padding: 8px 18px;
        border-radius: 8px;
        border: 0;
        background: var(--save-btn-bg);
        color: var(--save-btn-color);
        font-family: inherit;
        font-weight: 500;
        font-size: 0.74rem;
        letter-spacing: 0.06em;
        text-transform: uppercase;
        cursor: pointer;
        opacity: 1;
        transition: opacity 160ms ease, background-color 160ms ease;
    }

    .save-btn:hover:not(:disabled) {
        opacity: 0.85;
    }

    .save-btn:active:not(:disabled) {
        opacity: 0.65;
    }

    .save-btn:disabled {
        opacity: 0.35;
        cursor: default;
    }

    .ghost-btn {
        padding: 8px 14px;
        border-radius: 8px;
        border: 0;
        background: var(--ghost-btn-bg);
        color: var(--modal-muted);
        font-family: inherit;
        font-size: 0.72rem;
        font-weight: 300;
        letter-spacing: 0.06em;
        text-transform: uppercase;
        cursor: pointer;
        opacity: 1;
        transition: opacity 160ms ease, background-color 160ms ease, color 160ms ease;
    }

    .ghost-btn:hover:not(:disabled) {
        background: var(--ghost-btn-hover);
        color: #ffffff;
        opacity: 0.9;
    }

    :global(html.light-mode) .ghost-btn:hover:not(:disabled) {
        color: #111827;
    }

    .ghost-btn:active:not(:disabled) {
        opacity: 0.65;
    }

    .ghost-btn:disabled {
        opacity: 0.35;
        cursor: default;
    }

    .danger-btn {
        padding: 8px 14px;
        border-radius: 8px;
        border: 0;
        background: var(--danger-btn-bg);
        color: var(--danger-color);
        font-family: inherit;
        font-weight: 400;
        font-size: 0.72rem;
        letter-spacing: 0.06em;
        text-transform: uppercase;
        cursor: pointer;
        opacity: 1;
        transition: opacity 160ms ease, background-color 160ms ease;
    }

    .danger-btn:hover:not(:disabled) {
        background: var(--danger-btn-hover);
        opacity: 0.9;
    }

    .danger-btn:active:not(:disabled) {
        opacity: 0.7;
    }

    .danger-btn:disabled {
        opacity: 0.35;
        cursor: default;
    }

    .confirm-backdrop {
        position: absolute;
        inset: 0;
        background: rgba(0, 0, 0, 0.6);
        backdrop-filter: blur(4px);
        border-radius: 14px;
        display: flex;
        align-items: center;
        justify-content: center;
        z-index: 50;
        padding: 20px;
        box-sizing: border-box;
    }

    .confirm-modal {
        background: var(--modal-bg);
        padding: 24px;
        border-radius: 12px;
        max-width: 380px;
        box-shadow: 0 16px 40px rgba(0, 0, 0, 0.5);
        text-align: center;
    }

    .confirm-modal h4 {
        margin: 0 0 8px;
        font-size: 0.95rem;
        font-weight: 500;
        text-transform: uppercase;
        letter-spacing: 0.04em;
        color: var(--modal-title);
    }

    .confirm-modal p {
        margin: 0 0 20px;
        font-size: 0.76rem;
        color: var(--modal-muted);
        line-height: 1.4;
    }

    .confirm-actions {
        display: flex;
        justify-content: center;
        gap: 10px;
    }

    .danger-btn-solid {
        padding: 8px 16px;
        border-radius: 8px;
        border: 0;
        background: var(--danger-color);
        color: #ffffff;
        font-family: inherit;
        font-weight: 500;
        font-size: 0.72rem;
        letter-spacing: 0.06em;
        text-transform: uppercase;
        cursor: pointer;
        opacity: 1;
        transition: opacity 150ms ease;
    }

    .danger-btn-solid:hover:not(:disabled) {
        opacity: 0.85;
    }

    .danger-btn-solid:active:not(:disabled) {
        opacity: 0.65;
    }

    @media (max-width: 760px) {
        .modal {
            width: 100%;
            height: calc(100vh - 32px);
        }

        .meta-fields {
            grid-template-columns: 1fr;
        }

        .row {
            grid-template-columns: 1fr 1fr;
            height: auto;
        }

        .row.head {
            display: none;
        }
    }
</style>