package com.g2jackob.tuim.data.local

import android.content.Context
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow

class TokenStore(context: Context) {
    private val preferences = context.getSharedPreferences("tuim_auth", Context.MODE_PRIVATE)
    private val _accessToken = MutableStateFlow(preferences.getString(KEY_ACCESS, null))
    val accessToken: StateFlow<String?> = _accessToken.asStateFlow()

    fun accessTokenSnapshot(): String? = preferences.getString(KEY_ACCESS, null)
    fun refreshTokenSnapshot(): String? = preferences.getString(KEY_REFRESH, null)
    fun tokenEndpointSnapshot(): String? = preferences.getString(KEY_TOKEN_ENDPOINT, null)
    fun clientIdSnapshot(): String? = preferences.getString(KEY_CLIENT_ID, null)

    fun saveConfiguration(tokenEndpoint: String, clientId: String) {
        preferences.edit()
            .putString(KEY_TOKEN_ENDPOINT, tokenEndpoint)
            .putString(KEY_CLIENT_ID, clientId)
            .apply()
    }

    fun save(accessToken: String, refreshToken: String?) {
        preferences.edit()
            .putString(KEY_ACCESS, accessToken)
            .putString(KEY_REFRESH, refreshToken)
            .apply()
        _accessToken.value = accessToken
    }

    fun clear() {
        preferences.edit().clear().apply()
        _accessToken.value = null
    }

    private companion object {
        const val KEY_ACCESS = "access_token"
        const val KEY_REFRESH = "refresh_token"
        const val KEY_TOKEN_ENDPOINT = "token_endpoint"
        const val KEY_CLIENT_ID = "client_id"
    }
}
