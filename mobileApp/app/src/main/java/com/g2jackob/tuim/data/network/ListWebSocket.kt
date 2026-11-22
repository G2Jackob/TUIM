package com.g2jackob.tuim.data.network

import com.g2jackob.tuim.BuildConfig
import com.g2jackob.tuim.data.local.TokenStore
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.Response
import okhttp3.WebSocket
import okhttp3.WebSocketListener

class ListWebSocket(
    private val tokenStore: TokenStore,
    private val onChanged: () -> Unit
) : WebSocketListener() {
    private val client = OkHttpClient()
    private var socket: WebSocket? = null

    fun connect(listId: String) {
        disconnect()
        val token = tokenStore.accessTokenSnapshot().orEmpty()
        val base = BuildConfig.WS_BASE_URL.trimEnd('/')
        val request = Request.Builder()
            .url("$base/ws/shopping-lists/$listId/?token=$token")
            .build()
        socket = client.newWebSocket(request, this)
    }

    fun disconnect() {
        socket?.close(1000, "Disconnected")
        socket = null
    }

    override fun onMessage(webSocket: WebSocket, text: String) {
        onChanged()
    }

    override fun onFailure(webSocket: WebSocket, t: Throwable, response: Response?) {
        onChanged()
    }
}
