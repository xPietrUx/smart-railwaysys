from pydantic import BaseModel


class SimulationSpeedRequest(BaseModel):
	speed: float
