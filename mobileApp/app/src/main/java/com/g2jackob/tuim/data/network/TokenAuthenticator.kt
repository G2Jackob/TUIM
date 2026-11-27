package com.g2jackob.tuim.data.network

import com.g2jackob.tuim.data.local.TokenStore
import com.google.gson.Gson
import com.google.gson.annotations.SerializedName
import okhttp3.Authenticator
import okhttp3.FormBody
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.Response
import okhttp3.Route

class TokenAuthenticator(private val tokenStore: TokenStore) : Authenticator {
    private val refreshClient = OkHttpClient()
    private val gson = Gson()

    override fun authenticate(route: Route?, response: Response): Request? {
        if (response.responseCount() >= 2) return null

        val currentAccessToken = tokenStore.accessTokenSnapshot() ?: return null
        val previousAuthorization = response.request.header("Authorization")
        if (previousAuthorization != "Bearer $currentAccessToken") {
            return response.request.newBuilder()
                .header("Authorization", "Bearer $currentAccessToken")
                .build()
        }

        val refreshToken = tokenStore.refreshTokenSnapshot() ?: return null
        val tokenEndpoint = tokenStore.tokenEndpointSnapshot() ?: return null
        val clientId = tokenStore.clientIdSnapshot() ?: return null
        val refreshRequest = Request.Builder()
            .url(tokenEndpoint)
            .post(
                FormBody.Builder()
                    .add("grant_type", "refresh_token")
                    .add("client_id", clientId)
                    .add("refresh_token", refreshToken)
                    .build()
            )
            .build()

        return runCatching {
            refreshClient.newCall(refreshRequest).execute().use { refreshResponse ->
                if (!refreshResponse.isSuccessful) return null
                val body = refreshResponse.body?.string() ?: return null
                val tokens = gson.fromJson(body, RefreshedTokens::class.java)
                val accessToken = tokens.accessToken?.takeIf(String::isNotBlank) ?: return null
                tokenStore.save(accessToken, tokens.refreshToken ?: refreshToken)
                response.request.newBuilder()
                    .header("Authorization", "Bearer $accessToken")
                    .build()
            }
        }.getOrNull()
    }

    private fun Response.responseCount(): Int {
        var result = 1
        var prior = priorResponse
        while (prior != null) {
            result++
            prior = prior.priorResponse
        }
        return result
    }

    private data class RefreshedTokens(
        @SerializedName("access_token") val accessToken: String?,
        @SerializedName("refresh_token") val refreshToken: String?
    )
}
