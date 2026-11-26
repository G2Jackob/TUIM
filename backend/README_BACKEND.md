# Backend – Shopping List (Django + DRF + Channels + Keycloak)

## Jak wdrożyć w repo (4 kroki)
1. Skopiuj do `backend/`: foldery `accounts/`, `shopping/`, pliki `config/urls.py`, `config/asgi.py` (nadpisz),
   `conftest.py`, `pytest.ini`, `ruff.toml`.
2. Na **końcu** `backend/config/settings.py` wklej zawartość `config/settings_patch.py`
   (apps, PostgreSQL z env, Redis/Channels, DRF, Keycloak). Plik `settings_patch.py` potem usuń.
3. Dopisz zależności z `requirements-additions.txt` do `requirements.txt`.
4. W korzeniu repo podmień `docker-compose.yml`, dodaj `keycloak/`, `.env.example` → `.env`, `.github/workflows/ci.yml`.

Start: `docker compose up --build` →  API `http://localhost:8000/api/docs/` (Swagger), Keycloak `http://localhost:8080` (admin/admin).
Użytkownicy testowi w realmie `shopping`: **alice / alice123**, **bob / bob123**.

Token do testów w Swaggerze/curl (client publiczny ma włączony password grant tylko na dev):
```
curl -s -d "client_id=shopping-mobile&grant_type=password&username=alice&password=alice123" \
  http://localhost:8080/realms/shopping/protocol/openid-connect/token
```

## Endpointy REST (prefiks `/api/`, nagłówek `Authorization: Bearer <JWT>`)
| Metoda | Ścieżka | Opis | FR |
|---|---|---|---|
| GET | `health/` | healthcheck (publiczny) | – |
| GET | `auth/config/` | adresy Keycloaka dla appki (publiczny) | 01 |
| GET | `auth/me/` | zalogowany użytkownik | 01 |
| GET/POST | `lists/` | moje + udostępnione listy (`?archived=`), utworzenie | 02 |
| GET/PATCH/PUT/DELETE | `lists/{id}/` | szczegóły; zmiana/usunięcie tylko właściciel | 02 |
| POST | `lists/{id}/archive/`, `unarchive/` | archiwizacja (właściciel) | 02 |
| GET/POST | `lists/{id}/members/` | członkowie; dodanie po e-mailu/username (właściciel) | 03 |
| DELETE | `lists/{id}/members/{user_id}/` | odebranie dostępu (właściciel) / opuszczenie listy | 03 |
| POST | `lists/{id}/invites/` | kod zaproszenia (właściciel) | 03 |
| POST | `invites/accept/` | dołączenie kodem | 03 |
| GET/POST | `lists/{id}/items/` | produkty listy, dodanie | 04 |
| GET/PATCH/PUT/DELETE | `lists/{id}/items/{item_id}/` | podgląd/edycja/usunięcie | 04 |
| POST | `…/items/{id}/reserve/` · `release/` | „Ja to kupuję” / zwolnienie (409 gdy zajęte przez kogoś) | 05 |
| POST | `…/items/{id}/purchase/` · `unpurchase/` | odhaczenie / cofnięcie | 05 |
| GET | `lists/{id}/total/?currency=EUR` | suma szacunkowa + przeliczenie (NBP, cache, fallback) | 08 |
| GET | `exchange-rates/?...` | kursy walut z zewnętrznego API | 08 |

Błędy: 401 (brak/zły/wygasły token), 403 (brak uprawnień), 404 (cudza lista – nie ujawniamy istnienia),
400 (walidacja), 409 (konflikt rezerwacji), 503 (Keycloak/API zewnętrzne niedostępne).

## WebSockety (FR-06)
* `ws://host:8000/ws/lists/<uuid>/` – zdarzenia jednej listy; `ws://host:8000/ws/me/` – `list.shared` / `list.unshared`.
* Token: nagłówek `Authorization: Bearer …` (OkHttp) lub `?token=…` (fallback).
* Koperta: `{"event":"item.reserved","list_id":"…","data":{…},"actor_id":5,"timestamp":"…"}`.
  Zdarzenia: `list.updated/archived/deleted`, `item.created/updated/deleted/reserved/released/purchased/unpurchased`,
  `member.added/removed`.
* Zmiany wysyłasz przez REST; WS służy do odbioru. `{"action":"ping"}` → `{"event":"pong"}`.
* Kody zamknięcia: **4401** zły token, **4403** brak dostępu / usunięto Cię z listy, **4404** lista usunięta.
* Po zerwaniu połączenia: reconnect + `GET lists/{id}/` i `…/items/` (pełny stan), żeby nic nie zgubić.

## Dla zespołu mobilnego
Rejestracja/logowanie: Authorization Code + PKCE w Keycloaku (np. biblioteka AppAuth), parametry z `auth/config/`.
Redirect URI: `com.example.shoppinglist:/oauth2redirect` (zmień w `keycloak/shopping-realm.json` na prawdziwy package).
Emulator Androida widzi komputer jako `10.0.2.2` → ustaw `KEYCLOAK_PUBLIC_URL=http://10.0.2.2:8080`.

## Testy i jakość
`cd backend && pytest --cov=accounts --cov=shopping` → 205 testów, pokrycie ~99 % (jednostkowe: serwisy rezerwacji,
walidacja, JWT; integracyjne: API + WebSocket + baza + zewnętrzne API z mockiem). Lint: `ruff check .`, security: `bandit -r accounts shopping -ll`.
CI (`.github/workflows/ci.yml`): build → migracje na PostgreSQL → testy → ruff + bandit → deploy SSH (tylko `main`).
Sekrety do deployu: `DEPLOY_HOST`, `DEPLOY_USER`, `DEPLOY_SSH_KEY`.
