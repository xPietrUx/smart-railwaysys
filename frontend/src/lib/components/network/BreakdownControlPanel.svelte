<script lang="ts">
	import type { StationNode, TrackSegment } from '$lib/types/network';
	import { updateSegmentStatus, resetAllSegmentsStatus } from '$lib/services/network';

	export let stations: StationNode[] = [];
	export let segments: TrackSegment[] = [];
	export let onSegmentUpdated: (segmentId: string, newStatus: 'active' | 'blocked') => void = () => {};
	export let onResetAll: () => void = () => {};

	let selectedSegmentId = segments.length > 0 ? segments[0].segmentId : '';
	let loading = false;
	let resetting = false;

	$: stationNameMap = new Map(stations.map((s) => [s.id, s.name]));
	$: selectedSeg = segments.find((s) => s.segmentId === selectedSegmentId) ?? segments[0] ?? null;
	$: blockedSegments = segments.filter((s) => s.status === 'blocked');

	function formatSegLabel(seg: TrackSegment) {
		const srcName = stationNameMap.get(seg.source) ?? seg.source;
		const tgtName = stationNameMap.get(seg.target) ?? seg.target;
		return `${seg.segmentId} · ${srcName} ⇄ ${tgtName} (${seg.distKm} km)`;
	}

	async function handleToggle(seg: TrackSegment) {
		if (loading) return;
		loading = true;
		try {
			const baseUrl = import.meta.env.VITE_API_URL ?? 'http://localhost:8000';
			const newStatus = seg.status === 'active' ? 'blocked' : 'active';
			await updateSegmentStatus(fetch, baseUrl, seg.segmentId, newStatus);
			onSegmentUpdated(seg.segmentId, newStatus);
		} catch (err) {
			alert('Błąd aktualizacji statusu: ' + (err instanceof Error ? err.message : err));
		} finally {
			loading = false;
		}
	}

	async function handleResetAll() {
		if (resetting) return;
		resetting = true;
		try {
			const baseUrl = import.meta.env.VITE_API_URL ?? 'http://localhost:8000';
			await resetAllSegmentsStatus(fetch, baseUrl);
			onResetAll();
		} catch (err) {
			alert('Błąd resetowania sieci: ' + (err instanceof Error ? err.message : err));
		} finally {
			resetting = false;
		}
	}
</script>

