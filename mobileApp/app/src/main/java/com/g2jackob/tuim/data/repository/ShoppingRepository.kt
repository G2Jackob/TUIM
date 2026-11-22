package com.g2jackob.tuim.data.repository

import com.g2jackob.tuim.data.local.ShoppingItemEntity
import com.g2jackob.tuim.data.local.ShoppingListEntity
import com.g2jackob.tuim.data.network.ExternalProductDto
import kotlinx.coroutines.flow.Flow

interface ShoppingRepository {
    val lists: Flow<List<ShoppingListEntity>>
    fun items(listId: String): Flow<List<ShoppingItemEntity>>
    fun isLoggedIn(): Boolean

    suspend fun login(username: String, password: String): Result<Unit>
    suspend fun logout()
    suspend fun refreshSession(): Result<Unit>
    suspend fun syncLists(): Result<Unit>
    suspend fun syncList(listId: String): Result<Unit>
    suspend fun createList(name: String, description: String, currency: String): Result<Unit>
    suspend fun deleteList(listId: String): Result<Unit>
    suspend fun createItem(
        listId: String,
        name: String,
        quantity: Double,
        unit: String,
        category: String,
        note: String,
        estimatedPrice: Double?
    ): Result<Unit>
    suspend fun setPurchased(listId: String, itemId: String, purchased: Boolean): Result<Unit>
    suspend fun deleteItem(listId: String, itemId: String): Result<Unit>
    suspend fun searchProducts(query: String): Result<List<ExternalProductDto>>
}
