from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes.events import router as events_router
from app.api.routes.health import router as health_router
from app.api.routes.live import router as live_router
from app.api.routes.network import router as network_router
from app.api.routes.routing import router as routing_router
from app.api.routes.trains import router as trains_router
from app.core.config import ALLOWED_ORIGINS
from app.core.lifespan import lifespan


app = FastAPI(
	title="Smart Railway System API",
	lifespan=lifespan,
)

app.add_middleware(
	CORSMiddleware,
	allow_origins=ALLOWED_ORIGINS,
	allow_credentials=True,
	allow_methods=["*"],
	allow_headers=["*"],
)

app.include_router(health_router)
app.include_router(network_router)
app.include_router(trains_router)
app.include_router(events_router)
app.include_router(routing_router)
app.include_router(live_router)
