import base64
import hashlib
import hmac
import json
import os
import re
import secrets
import time
import uuid

from neo4j import Session

from app.core.config import (
	AUTH_SECRET,
	AUTH_TOKEN_TTL_SECONDS,
	DEFAULT_ADMIN_EMAIL,
	DEFAULT_ADMIN_PASSWORD,
)

# --- Katalog uprawnień i domyślne role -------------------------------------

# Pełny katalog uprawnień. Klucz zapisujemy w roli, wartość to etykieta
# pokazywana w panelu administratora.
PERMISSIONS: dict[str, str] = {
	"simulation.view": "Podgląd symulacji",
	"simulation.control": "Sterowanie symulacją (pauza, prędkość, pociągi)",
	"timetable.manage": "Zarządzanie rozkładami jazdy",
	"users.manage": "Zarządzanie użytkownikami",
	"roles.manage": "Zarządzanie rolami i uprawnieniami",
}

# Uprawnienia, bez których administrator zablokowałby sobie panel — nie da się
# ich odebrać roli "admin".
ADMIN_LOCKED_PERMISSIONS = ("users.manage", "roles.manage")

DEFAULT_ROLE_NAME = "user"
GUEST_ROLE_NAME = "guest"
ADMIN_ROLE_NAME = "admin"

# Role zakładane automatycznie przy starcie (is_system = nie można ich usunąć).
DEFAULT_ROLES: dict[str, dict] = {
	ADMIN_ROLE_NAME: {"label": "Administrator", "permissions": list(PERMISSIONS.keys())},
	DEFAULT_ROLE_NAME: {
		"label": "Użytkownik",
		"permissions": ["simulation.view", "simulation.control", "timetable.manage"],
	},
	GUEST_ROLE_NAME: {"label": "Gość", "permissions": ["simulation.view"]},
}

_ROLE_NAME_RE = re.compile(r"^[a-z][a-z0-9_]{1,30}$")


def normalize_email(email: str) -> str:
	return email.strip().lower()


# --- Hasła ------------------------------------------------------------------


def _hash_password(password: str, salt: bytes | None = None) -> str:
	salt = salt or os.urandom(16)
	digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 310_000)
	return f"pbkdf2_sha256$310000${base64.urlsafe_b64encode(salt).decode()}${base64.urlsafe_b64encode(digest).decode()}"


def _verify_password(password: str, encoded: str) -> bool:
	try:
		_, rounds, salt, expected = encoded.split("$", 3)
		digest = hashlib.pbkdf2_hmac(
			"sha256", password.encode(), base64.urlsafe_b64decode(salt), int(rounds)
		)
		return hmac.compare_digest(base64.urlsafe_b64encode(digest).decode(), expected)
	except (ValueError, TypeError):
		return False


# --- Reprezentacje publiczne ------------------------------------------------


def public_user(user: dict) -> dict:
	"""Bez hasła i pól wewnętrznych — bezpieczne do zwrócenia klientowi."""
	return {
		"id": user["id"],
		"email": user["email"],
		"role": user.get("role") or DEFAULT_ROLE_NAME,
		"active": bool(user.get("active", True)),
		"created_at": user.get("created_at"),
	}


def _public_role(role: dict) -> dict:
	return {
		"name": role["name"],
		"label": role.get("label") or role["name"],
		"permissions": list(role.get("permissions") or []),
		"is_system": bool(role.get("is_system", False)),
	}


# --- Użytkownicy ------------------------------------------------------------


def create_user(session: Session, email: str, password: str, role: str = DEFAULT_ROLE_NAME) -> dict | None:
	email = normalize_email(email)
	if "@" not in email:
		raise ValueError("Podaj poprawny adres e-mail.")
	if session.run("MATCH (u:User {email: $email}) RETURN u", email=email).single():
		return None
	user_id = f"USR_{uuid.uuid4().hex[:12]}"
	row = session.run(
		"CREATE (u:User {id: $id, email: $email, password_hash: $password_hash, role: $role, active: true, created_at: $created_at}) RETURN u",
		id=user_id,
		email=email,
		password_hash=_hash_password(password),
		role=role,
		created_at=time.time(),
	).single()
	return dict(row["u"])


def authenticate(session: Session, email: str, password: str) -> dict | None:
	row = session.run(
		"MATCH (u:User {email: $email}) RETURN u", email=normalize_email(email)
	).single()
	if not row:
		return None
	user = dict(row["u"])
	if not bool(user.get("active", True)):
		return None
	return user if _verify_password(password, user.get("password_hash", "")) else None


def get_user_by_id(session: Session, user_id: str) -> dict | None:
	row = session.run("MATCH (u:User {id: $id}) RETURN u", id=user_id).single()
	return dict(row["u"]) if row else None


