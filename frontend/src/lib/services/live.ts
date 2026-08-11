import { writable, type Readable } from 'svelte/store';
import type { RailEventNode } from '$lib/types/event';
import type { ActiveScenarioInfo } from '$lib/types/scenario';
import type { TrainNode } from '$lib/types/train';

export type ConnectionStatus = 'connecting' | 'open' | 'reconnecting' | 'polling-fallback';

export type LiveSnapshot = {
	trains: TrainNode[];
	events: RailEventNode[];
	scenario: ActiveScenarioInfo | null;
	paused: boolean;
	/** Mnożnik tempa symulacji (0.5–2). */
	speed: number;
	/** Zegar symulacji w minutach (tempo skalowane prędkością, bez okresów pauzy). */
	simClockMinutes: number;
	timestamp: number;
};

export type LiveStore = {
	snapshot: Readable<LiveSnapshot>;
	status: Readable<ConnectionStatus>;
	connect: () => void;
	disconnect: () => void;
};

const MAX_BACKOFF_MS = 15_000;
const FAILURES_BEFORE_POLLING_FALLBACK = 4;
const POLL_INTERVAL_MS = 2_000;
const WS_RETRY_WHILE_POLLING_MS = 20_000;

export async function fetchTrainsSnapshot(
	fetchFn: typeof fetch,
	baseUrl: string
): Promise<{ trains: TrainNode[]; timestamp: number }> {
	const response = await fetchFn(`${baseUrl}/api/trains`);
	if (!response.ok) {
		throw new Error(`API pociągów zwróciło ${response.status}`);
	}
	return response.json();
}

export async function fetchEventsSnapshot(
	fetchFn: typeof fetch,
	baseUrl: string
): Promise<{ events: RailEventNode[]; timestamp: number }> {
	const response = await fetchFn(`${baseUrl}/api/events`);
	if (!response.ok) {
		throw new Error(`API zdarzeń zwróciło ${response.status}`);
	}
	return response.json();
}

function deriveWsUrl(baseUrl: string): string {
	return baseUrl.replace(/^http/, 'ws') + '/ws/live';
}

/**
 * Domyślnie napędza widok przez WebSocket (push z serwera po każdym ticku
 * symulacji). Jeśli WS się nie łączy, po kilku próbach cicho przełącza się na
 * odpytywanie REST co POLL_INTERVAL_MS, jednocześnie w tle nadal próbując co
 * jakiś czas wrócić na WebSocket.
 */
export function createLiveStore(
	fetchFn: typeof fetch,
	baseUrl: string,
	initial: LiveSnapshot
): LiveStore {
	const snapshotStore = writable<LiveSnapshot>(initial);
	const statusStore = writable<ConnectionStatus>('connecting');
	const wsUrl = deriveWsUrl(baseUrl);

	let socket: WebSocket | null = null;
	let reconnectAttempts = 0;
	let reconnectTimer: ReturnType<typeof setTimeout> | null = null;
	let pollTimer: ReturnType<typeof setInterval> | null = null;
	let wsRetryWhilePollingTimer: ReturnType<typeof setInterval> | null = null;
	let stopped = true;

	function clearAllTimers() {
		if (reconnectTimer) clearTimeout(reconnectTimer);
		if (pollTimer) clearInterval(pollTimer);
		if (wsRetryWhilePollingTimer) clearInterval(wsRetryWhilePollingTimer);
		reconnectTimer = null;
		pollTimer = null;
		wsRetryWhilePollingTimer = null;
	}

	async function pollOnce() {
		try {
			const [trainsData, eventsData] = await Promise.all([
				fetchTrainsSnapshot(fetchFn, baseUrl),
				fetchEventsSnapshot(fetchFn, baseUrl)
			]);
			// REST nie zna statusu scenariusza ani pauzy — zachowujemy ostatnie znane.
			snapshotStore.update((prev) => ({
				trains: trainsData.trains,
				events: eventsData.events,
				scenario: prev.scenario,
				paused: prev.paused,
				speed: prev.speed,
				simClockMinutes: prev.simClockMinutes,
				timestamp: trainsData.timestamp
			}));
		} catch {
			// Cicho pomijamy -- spróbujemy ponownie przy następnym pollu albo WS.
		}
	}

	function startPollingFallback() {
		if (pollTimer) return;
		statusStore.set('polling-fallback');
		void pollOnce();
		pollTimer = setInterval(pollOnce, POLL_INTERVAL_MS);
		if (!wsRetryWhilePollingTimer) {
			wsRetryWhilePollingTimer = setInterval(() => {
				reconnectAttempts = 0;
				openSocket();
			}, WS_RETRY_WHILE_POLLING_MS);
		}
	}

	function scheduleReconnect() {
		if (stopped) return;
		reconnectAttempts += 1;
		if (reconnectAttempts >= FAILURES_BEFORE_POLLING_FALLBACK) {
			startPollingFallback();
			return;
		}
		statusStore.set('reconnecting');
		const delay = Math.min(1000 * 2 ** (reconnectAttempts - 1), MAX_BACKOFF_MS);
		reconnectTimer = setTimeout(openSocket, delay);
	}

	function openSocket() {
		if (stopped) return;
		try {
			socket = new WebSocket(wsUrl);
		} catch {
			scheduleReconnect();
			return;
		}

		socket.addEventListener('open', () => {
			reconnectAttempts = 0;
			if (pollTimer) {
				clearInterval(pollTimer);
				pollTimer = null;
			}
			if (wsRetryWhilePollingTimer) {
				clearInterval(wsRetryWhilePollingTimer);
				wsRetryWhilePollingTimer = null;
			}
			statusStore.set('open');
		});

		socket.addEventListener('message', (event) => {
			try {
				const payload = JSON.parse(event.data);
				if (payload.type === 'snapshot' || payload.type === 'tick') {
					snapshotStore.set({
						trains: payload.trains,
						events: payload.events,
						scenario: payload.scenario ?? null,
						paused: payload.paused ?? false,
						speed: payload.speed ?? 1,
						simClockMinutes: payload.simClockMinutes ?? 0,
						timestamp: payload.timestamp
					});
				}
			} catch {
				// Ignorujemy niepoprawną ramkę -- kolejna powinna być poprawna.
			}
		});

		socket.addEventListener('close', () => scheduleReconnect());
		socket.addEventListener('error', () => socket?.close());
	}

	function connect() {
		if (!stopped) return;
		stopped = false;
		openSocket();
	}

	function disconnect() {
		stopped = true;
		clearAllTimers();
		socket?.close();
		socket = null;
	}

	return {
		snapshot: { subscribe: snapshotStore.subscribe },
		status: { subscribe: statusStore.subscribe },
		connect,
		disconnect
	};
}
