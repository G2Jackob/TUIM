package com.g2jackob.tuim.data.network

import android.net.Uri
import com.g2jackob.tuim.BuildConfig
import net.openid.appauth.connectivity.ConnectionBuilder
import java.net.HttpURLConnection
import java.net.URL

class DevelopmentConnectionBuilder : ConnectionBuilder {
    override fun openConnection(uri: Uri): HttpURLConnection {
        val isEmulatorKeycloakHttp =
            BuildConfig.DEBUG &&
                uri.scheme == "http" &&
                uri.host == EMULATOR_HOST &&
                uri.port == KEYCLOAK_PORT
        require(uri.scheme == "https" || isEmulatorKeycloakHttp) {
            "AppAuth requires HTTPS except for the local emulator Keycloak endpoint"
        }
        return URL(uri.toString()).openConnection() as HttpURLConnection
    }

    private companion object {
        const val EMULATOR_HOST = "10.0.2.2"
        const val KEYCLOAK_PORT = 8080
    }
}
