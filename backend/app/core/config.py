from os import getenv

AUTH_SECRET = getenv("AUTH_SECRET", "change-this-secret-in-production")
AUTH_TOKEN_TTL_SECONDS = int(getenv("AUTH_TOKEN_TTL_SECONDS", "604800"))

# Konto administratora zakładane przy pierwszym starcie, jeśli w bazie nie ma
# żadnego aktywnego admina. Zmień hasło po pierwszym logowaniu (albo nadpisz
# przez zmienne środowiskowe ADMIN_EMAIL / ADMIN_PASSWORD).
DEFAULT_ADMIN_EMAIL = getenv("ADMIN_EMAIL", "admin@smartrailway.pl")
DEFAULT_ADMIN_PASSWORD = getenv("ADMIN_PASSWORD", "admin12345")

DEFAULT_ORIGINS = "http://localhost:5173,http://127.0.0.1:5173"

ALLOWED_ORIGINS = [
	origin.strip()
	for origin in getenv("FRONTEND_ORIGINS", DEFAULT_ORIGINS).split(",")
	if origin.strip()
]

# --- Silnik symulacji pociągów ---
# Realny czas vs. czas symulacji: timery przerwy (dwell) i zdarzeń losowych liczone
# są w realnych sekundach (obserwator zawsze widzi efekt w rozsądnym czasie),
# a jedynie postęp pociągu na odcinku jest skalowany przez SIM_TIME_SCALE.

SIM_TICK_INTERVAL_S = float(getenv("SIM_TICK_INTERVAL_S", "1.0"))
SIM_TIME_SCALE = float(getenv("SIM_TIME_SCALE", "60.0"))

# Dozwolone mnożniki tempa symulacji (sterowane z UI, styl EU4). Mnożnik skaluje
# postęp pociągów na odcinkach; timery liczone w realnych sekundach (przerwy,
# zdarzenia) pozostają nietknięte — patrz komentarz wyżej.
SIM_SPEED_OPTIONS = (0.5, 1.0, 1.5, 2.0)

SIM_DWELL_REAL_SECONDS_MIN = float(getenv("SIM_DWELL_REAL_SECONDS_MIN", "5.0"))
SIM_DWELL_REAL_SECONDS_MAX = float(getenv("SIM_DWELL_REAL_SECONDS_MAX", "15.0"))

SIM_EVENT_MEAN_INTERVAL_REAL_S = float(getenv("SIM_EVENT_MEAN_INTERVAL_REAL_S", "45.0"))
SIM_EVENT_DURATION_REAL_S_MIN = float(getenv("SIM_EVENT_DURATION_REAL_S_MIN", "20.0"))
SIM_EVENT_DURATION_REAL_S_MAX = float(getenv("SIM_EVENT_DURATION_REAL_S_MAX", "60.0"))

SIM_SPEED_RESTRICTION_FACTOR = float(getenv("SIM_SPEED_RESTRICTION_FACTOR", "0.5"))

SIM_DEBUG_ENDPOINTS_ENABLED = getenv("SIM_DEBUG_ENDPOINTS_ENABLED", "true").strip().lower() in (
	"1",
	"true",
	"yes",
)

# Wagi typów zdarzeń losowych (suma nie musi być 1.0 — losowanie ważone).
SIM_EVENT_TYPE_WEIGHTS = {
	"line_failure": 0.4,
	"derailment": 0.15,
	"speed_restriction": 0.3,
	"signal_failure": 0.15,
}
