package com.g2jackob.tuim.data.network

import com.google.gson.annotations.SerializedName

data class AuthConfigDto(
    val issuer: String,
    @SerializedName("client_id") val clientId: String,
    @SerializedName("authorization_endpoint") val authorizationEndpoint: String,
    @SerializedName("token_endpoint") val tokenEndpoint: String,
    @SerializedName("registration_endpoint") val registrationEndpoint: String? = null,
    @SerializedName("end_session_endpoint") val endSessionEndpoint: String? = null
)

data class UserBriefDto(
    val id: String? = null,
    val username: String? = null,
    @SerializedName("display_name") val displayName: String? = null
) {
    fun label(): String = displayName?.takeIf(String::isNotBlank)
        ?: username?.takeIf(String::isNotBlank)
        ?: id.orEmpty()
}

data class CurrentUserDto(
    val id: String,
    val username: String,
    val email: String? = null,
    @SerializedName("display_name") val displayName: String? = null
)

data class ShoppingListDto(
    val id: String,
    val name: String,
    val description: String? = null,
    val currency: String? = null,
    @SerializedName("is_archived") val isArchived: Boolean = false,
    val role: String? = null,
    @SerializedName("items_count") val itemsCount: Int = 0,
    @SerializedName("purchased_count") val purchasedCount: Int = 0
)

data class ShoppingItemDto(
    val id: String,
    val name: String,
    val quantity: Double = 1.0,
    val unit: String = "szt.",
    val category: String? = null,
    val note: String? = null,
    @SerializedName("is_purchased") val purchased: Boolean = false,
    @SerializedName("reserved_by") val reservedBy: UserBriefDto? = null,
    @SerializedName("estimated_price") val estimatedPrice: Double? = null,
    @SerializedName("purchased_by") val purchasedBy: UserBriefDto? = null
)

data class ListMemberDto(
    val user: UserBriefDto,
    val role: String,
    @SerializedName("joined_at") val joinedAt: String
)

data class InviteDto(
    val code: String,
    @SerializedName("list_id") val listId: String,
    @SerializedName("expires_at") val expiresAt: String
)

data class ExchangeRateDto(
    @SerializedName("from") val fromCurrency: String,
    @SerializedName("to") val toCurrency: String,
    val rate: String,
    @SerializedName("rate_date") val rateDate: String? = null,
    val stale: Boolean = false
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

data class AddMemberRequest(val identifier: String)

data class AcceptInviteRequest(val code: String)

data class ListTotalDto(
    val currency: String,
    val total: String,
    @SerializedName("items_priced") val itemsPriced: Int,
    @SerializedName("items_without_price") val itemsWithoutPrice: Int,
    val converted: ConvertedTotalDto? = null
)

data class ConvertedTotalDto(
    val currency: String,
    val total: String,
    val rate: String,
    @SerializedName("rate_date") val rateDate: String? = null,
    val stale: Boolean = false
)
