export type TrainPlanType = 'REGIONAL' | 'IC' | 'FREIGHT';

/** Jeden pociąg rozkładu — kursuje cyklicznie na relacji from->to,
 *  wjeżdża na sieć departS sekund po uruchomieniu scenariusza. */
export type TrainPlan = {
	name: string;
	type: TrainPlanType;
	fromStationId: string;
	toStationId: string;
	departS: number;
};

/** Scenariusz rozkładu pociągów — uruchomienie zastępuje całą flotę na sieci. */
export type Scenario = {
	id: string;
	name: string;
	description: string;
	trains: TrainPlan[];
};

export type ScenariosResponse = {
	scenarios: Scenario[];
};

export type ActiveScenarioInfo = {
	id: string;
	name: string;
	startedAt: number;
	totalTrains: number;
	spawnedTrains: number;
};
