from os import getenv

DEFAULT_ORIGINS = "http://localhost:5173,http://127.0.0.1:5173"

ALLOWED_ORIGINS = [
	origin.strip()
	for origin in getenv("FRONTEND_ORIGINS", DEFAULT_ORIGINS).split(",")
	if origin.strip()
]
