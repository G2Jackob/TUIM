# Backend – Shopping List (Django + DRF + Channels + Keycloak)

## Uruchomienie

W katalogu głównym repozytorium uzupełnij lokalny `.env` i uruchom `docker compose up --build`. API będzie dostępne
pod `http://localhost:8000/api/docs/` (Swagger), a Keycloak pod `http://localhost:8080`.
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

## Testy i GitHub Actions

Backend korzysta z Pytest + pytest-django; testy API i WebSocket używają bazy testowej SQLite oraz mocków, więc nie
wymagają uruchomionego PostgreSQL, Redis ani Keycloaka:

```powershell
cd backend
python -m pytest -q
```

Android używa lokalnych testów JUnit uruchamianych przez Gradle:

```powershell
cd mobileApp
.\gradlew.bat testDebugUnitTest
```

Workflow `.github/workflows/ci.yml` uruchamia oba zestawy testów na push i pull request. Deploy na lokalny komputer
uruchamia się wyłącznie po pushu na `main` i po przejściu testów.

## Deploy na własny komputer z Dockerem

Ponieważ komputer lokalny zwykle nie jest osiągalny z GitHub-hosted runnera, deploy korzysta z self-hosted runnera:

1. W repozytorium GitHub otwórz **Settings → Actions → Runners → New self-hosted runner** i zainstaluj runner
   na komputerze z Docker Desktop. Workflow oczekuje domyślnych etykiet `self-hosted` i `windows`.
2. Docker Desktop musi działać, a konto uruchamiające runnera musi mieć dostęp do polecenia `docker`.
3. W **Settings → Secrets and variables → Actions** dodaj sekret `TUIM_ENV_FILE` z pełną zawartością produkcyjnego
   pliku `.env` (nie dodawaj tego pliku do repozytorium). Ustaw `ALLOWED_HOSTS` oraz `KEYCLOAK_PUBLIC_URL` na adresy
   osiągalne z urządzeń klienckich, zamiast pozostawiać `localhost`.
4. Po mergu na `main`, gdy testy przejdą, runner wykona `docker compose up --build --detach`. Kontenery i wolumen
   `postgres_data` pozostają na komputerze, więc dane bazy przetrwają kolejne wdrożenia.

Self-hosted runner wykonuje kod z repozytorium z uprawnieniami konta Windows, więc nie uruchamiaj go dla
niezaufanych workflow ani nie dopuszczaj niezweryfikowanych zmian na `main`. Dla serwera dostępnego publicznie
bezpieczniejszym i stabilniejszym wariantem jest odrębny serwer Linux i deploy przez SSH.
