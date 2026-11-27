package com.g2jackob.tuim.data.network

import android.os.Handler
import android.os.Looper
import com.g2jackob.tuim.BuildConfig
import com.g2jackob.tuim.data.local.TokenStore
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.Response
import okhttp3.WebSocket
import okhttp3.WebSocketListener
import java.util.concurrent.TimeUnit

class UserWebSocket(
    private val tokenStore: TokenStore,
    private val onChanged: () -> Unit
) : WebSocketListener() {
    private val client = OkHttpClient.Builder()
        .pingInterval(30, TimeUnit.SECONDS)
        .build()
    private val handler = Handler(Looper.getMainLooper())
    private var socket: WebSocket? = null
    private var closedByUser = false
    private var retryCount = 0

    private val reconnect = Runnable { openSocket() }

    fun connect() {
        disconnect()
        closedByUser = false
        retryCount = 0
        openSocket()
    }

    fun disconnect() {
        closedByUser = true
        handler.removeCallbacks(reconnect)
        socket?.close(1000, "Disconnected")
        socket = null
    }

    private fun openSocket() {
        val token = tokenStore.accessTokenSnapshot()
        if (token.isNullOrBlank()) return

        val base = BuildConfig.WS_BASE_URL.trimEnd('/')
        val request = Request.Builder()
            .url("$base/ws/me/")
            .header("Authorization", "Bearer $token")
            .build()
        socket = client.newWebSocket(request, this)
    }

    override fun onOpen(webSocket: WebSocket, response: Response) {
        retryCount = 0
    }

    override fun onMessage(webSocket: WebSocket, text: String) {
        onChanged()
    }

    override fun onFailure(webSocket: WebSocket, t: Throwable, response: Response?) {
        onChanged()
        scheduleReconnect()
    }

    override fun onClosed(webSocket: WebSocket, code: Int, reason: String) {
        onChanged()
        scheduleReconnect()
    }

    private fun scheduleReconnect() {
        if (closedByUser) return
        handler.removeCallbacks(reconnect)
        val delaySeconds = (1L shl retryCount.coerceAtMost(5)).coerceAtMost(30L)
        retryCount++
        handler.postDelayed(reconnect, delaySeconds * 1_000)
    }
}