<div class="breakdown-panel">
	<div class="panel-header">
		<div class="header-title">
			<span class="icon">🚧</span>
			<div>
				<h3>Symulacja Awarii (What-If)</h3>
				<p class="subtitle">Zablokuj odcinek, aby przetestować dynamiczny rerouting A*</p>
			</div>
		</div>
		{#if blockedSegments.length > 0}
			<span class="blocked-counter">{blockedSegments.length} zablokowane</span>
		{/if}
	</div>

	<!-- Wybór odcinka do zablokowania/odblokowania -->
	<div class="selector-section">
		<label for="seg-select">Wybierz odcinek toru z sieci:</label>
		<div class="select-row">
			<select id="seg-select" bind:value={selectedSegmentId}>
				{#each segments as seg}
					<option value={seg.segmentId}>
						{seg.status === 'blocked' ? '🔴 [ZABLOKOWANY]' : '🟢'} {formatSegLabel(seg)}
					</option>
				{/each}
			</select>
		</div>

		{#if selectedSeg}
			<div class="seg-action-card" class:blocked-card={selectedSeg.status === 'blocked'}>
				<div class="seg-info">
					<span class="seg-name">{formatSegLabel(selectedSeg)}</span>
					<span class="status-badge" class:blocked={selectedSeg.status === 'blocked'}>
						{selectedSeg.status === 'blocked' ? 'Zablokowany (Awaria)' : 'Aktywny (Przejezdny)'}
					</span>
				</div>
				<button
					type="button"
					class="toggle-btn"
					class:btn-block={selectedSeg.status === 'active'}
					class:btn-unblock={selectedSeg.status === 'blocked'}
					on:click={() => selectedSeg && handleToggle(selectedSeg)}
					disabled={loading}
				>
					{#if loading}
						Zmiana stanu...
					{:else if selectedSeg.status === 'active'}
						⚡ Wywołaj Awarię (Zablokuj tor)
					{:else}
						✅ Napraw Tor (Odblokuj)
					{/if}
				</button>
			</div>
		{/if}
	</div>

	<!-- Lista aktualnie zablokowanych torów -->
	<div class="blocked-list-section">
		<span class="list-title">Aktywne awarie w sieci:</span>
		{#if blockedSegments.length === 0}
			<div class="clean-state">
				<span>✅ Wszystkie szlaki kolejowe są przejezdne</span>
			</div>
		{:else}
			<div class="blocked-pills">
				{#each blockedSegments as bseg}
					<div class="blocked-pill">
						<div class="pill-info">
							<strong>{bseg.segmentId}</strong>
							<span>{stationNameMap.get(bseg.source)} ⇄ {stationNameMap.get(bseg.target)}</span>
						</div>
						<button
							type="button"
							class="fix-btn"
							on:click={() => handleToggle(bseg)}
							disabled={loading}
							title="Odblokuj tor"
						>
							Napraw 🔧
						</button>
					</div>
				{/each}
			</div>
		{/if}
	</div>

	{#if blockedSegments.length > 0}
		<div class="reset-section">
			<button
				type="button"
				class="reset-btn"
				on:click={handleResetAll}
				disabled={resetting}
			>
				🔄 Odblokuj całą sieć (Reset awarii)
			</button>
		</div>
	{/if}
</div>

<style>
	.breakdown-panel {
		background: rgba(17, 24, 39, 0.85);
		backdrop-filter: blur(12px);
		border: 1px solid rgba(239, 68, 68, 0.25);
		border-radius: 16px;
		padding: 20px;
		color: #f3f4f6;
		box-shadow: 0 10px 30px rgba(0, 0, 0, 0.35);
		font-family: system-ui, -apple-system, sans-serif;
	}

	.panel-header {
		display: flex;
		align-items: center;
		justify-content: space-between;
		margin-bottom: 16px;
		padding-bottom: 12px;
		border-bottom: 1px solid rgba(255, 255, 255, 0.08);
	}

	.header-title {
		display: flex;
		align-items: center;
		gap: 12px;
	}

	.icon {
		font-size: 1.6rem;
	}

	h3 {
		margin: 0;
		font-size: 1.1rem;
		font-weight: 700;
		color: #ffffff;
	}

	.subtitle {
		margin: 2px 0 0;
		font-size: 0.78rem;
		color: #9ca3af;
	}

	.blocked-counter {
		background: rgba(239, 68, 68, 0.2);
		border: 1px solid #ef4444;
		color: #fca5a5;
		font-weight: 700;
		font-size: 0.75rem;
		padding: 4px 10px;
		border-radius: 20px;
	}

	.selector-section {
		margin-bottom: 16px;
	}

	label {
		display: block;
		font-size: 0.78rem;
		font-weight: 600;
		color: #9ca3af;
		text-transform: uppercase;
		letter-spacing: 0.5px;
		margin-bottom: 8px;
	}

	.select-row select {
		width: 100%;
		background: rgba(15, 23, 42, 0.9);
		border: 1px solid rgba(255, 255, 255, 0.18);
		border-radius: 10px;
		color: #ffffff;
		padding: 10px 12px;
		font-size: 0.88rem;
		outline: none;
		transition: border-color 0.2s;
	}

	.select-row select:focus {
		border-color: #ef4444;
	}

	.seg-action-card {
		margin-top: 12px;
		background: rgba(255, 255, 255, 0.04);
		border: 1px solid rgba(255, 255, 255, 0.1);
		border-radius: 12px;
		padding: 14px;
		display: flex;
		flex-direction: column;
		gap: 12px;
		transition: all 0.2s;
	}

	.seg-action-card.blocked-card {
		background: rgba(239, 68, 68, 0.08);
		border-color: rgba(239, 68, 68, 0.35);
	}

	.seg-info {
		display: flex;
		justify-content: space-between;
		align-items: center;
		gap: 8px;
	}

	.seg-name {
		font-size: 0.85rem;
		font-weight: 600;
		color: #e5e7eb;
	}

	.status-badge {
		font-size: 0.72rem;
		font-weight: 700;
		background: rgba(16, 185, 129, 0.15);
		color: #34d399;
		border: 1px solid rgba(16, 185, 129, 0.3);
		padding: 2px 8px;
		border-radius: 6px;
	}

	.status-badge.blocked {
		background: rgba(239, 68, 68, 0.2);
		color: #f87171;
		border-color: rgba(239, 68, 68, 0.4);
	}

	.toggle-btn {
		width: 100%;
		padding: 10px;
		border-radius: 8px;
		font-weight: 600;
		font-size: 0.88rem;
		cursor: pointer;
		transition: all 0.2s;
	}

	.btn-block {
		background: linear-gradient(135deg, #ef4444, #dc2626);
		border: none;
		color: #ffffff;
		box-shadow: 0 4px 12px rgba(220, 38, 38, 0.3);
	}

	.btn-block:hover:not(:disabled) {
		background: linear-gradient(135deg, #f87171, #ef4444);
	}

	.btn-unblock {
		background: linear-gradient(135deg, #10b981, #059669);
		border: none;
		color: #ffffff;
		box-shadow: 0 4px 12px rgba(16, 185, 129, 0.3);
	}

	.btn-unblock:hover:not(:disabled) {
		background: linear-gradient(135deg, #34d399, #10b981);
	}

	.blocked-list-section {
		border-top: 1px solid rgba(255, 255, 255, 0.08);
		padding-top: 14px;
	}

	.list-title {
		display: block;
		font-size: 0.75rem;
		color: #9ca3af;
		margin-bottom: 8px;
	}

	.clean-state {
		background: rgba(16, 185, 129, 0.1);
		border: 1px solid rgba(16, 185, 129, 0.25);
		border-radius: 8px;
		padding: 10px 14px;
		font-size: 0.82rem;
		color: #6ee7b7;
	}

	.blocked-pills {
		display: flex;
		flex-direction: column;
		gap: 8px;
	}

	.blocked-pill {
		display: flex;
		align-items: center;
		justify-content: space-between;
		background: rgba(239, 68, 68, 0.12);
		border: 1px solid rgba(239, 68, 68, 0.3);
		border-radius: 8px;
		padding: 8px 12px;
	}

	.pill-info {
		display: flex;
		flex-direction: column;
		gap: 2px;
	}

	.pill-info strong {
		color: #fca5a5;
		font-size: 0.85rem;
	}

	.pill-info span {
		color: #d1d5db;
		font-size: 0.76rem;
	}

	.fix-btn {
		background: rgba(16, 185, 129, 0.2);
		border: 1px solid #10b981;
		color: #6ee7b7;
		padding: 6px 12px;
		border-radius: 6px;
		font-size: 0.78rem;
		font-weight: 600;
		cursor: pointer;
		transition: all 0.2s;
	}

	.fix-btn:hover:not(:disabled) {
		background: #10b981;
		color: #ffffff;
	}

	.reset-section {
		margin-top: 14px;
	}

	.reset-btn {
		width: 100%;
		background: rgba(255, 255, 255, 0.06);
		border: 1px solid rgba(255, 255, 255, 0.15);
		color: #e5e7eb;
		padding: 10px;
		border-radius: 8px;
		font-weight: 600;
		font-size: 0.85rem;
		cursor: pointer;
		transition: all 0.2s;
	}

	.reset-btn:hover:not(:disabled) {
		background: rgba(255, 255, 255, 0.12);
		color: #ffffff;
	}
</style>
