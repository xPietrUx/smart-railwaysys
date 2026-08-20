from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes.admin import router as admin_router
from app.api.routes.events import router as events_router
from app.api.routes.auth import router as auth_router
from app.api.routes.health import router as health_router
from app.api.routes.live import router as live_router
from app.api.routes.network import router as network_router
from app.api.routes.routing import router as routing_router
from app.api.routes.scenarios import router as scenarios_router
from app.api.routes.simulation import router as simulation_router
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

from fastapi.responses import RedirectResponse

app.include_router(health_router)
app.include_router(auth_router)
app.include_router(admin_router)
app.include_router(network_router)
app.include_router(trains_router)
app.include_router(events_router)
app.include_router(routing_router)
app.include_router(scenarios_router)
app.include_router(simulation_router)
app.include_router(live_router)


@app.get("/admin", include_in_schema=False)
def redirect_admin_to_frontend():
	frontend_url = ALLOWED_ORIGINS[0] if ALLOWED_ORIGINS else "http://localhost:5173"
	return RedirectResponse(url=f"{frontend_url}/admin", status_code=307)


@app.get("/", include_in_schema=False)
def redirect_root_to_frontend():
	frontend_url = ALLOWED_ORIGINS[0] if ALLOWED_ORIGINS else "http://localhost:5173"
	return RedirectResponse(url=frontend_url, status_code=307)

