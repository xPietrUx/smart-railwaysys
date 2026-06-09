### Dane w bazie (Memgraph Lab)

Otwórz [http://localhost:3000](http://localhost:3000) → kliknij **Connect** (dane połączenia są wypełnione automatycznie **za pomocą GUI**).

W zakładce **Query** wklej i uruchom:

```cypher
-- Podgląd całego grafu (stacje + tory)
MATCH (n)-[r]->(m) RETURN n, r, m LIMIT 50
```

```cypher
-- Lista stacji
MATCH (s:Station) RETURN s.id, s.name, s.type ORDER BY s.name
```

```cypher
-- Lista pociągów z aktualną pozycją
MATCH (t:Train) RETURN t.id, t.name, t.type, t.status, t.current_from, t.current_to, t.progress
```

Powinno zwrócić 10 stacji, 12 par torów (24 relacje), 4 pociągi.

---

## Ponowne wczytanie danych (reset bazy)

Seed jest **idempotentny** — czyści bazę przed załadowaniem, więc można go uruchamiać wielokrotnie:

```bash
docker compose exec backend python db/seed.py
```

---
