import { get } from 'svelte/store';
import { describe, expect, it } from 'vitest';
import { locale, localizedScenarioField, setLocale, t } from './index';

describe('i18n', () => {
	it('switches language and interpolates parameters', () => {
		setLocale('en');
		expect(get(locale)).toBe('en');
		expect(get(t)('details.upTo', { speed: 80 })).toBe('up to 80 km/h');

		setLocale('pl');
		expect(get(t)('details.upTo', { speed: 80 })).toBe('do 80 km/h');
	});

	it('localizes built-in scenarios and preserves user-defined content', () => {
		setLocale('en');
		const translator = get(t);

		expect(
			localizedScenarioField('ROZKLAD_BESKIDY', 'name', 'Beskidy i południe', translator)
		).toBe('Beskids and the south');
		expect(localizedScenarioField('ROZKLAD_CUSTOM', 'name', 'My scenario', translator)).toBe(
			'My scenario'
		);
	});
});
