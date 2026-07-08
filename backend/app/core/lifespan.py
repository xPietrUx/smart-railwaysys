import time
from contextlib import asynccontextmanager

from fastapi import FastAPI
from neo4j import GraphDatabase
from neo4j.exceptions import ServiceUnavailable

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
		count = session.run("MATCH (s:Station) RETURN count(s) AS c").single()["c"]
		if count == 0:
			print("Graf pusty — uruchamiam seed...")
			load_data(session)
		else:
			print(f"Graf już zasilony ({count} stacji) — pomijam seed.")
	app.state.driver = driver
	yield
	driver.close()
	print("✓ Połączenie z Memgraph zamknięte")
