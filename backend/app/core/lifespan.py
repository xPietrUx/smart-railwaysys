import asyncio
import random
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI
from neo4j import GraphDatabase
from neo4j.exceptions import ServiceUnavailable

from app.core import config
from app.core.ws_manager import ConnectionManager
from app.services import scenario_service, simulation_engine
from db.seed import AUTH, URI, load_data


def connect_with_retry(delay: int = 2):
	"""Czeka, aż Memgraph będzie gotowy (depends_on nie gwarantuje gotowości)."""
	attempt = 1
	while True:
		try:
			driver = GraphDatabase.driver(URI, auth=AUTH)
			driver.verify_connectivity()
			print("✓ Połączono z Memgraph")
			return driver
		except ServiceUnavailable:
			print(f"Memgraph niedostępny (próba {attempt})...")
			time.sleep(delay)
			attempt += 1


@asynccontextmanager
async def lifespan(app: FastAPI):
	driver = connect_with_retry()
	with driver.session() as session:
		try:
			session.run("CREATE CONSTRAINT ON (u:User) ASSERT u.email IS UNIQUE")  # ograniczenie unikalności e-maili
		except Exception:
			pass
		count = session.run("MATCH (s:Station) RETURN count(s) AS c").single()["c"]
		if count == 0:
			print("Graf pusty — uruchamiam seed...")
			load_data(session)
		else:
			print(f"Graf już zasilony ({count} stacji) — pomijam seed.")
		created = scenario_service.ensure_starter_scenarios(session, time.time())
		if created:
			print(f"✓ Utworzono {created} startowych scenariuszy rozkładu")
	app.state.driver = driver

	app.state.ws_manager = ConnectionManager()
	app.state.sim_lock = asyncio.Lock()
	app.state.scenario = None
	app.state.sim_paused = False
	app.state.pause_started_at = None
	app.state.sim_speed = 1.0
	app.state.sim_clock_minutes = 0.0
	app.state.sim_last_tick_at = None
	app.state.next_event_at = time.time() + random.expovariate(
		1.0 / config.SIM_EVENT_MEAN_INTERVAL_REAL_S
	)
	simulation_engine.start_simulation(app)
	print("✓ Autonomiczna symulacja pociągów uruchomiona")

	yield

	await simulation_engine.stop_simulation(app)
	driver.close()
	print("✓ Połączenie z Memgraph zamknięte")
