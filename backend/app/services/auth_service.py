import base64
import hashlib
import hmac
import json
import os
import secrets
import time
import uuid

from neo4j import Session

from app.core.config import AUTH_SECRET, AUTH_TOKEN_TTL_SECONDS


def normalize_email(email: str) -> str:
	return email.strip().lower()


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


def create_user(session: Session, email: str, password: str) -> dict | None:
	email = normalize_email(email)
	if "@" not in email:
		raise ValueError("Podaj poprawny adres e-mail.")
	if session.run("MATCH (u:User {email: $email}) RETURN u", email=email).single():
		return None
	user_id = f"USR_{uuid.uuid4().hex[:12]}"
	row = session.run(
		"CREATE (u:User {id: $id, email: $email, password_hash: $password_hash, created_at: $created_at}) RETURN u",
		id=user_id,
		email=email,
		password_hash=_hash_password(password),
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
	return user if _verify_password(password, user.get("password_hash", "")) else None


def _encode(data: bytes) -> str:
	return base64.urlsafe_b64encode(data).decode().rstrip("=")


def issue_token(user: dict) -> str:
	payload = _encode(json.dumps({"sub": user["id"], "email": user["email"], "exp": int(time.time()) + AUTH_TOKEN_TTL_SECONDS}, separators=(",", ":")).encode())
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
