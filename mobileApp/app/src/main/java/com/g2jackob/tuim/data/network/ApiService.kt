package com.g2jackob.tuim.data.network

import retrofit2.http.Body
import retrofit2.http.DELETE
import retrofit2.http.GET
import retrofit2.http.PATCH
import retrofit2.http.POST
import retrofit2.http.Path
import retrofit2.http.Query

interface ApiService {
    @POST("api/auth/login/")
    suspend fun login(@Body request: LoginRequest): TokenResponse

    @POST("api/auth/refresh/")
    suspend fun refresh(@Body request: RefreshRequest): TokenResponse

    @GET("api/shopping-lists/")
    suspend fun getLists(): List<ShoppingListDto>

    @POST("api/shopping-lists/")
    suspend fun createList(@Body request: ShoppingListRequest): ShoppingListDto

    @GET("api/shopping-lists/{id}/")
    suspend fun getList(@Path("id") id: String): ShoppingListDto

    @DELETE("api/shopping-lists/{id}/")
    suspend fun deleteList(@Path("id") id: String)

    @POST("api/shopping-lists/{id}/items/")
    suspend fun createItem(
        @Path("id") listId: String,
        @Body request: ShoppingItemRequest
    ): ShoppingItemDto

    @PATCH("api/shopping-lists/{listId}/items/{itemId}/")
    suspend fun updateItem(
        @Path("listId") listId: String,
        @Path("itemId") itemId: String,
        @Body request: PurchasedRequest
    ): ShoppingItemDto

    @DELETE("api/shopping-lists/{listId}/items/{itemId}/")
    suspend fun deleteItem(
        @Path("listId") listId: String,
        @Path("itemId") itemId: String
    )

    @GET("api/external/products/")
    suspend fun searchProducts(@Query("q") query: String): ProductSearchResponse
}