def list_users(session: Session) -> list[dict]:
	rows = session.run("MATCH (u:User) RETURN u ORDER BY u.created_at")
	return [public_user(dict(row["u"])) for row in rows]


def _count_active_admins(session: Session) -> int:
	return session.run(
		"MATCH (u:User) WHERE u.role = $admin AND coalesce(u.active, true) = true RETURN count(u) AS c",
		admin=ADMIN_ROLE_NAME,
	).single()["c"]


def _is_last_admin(session: Session, user: dict) -> bool:
	is_active_admin = user.get("role") == ADMIN_ROLE_NAME and bool(user.get("active", True))
	return is_active_admin and _count_active_admins(session) <= 1


def update_user(
	session: Session,
	user_id: str,
	*,
	email: str | None = None,
	role: str | None = None,
	active: bool | None = None,
) -> dict | None:
	user = get_user_by_id(session, user_id)
	if not user:
		return None

	props: dict = {}
	if email is not None:
		email = normalize_email(email)
		if "@" not in email:
			raise ValueError("Podaj poprawny adres e-mail.")
		clash = session.run(
			"MATCH (u:User {email: $email}) WHERE u.id <> $id RETURN u", email=email, id=user_id
		).single()
		if clash:
			raise ValueError("Inny użytkownik ma już ten adres e-mail.")
		props["email"] = email
	if role is not None:
		if not role_exists(session, role):
			raise ValueError("Wybrana rola nie istnieje.")
		props["role"] = role
	if active is not None:
		props["active"] = bool(active)

	# Zabezpieczenie przed samoblokadą: nie degradujemy ani nie wyłączamy ostatniego admina.
	degrading = role is not None and role != ADMIN_ROLE_NAME
	deactivating = active is False
	if (degrading or deactivating) and _is_last_admin(session, user):
		raise ValueError("To ostatni aktywny administrator — nie można go zdegradować ani wyłączyć.")

	if not props:
		return public_user(user)
	row = session.run(
		"MATCH (u:User {id: $id}) SET u += $props RETURN u", id=user_id, props=props
	).single()
	return public_user(dict(row["u"]))


def set_user_password(session: Session, user_id: str, password: str) -> dict | None:
	if len(password) < 8:
		raise ValueError("Hasło musi mieć co najmniej 8 znaków.")
	row = session.run(
		"MATCH (u:User {id: $id}) SET u.password_hash = $password_hash RETURN u",
		id=user_id,
		password_hash=_hash_password(password),
	).single()
	return dict(row["u"]) if row else None


def delete_user(session: Session, user_id: str) -> bool:
	user = get_user_by_id(session, user_id)
	if not user:
		return False
	if _is_last_admin(session, user):
		raise ValueError("Nie można usunąć ostatniego administratora.")
	session.run("MATCH (u:User {id: $id}) DETACH DELETE u", id=user_id)
	return True


# --- Role -------------------------------------------------------------------


def role_exists(session: Session, name: str) -> bool:
	return session.run("MATCH (r:Role {name: $name}) RETURN r", name=name).single() is not None


def list_roles(session: Session) -> list[dict]:
	rows = session.run("MATCH (r:Role) RETURN r ORDER BY r.is_system DESC, r.name")
	return [_public_role(dict(row["r"])) for row in rows]


def get_role(session: Session, name: str) -> dict | None:
	row = session.run("MATCH (r:Role {name: $name}) RETURN r", name=name).single()
	return _public_role(dict(row["r"])) if row else None


def _clean_permissions(permissions) -> list[str]:
	"""Tylko znane uprawnienia, bez duplikatów, w stabilnej kolejności."""
	result: list[str] = []
	for perm in permissions or []:
		if perm in PERMISSIONS and perm not in result:
			result.append(perm)
	return result


def create_role(session: Session, name: str, label: str, permissions) -> dict:
	name = (name or "").strip().lower()
	if not _ROLE_NAME_RE.match(name):
		raise ValueError("Nazwa roli: małe litery, cyfry i podkreślenia (2–31 znaków, zaczyna się literą).")
	if role_exists(session, name):
		raise ValueError("Rola o tej nazwie już istnieje.")
	row = session.run(
		"CREATE (r:Role {name: $name, label: $label, permissions: $permissions, is_system: false, created_at: $created_at}) RETURN r",
		name=name,
		label=(label or name).strip(),
		permissions=_clean_permissions(permissions),
		created_at=time.time(),
	).single()
	return _public_role(dict(row["r"]))


