# TUIM

## Uruchomienie lokalne

```powershell
docker compose up --build
docker compose exec backend python manage.py createsuperuser
```

Migracje bazy są wykonywane przy starcie kontenera backendu.
Po zmianach w kodzie backendu przebuduj obraz poleceniem `docker compose up --build`.

## Testy i CI/CD

- Backend: Pytest + pytest-django (`cd backend; python -m pytest -q`).
- Android: lokalne testy JUnit (`cd mobileApp; .\gradlew.bat testDebugUnitTest`).
- GitHub Actions uruchamia oba zestawy testów na push i pull request.
- Push na `main` po przejściu testów wdraża Compose na skonfigurowanym self-hosted runnerze z Dockerem.