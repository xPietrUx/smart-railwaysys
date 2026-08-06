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
				✕
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
					➕ {$t('editor.addTrain')}
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
							✕
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
					{deleting ? $t('editor.deleting') : `🗑 ${$t('editor.deleteScenario')}`}
				</button>
			{:else}
				<span></span>
			{/if}
			<div class="footer-right">
				<button type="button" class="ghost-btn" on:click={() => onClose(false)}
					>{$t('editor.cancel')}</button
				>
				<button type="button" class="save-btn" on:click={handleSave} disabled={saving || deleting}>
					{saving
						? $t('editor.saving')
						: scenario !== null
							? `💾 ${$t('editor.saveChanges')}`
							: `💾 ${$t('editor.createScenario')}`}
				</button>
			</div>
		</div>
	</div>
</div>

<style>
	.overlay {
		position: absolute;
		inset: 0;
		z-index: 40;
		background: rgba(2, 6, 23, 0.6);
		backdrop-filter: blur(3px);
		display: flex;
		align-items: center;
		justify-content: center;
		padding: 20px;
	}

	.modal {
		width: min(760px, 94vw);
		max-height: min(84vh, 720px);
		display: flex;
		flex-direction: column;
		background: rgba(15, 23, 42, 0.97);
		border: 1px solid rgba(148, 163, 184, 0.25);
		border-radius: 18px;
		box-shadow: 0 30px 80px rgba(2, 6, 23, 0.7);
	}

	.modal-header {
		display: flex;
		justify-content: space-between;
		align-items: flex-start;
		gap: 12px;
		padding: 18px 20px 12px;
		border-bottom: 1px solid rgba(148, 163, 184, 0.15);
	}

	.modal-label {
		margin: 0 0 4px;
		text-transform: uppercase;
		letter-spacing: 0.14em;
		font-size: 0.7rem;
		color: #93c5fd;
	}

	h2 {
		margin: 0;
		font-size: 1.15rem;
	}

	h3 {
		margin: 0;
		font-size: 0.85rem;
		color: #94a3b8;
		text-transform: uppercase;
		letter-spacing: 0.08em;
	}

	.close-btn {
		padding: 6px 10px;
		border-radius: 9px;
		border: 1px solid rgba(148, 163, 184, 0.3);
		background: rgba(51, 65, 85, 0.6);
		color: #cbd5e1;
		font-size: 0.85rem;
		cursor: pointer;
	}

	.close-btn:hover {
		border-color: rgba(239, 68, 68, 0.6);
		color: #fca5a5;
	}

	.modal-body {
		padding: 14px 20px;
		overflow-y: auto;
		min-height: 0;
	}

	.meta-fields {
		display: grid;
		grid-template-columns: 1fr 1fr;
		gap: 10px;
		margin-bottom: 14px;
	}

	.field {
		display: grid;
		gap: 4px;
	}

	.field span {
		font-size: 0.74rem;
		color: #94a3b8;
	}

	input,
	select {
		width: 100%;
		box-sizing: border-box;
		padding: 7px 9px;
		border-radius: 9px;
		border: 1px solid rgba(148, 163, 184, 0.25);
		background: rgba(30, 41, 59, 0.8);
		color: #e5eefb;
		font: inherit;
		font-size: 0.82rem;
	}

	input:focus,
	select:focus {
		outline: none;
		border-color: rgba(96, 165, 250, 0.7);
	}

	.trains-head {
		display: flex;
		justify-content: space-between;
		align-items: center;
		margin-bottom: 8px;
	}

	.add-btn {
		padding: 6px 12px;
		border-radius: 10px;
		border: 1px dashed rgba(96, 165, 250, 0.5);
		background: rgba(30, 58, 138, 0.25);
		color: #bfdbfe;
		font-size: 0.78rem;
		font-weight: 600;
		cursor: pointer;
	}

	.add-btn:hover:not(:disabled) {
		border-color: rgba(96, 165, 250, 0.9);
	}

	.add-btn:disabled {
		opacity: 0.5;
		cursor: default;
	}

	.trains-table {
		display: grid;
		gap: 6px;
	}

	.row {
		display: grid;
		grid-template-columns: 1.4fr 0.9fr 1.1fr 1.1fr 0.7fr 32px;
		gap: 6px;
		align-items: center;
	}

	.row.head {
		font-size: 0.7rem;
		color: #94a3b8;
		text-transform: uppercase;
		letter-spacing: 0.06em;
		padding: 0 2px;
	}

	.remove-btn {
		padding: 6px 0;
		border-radius: 8px;
		border: 1px solid rgba(148, 163, 184, 0.25);
		background: rgba(51, 65, 85, 0.5);
		color: #cbd5e1;
		font-size: 0.78rem;
		cursor: pointer;
	}

	.remove-btn:hover {
		border-color: rgba(239, 68, 68, 0.6);
		color: #fca5a5;
	}

	.error {
		margin: 12px 0 0;
		padding: 8px 10px;
		border-radius: 10px;
		background: rgba(127, 29, 29, 0.35);
		border: 1px solid rgba(239, 68, 68, 0.45);
		color: #fecaca;
		font-size: 0.82rem;
		line-height: 1.4;
	}

	.modal-footer {
		display: flex;
		justify-content: space-between;
		align-items: center;
		gap: 10px;
		padding: 12px 20px 16px;
		border-top: 1px solid rgba(148, 163, 184, 0.15);
	}

	.footer-right {
		display: flex;
		gap: 8px;
	}

	.save-btn {
		padding: 8px 16px;
		border-radius: 10px;
		border: 1px solid rgba(52, 211, 153, 0.5);
		background: rgba(6, 78, 59, 0.5);
		color: #6ee7b7;
		font-weight: 700;
		font-size: 0.84rem;
		cursor: pointer;
	}

	.save-btn:hover:not(:disabled) {
		border-color: rgba(52, 211, 153, 0.9);
	}

	.save-btn:disabled {
		opacity: 0.6;
		cursor: default;
	}

	.danger-btn {
		padding: 8px 14px;
		border-radius: 10px;
		border: 1px solid rgba(239, 68, 68, 0.5);
		background: rgba(127, 29, 29, 0.35);
		color: #fca5a5;
		font-weight: 600;
		font-size: 0.82rem;
		cursor: pointer;
	}

	.danger-btn:hover:not(:disabled) {
		border-color: rgba(239, 68, 68, 0.9);
	}

	.danger-btn:disabled {
		opacity: 0.6;
		cursor: default;
	}

	.ghost-btn {
		padding: 8px 14px;
		border-radius: 10px;
		border: 1px solid rgba(148, 163, 184, 0.3);
		background: transparent;
		color: #cbd5e1;
		font-size: 0.82rem;
		cursor: pointer;
	}

	.ghost-btn:hover {
		border-color: rgba(96, 165, 250, 0.6);
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
