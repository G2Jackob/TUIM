package com.g2jackob.tuim.data.network

import retrofit2.http.Body
import retrofit2.http.DELETE
import retrofit2.http.GET
import retrofit2.http.PATCH
import retrofit2.http.POST
import retrofit2.http.Path
import retrofit2.http.Query

interface ApiService {
    @GET("api/auth/config/")
    suspend fun getAuthConfig(): AuthConfigDto

    @GET("api/auth/me/")
    suspend fun getCurrentUser(): CurrentUserDto

    @GET("api/lists/")
    suspend fun getLists(): List<ShoppingListDto>

    @POST("api/lists/")
    suspend fun createList(@Body request: ShoppingListRequest): ShoppingListDto

    @GET("api/lists/{id}/")
    suspend fun getList(@Path("id") id: String): ShoppingListDto

    @PATCH("api/lists/{id}/")
    suspend fun updateList(
        @Path("id") id: String,
        @Body request: ShoppingListRequest
    ): ShoppingListDto

    @DELETE("api/lists/{id}/")
    suspend fun deleteList(@Path("id") id: String)

    @POST("api/lists/{id}/archive/")
    suspend fun archiveList(@Path("id") id: String): ShoppingListDto

    @POST("api/lists/{id}/unarchive/")
    suspend fun unarchiveList(@Path("id") id: String): ShoppingListDto

    @GET("api/lists/{id}/members/")
    suspend fun getMembers(@Path("id") id: String): List<ListMemberDto>

    @POST("api/lists/{id}/members/")
    suspend fun addMember(
        @Path("id") id: String,
        @Body request: AddMemberRequest
    ): ListMemberDto

    @DELETE("api/lists/{id}/members/{userId}/")
    suspend fun removeMember(
        @Path("id") id: String,
        @Path("userId") userId: String
    )

    @POST("api/lists/{id}/invites/")
    suspend fun createInvite(@Path("id") id: String): InviteDto

    @POST("api/invites/accept/")
    suspend fun acceptInvite(@Body request: AcceptInviteRequest): ShoppingListDto

    @GET("api/lists/{listId}/items/")
    suspend fun getItems(@Path("listId") listId: String): List<ShoppingItemDto>

    @POST("api/lists/{listId}/items/")
    suspend fun createItem(
        @Path("listId") listId: String,
        @Body request: ShoppingItemRequest
    ): ShoppingItemDto

    @PATCH("api/lists/{listId}/items/{itemId}/")
    suspend fun updateItem(
        @Path("listId") listId: String,
        @Path("itemId") itemId: String,
        @Body request: ShoppingItemRequest
    ): ShoppingItemDto

    @DELETE("api/lists/{listId}/items/{itemId}/")
    suspend fun deleteItem(
        @Path("listId") listId: String,
        @Path("itemId") itemId: String
    )

    @POST("api/lists/{listId}/items/{itemId}/reserve/")
    suspend fun reserveItem(
        @Path("listId") listId: String,
        @Path("itemId") itemId: String
    ): ShoppingItemDto

    @POST("api/lists/{listId}/items/{itemId}/release/")
    suspend fun releaseItem(
        @Path("listId") listId: String,
        @Path("itemId") itemId: String
    ): ShoppingItemDto

    @POST("api/lists/{listId}/items/{itemId}/purchase/")
    suspend fun purchaseItem(
        @Path("listId") listId: String,
        @Path("itemId") itemId: String
    ): ShoppingItemDto

    @POST("api/lists/{listId}/items/{itemId}/unpurchase/")
    suspend fun unpurchaseItem(
        @Path("listId") listId: String,
        @Path("itemId") itemId: String
    ): ShoppingItemDto

    @GET("api/lists/{listId}/total/")
    suspend fun getListTotal(
        @Path("listId") listId: String,
        @Query("currency") currency: String
    ): ListTotalDto

    @GET("api/exchange-rates/")
    suspend fun getExchangeRate(
        @Query("from") fromCurrency: String,
        @Query("to") toCurrency: String
    ): ExchangeRateDto
}
