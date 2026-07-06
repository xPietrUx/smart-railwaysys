from fastapi import HTTPException, Request
from neo4j import Driver


def get_driver(request: Request) -> Driver:
	driver = getattr(request.app.state, "driver", None)
	if driver is None:
		raise HTTPException(status_code=503, detail="Memgraph driver not ready")
	return driver
