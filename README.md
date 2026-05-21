# Obługa projetku

Po `git clone (link projektu)` upewniamy się że doocker działa na naszym sprzęcie a następnie wykonujemy:

1. JEŚLI PIERWSZY RAZ URCHAMIAMY PROJEKT

Tworzymy plik .env z pliku .env.example

```bash
docker compose build --no-cache
docker compose up
CTRL + C
```

2. Jeśli rutynowy start pracy w projekcie

```bash
docker compose up --watch
CTRL + C by zatrzymać
```

Tyle powinno wystaczyć by pracować z projektem, `CTRL+S` by zaktualizować zmiany

3. Czyszczenie całkowite kontenerów (wraz z danym w bazie)

```bash
docker compose down -v
docker builder prune -a -f
```
