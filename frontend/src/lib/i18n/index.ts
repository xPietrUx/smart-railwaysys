import { browser } from '$app/environment';
import { derived, get, writable } from 'svelte/store';
import en from './locales/en.json';
import pl from './locales/pl.json';

export type Locale = 'pl' | 'en';
export type TranslationKey = keyof typeof pl;
export type TranslationParams = Record<string, string | number>;
export type Translator = (key: TranslationKey, params?: TranslationParams) => string;

const STORAGE_KEY = 'smart-railway.locale';
const dictionaries: Record<Locale, Record<TranslationKey, string>> = { pl, en };

export const locale = writable<Locale>('pl');

function render(key: TranslationKey, selectedLocale: Locale, params: TranslationParams = {}) {
	const template = dictionaries[selectedLocale][key] ?? dictionaries.pl[key] ?? key;
	return template.replace(/\{\{(\w+)\}\}/g, (_, name: string) =>
		String(params[name] ?? `{{${name}}}`)
	);
}

export const t = derived(locale, ($locale): Translator => {
	return (key, params) => render(key, $locale, params);
});

export function translate(key: TranslationKey, params?: TranslationParams): string {
	return render(key, get(locale), params);
}

export function setLocale(nextLocale: Locale): void {
	locale.set(nextLocale);
	if (!browser) return;
	try {
		localStorage.setItem(STORAGE_KEY, nextLocale);
	} catch {
		// Zmiana języka nadal działa, gdy przeglądarka blokuje pamięć lokalną.
	}
	document.documentElement.lang = nextLocale;
}

export function initLocale(): void {
	if (!browser) return;
	let stored: string | null = null;
	try {
		stored = localStorage.getItem(STORAGE_KEY);
	} catch {
		// Preferencja przeglądarki pozostaje bezpiecznym ustawieniem domyślnym.
	}
	const preferred: Locale =
		stored === 'pl' || stored === 'en'
			? stored
			: navigator.language.toLowerCase().startsWith('en')
				? 'en'
				: 'pl';
	setLocale(preferred);
}

export function localizedScenarioField(
	id: string,
	field: 'name' | 'description',
	fallback: string,
	translator: Translator
): string {
	const key = `scenario.${id}.${field}` as TranslationKey;
	return Object.prototype.hasOwnProperty.call(pl, key) ? translator(key) : fallback;
}
