import type { TrainStatus } from './train';

export type Selected =
	| { kind: 'station'; id: string }
	| { kind: 'segment'; id: string }
	| { kind: 'train'; id: string };

/** Filtr podświetlenia sterowany chipami w pasku górnym: wyróżnia na mapie
 *  pociągi o danym statusie albo wszystko, co jest dotknięte incydentem. */
export type HighlightFilter = { kind: 'train-status'; status: TrainStatus } | { kind: 'incidents' };
