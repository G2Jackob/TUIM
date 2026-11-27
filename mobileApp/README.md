# TUIM Android app

Android client built with Kotlin, Jetpack Compose, Room, Retrofit, OkHttp, and AppAuth.

## Run on the Android emulator

Start the backend and Keycloak with Docker Compose from the repository root, then install the app:

```powershell
.\gradlew.bat installDebug
```

The default API URL points to `http://10.0.2.2:8000/`, which routes from the Android emulator to the host machine. Override it for another device or environment with Gradle properties:

```powershell
.\gradlew.bat installDebug -PTUIM_API_BASE_URL=http://10.0.2.2:8000/ -PTUIM_WS_BASE_URL=ws://10.0.2.2:8000/
```

The app gets Keycloak authorization and token endpoints from `GET /api/auth/config/` and uses Authorization Code + PKCE. The Keycloak client redirect URI and the app's `REDIRECT_URI` / `appAuthRedirectScheme` must match; the current configured URI is `com.example.shoppinglist:/oauth2redirect`.

For emulator login, Keycloak's public URL must be reachable at `http://10.0.2.2:8080`. Use the development test accounts provisioned by the backend/Keycloak configuration, or select **Tryb demo** on the login screen to run against local Room data without a server.

## App functionality

- Lists can be created, edited, archived/restored, and deleted by their owner.
- Owners can add members by username or email, remove members, and create invitation codes. Members can leave a shared list or join one using an invitation code.
- Products support create/edit/delete, supported units, category, note, optional unit price, reservation, and purchased status.
- List totals can be converted to another currency; the app can also request and display a current/cached exchange rate.
- List and product updates are synchronized through REST and list WebSockets. The lists screen listens for shared/unshared events and refreshes the local Room cache.

## Build and tests

```powershell
.\gradlew.bat testDebugUnitTest
.\gradlew.bat assembleDebug
```
