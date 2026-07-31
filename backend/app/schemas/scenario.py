from pydantic import BaseModel, Field


class TrainPlan(BaseModel):
	"""Jeden pociąg rozkładu: relacja from->to obsługiwana cyklicznie (tam,
	przerwa, powrót — jak flota bazowa), wjeżdżający na sieć departS sekund po
	uruchomieniu scenariusza."""

	name: str = Field(min_length=1, max_length=80)
	type: str = "REGIONAL"  # 'REGIONAL' | 'IC' | 'FREIGHT'
	fromStationId: str
	toStationId: str
	departS: float = Field(default=0.0, ge=0.0, le=600.0)


class Scenario(BaseModel):
	"""Scenariusz rozkładu pociągów. Uruchomienie zastępuje wszystkie pociągi na
	sieci pociągami z rozkładu."""

	id: str
	name: str
	description: str = ""
	trains: list[TrainPlan]


class ScenarioCreateRequest(BaseModel):
	name: str = Field(min_length=1, max_length=80)
	description: str = Field(default="", max_length=300)
	trains: list[TrainPlan] = Field(min_length=1, max_length=60)


class ScenariosResponse(BaseModel):
	scenarios: list[Scenario]


class ActiveScenarioInfo(BaseModel):
	"""Status uruchomionego rozkładu (idzie w każdej ramce WS)."""

	id: str
	name: str
	startedAt: float
	totalTrains: int
	spawnedTrains: int
