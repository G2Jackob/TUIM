package com.g2jackob.tuim.data.network

import com.google.gson.annotations.SerializedName

data class LoginRequest(
    val username: String,
    val password: String
)

data class RefreshRequest(
    val refresh: String
)

data class TokenResponse(
    @SerializedName("access") val accessToken: String?,
    @SerializedName("access_token") val accessTokenSnake: String?,
    @SerializedName("refresh") val refreshToken: String?,
    @SerializedName("refresh_token") val refreshTokenSnake: String?
) {
    fun access(): String = accessToken ?: accessTokenSnake.orEmpty()
    fun refresh(): String = refreshToken ?: refreshTokenSnake.orEmpty()
}

data class ShoppingListDto(
    val id: String,
    val name: String,
    val description: String? = null,
    val currency: String? = null,
    val items: List<ShoppingItemDto>? = null
)

data class ShoppingItemDto(
    val id: String,
    val name: String,
    val quantity: Double = 1.0,
    val unit: String = "szt.",
    val category: String? = null,
    val note: String? = null,
    val purchased: Boolean = false,
    @SerializedName("reserved_by") val reservedBy: String? = null,
    @SerializedName("estimated_price") val estimatedPrice: Double? = null
)

data class ShoppingListRequest(
    val name: String,
    val description: String = "",
    val currency: String = "PLN"
)

data class ShoppingItemRequest(
    val name: String,
    val quantity: Double,
    val unit: String,
    val category: String = "",
    val note: String = "",
    @SerializedName("estimated_price") val estimatedPrice: Double? = null
)

data class PurchasedRequest(val purchased: Boolean)

data class ProductSearchResponse(
    val products: List<ExternalProductDto>? = null
)

data class ExternalProductDto(
    val name: String,
    val category: String? = null
)