def update_role(
	session: Session, name: str, *, label: str | None = None, permissions=None
) -> dict | None:
	role = get_role(session, name)
	if not role:
		return None
	if role["is_system"]:
		raise ValueError("Roli systemowej nie można edytować.")
	props: dict = {}
	if label is not None:
		props["label"] = label.strip() or name
	if permissions is not None:
		props["permissions"] = _clean_permissions(permissions)
	if not props:
		return role
	row = session.run(
		"MATCH (r:Role {name: $name}) SET r += $props RETURN r", name=name, props=props
	).single()
	return _public_role(dict(row["r"]))


def delete_role(session: Session, name: str) -> bool:
	role = get_role(session, name)
	if not role:
		return False
	if role["is_system"]:
		raise ValueError("Roli systemowej nie można usunąć.")
	in_use = session.run(
		"MATCH (u:User {role: $name}) RETURN count(u) AS c", name=name
	).single()["c"]
	if in_use:
		raise ValueError(f"Rola jest przypisana do {in_use} użytkownik(ów) — najpierw zmień im rolę.")
	session.run("MATCH (r:Role {name: $name}) DELETE r", name=name)
	return True


def permissions_for_role(session: Session, role_name: str) -> list[str]:
	role = get_role(session, role_name)
	if role:
		return role["permissions"]
	default = DEFAULT_ROLES.get(role_name)
	return list(default["permissions"]) if default else []


# --- Zasiew startowy --------------------------------------------------------


def ensure_roles(session: Session) -> None:
	"""Zakłada role systemowe. Istniejącym nie nadpisuje uprawnień (admin mógł je
	edytować), pilnuje tylko, by rola admin zawsze miała uprawnienia zarządcze."""
	for name, spec in DEFAULT_ROLES.items():
		session.run(
			"""
			MERGE (r:Role {name: $name})
			ON CREATE SET r.label = $label, r.permissions = $permissions,
				r.is_system = true, r.created_at = $created_at
			ON MATCH SET r.is_system = true
			""",
			name=name,
			label=spec["label"],
			permissions=spec["permissions"],
			created_at=time.time(),
		)
	admin = get_role(session, ADMIN_ROLE_NAME)
	if admin:
		perms = list(admin["permissions"])
		missing = [p for p in ADMIN_LOCKED_PERMISSIONS if p not in perms]
		if missing:
			session.run(
				"MATCH (r:Role {name: $name}) SET r.permissions = $permissions",
				name=ADMIN_ROLE_NAME,
				permissions=perms + missing,
			)


def ensure_admin_user(session: Session) -> str | None:
	"""Gwarantuje istnienie konta administratora. Zwraca e-mail, jeśli utworzono
	lub podniesiono konto — inaczej None."""
	if _count_active_admins(session) > 0:
		return None
	email = normalize_email(DEFAULT_ADMIN_EMAIL)
	existing = session.run("MATCH (u:User {email: $email}) RETURN u", email=email).single()
	if existing:
		session.run(
			"MATCH (u:User {email: $email}) SET u.role = $admin, u.active = true",
			email=email,
			admin=ADMIN_ROLE_NAME,
		)
		return email
	session.run(
		"CREATE (u:User {id: $id, email: $email, password_hash: $password_hash, role: $admin, active: true, created_at: $created_at})",
		id=f"USR_{uuid.uuid4().hex[:12]}",
		email=email,
		password_hash=_hash_password(DEFAULT_ADMIN_PASSWORD),
		admin=ADMIN_ROLE_NAME,
		created_at=time.time(),
	)
	return email


# --- Tokeny -----------------------------------------------------------------


def _encode(data: bytes) -> str:
	return base64.urlsafe_b64encode(data).decode().rstrip("=")


def issue_token(user: dict) -> str:
	payload = _encode(
		json.dumps(
			{
				"sub": user["id"],
				"email": user["email"],
				"role": user.get("role") or DEFAULT_ROLE_NAME,
				"exp": int(time.time()) + AUTH_TOKEN_TTL_SECONDS,
			},
			separators=(",", ":"),
		).encode()
	)
	signature = _encode(hmac.new(AUTH_SECRET.encode(), payload.encode(), hashlib.sha256).digest())
	return f"{payload}.{signature}"


def verify_token(token: str) -> dict | None:
	try:
		payload, signature = token.split(".", 1)
		expected = _encode(hmac.new(AUTH_SECRET.encode(), payload.encode(), hashlib.sha256).digest())
		if not secrets.compare_digest(signature, expected):
			return None
		data = json.loads(base64.urlsafe_b64decode(payload + "=" * (-len(payload) % 4)))
		return data if int(data["exp"]) > int(time.time()) else None
	except (ValueError, KeyError, TypeError, json.JSONDecodeError):
		return None
