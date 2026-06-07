import time
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from neo4j import GraphDatabase
from neo4j.exceptions import ServiceUnavailable

from db.seed import URI, AUTH, load_data


def connect_with_retry(retries: int = 10, delay: int = 2):
    """Czeka, aż Memgraph będzie gotowy (depends_on nie gwarantuje gotowości)."""
    for attempt in range(1, retries + 1):
        try:
            driver = GraphDatabase.driver(URI, auth=AUTH)
            driver.verify_connectivity()
            print("✓ Połączono z Memgraph")
            return driver
        except ServiceUnavailable:
            print(f"Memgraph niedostępny (próba {attempt}/{retries})...")
            time.sleep(delay)
    raise RuntimeError("Nie udało się połączyć z Memgraph po wielu próbach")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # --- startup ---
    driver = connect_with_retry()
    with driver.session() as session:
        count = session.run("MATCH (s:Station) RETURN count(s) AS c").single()["c"]
        if count == 0:
            print("Graf pusty — uruchamiam seed...")
            load_data(session)
        else:
            print(f"Graf już zasilony ({count} stacji) — pomijam seed.")
    # udostępniamy driver endpointom przez app.state.driver
    app.state.driver = driver
    yield
    # --- shutdown ---
    driver.close()
    print("✓ Połączenie z Memgraph zamknięte")


app = FastAPI(lifespan=lifespan)

origins = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/hello")
def get_welcome_message():
    return {"message": "Połączenie z backendem udane"}
