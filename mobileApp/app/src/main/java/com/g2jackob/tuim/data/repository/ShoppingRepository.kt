package com.g2jackob.tuim.data.repository

import com.g2jackob.tuim.data.local.ShoppingItemEntity
import com.g2jackob.tuim.data.local.ShoppingListEntity
import com.g2jackob.tuim.data.network.CurrentUserDto
import com.g2jackob.tuim.data.network.ExchangeRateDto
import com.g2jackob.tuim.data.network.InviteDto
import com.g2jackob.tuim.data.network.ListMemberDto
import com.g2jackob.tuim.data.network.ListTotalDto
import kotlinx.coroutines.flow.Flow

interface ShoppingRepository {
    val lists: Flow<List<ShoppingListEntity>>
    fun items(listId: String): Flow<List<ShoppingItemEntity>>
    fun isLoggedIn(): Boolean

    suspend fun loginDemo(): Result<Unit>
    suspend fun completeLogin(accessToken: String, refreshToken: String?): Result<Unit>
    suspend fun logout()
    suspend fun getCurrentUser(): Result<CurrentUserDto>
    suspend fun syncLists(): Result<Unit>
    suspend fun syncList(listId: String): Result<Unit>
    suspend fun createList(name: String, description: String, currency: String): Result<Unit>
    suspend fun updateList(
        listId: String,
        name: String,
        description: String,
        currency: String
    ): Result<Unit>
    suspend fun setListArchived(listId: String, archived: Boolean): Result<Unit>
    suspend fun deleteList(listId: String): Result<Unit>
    suspend fun getMembers(listId: String): Result<List<ListMemberDto>>
    suspend fun addMember(listId: String, identifier: String): Result<Unit>
    suspend fun removeMember(listId: String, userId: String): Result<Unit>
    suspend fun createInvite(listId: String): Result<InviteDto>
    suspend fun acceptInvite(code: String): Result<Unit>
    suspend fun createItem(
        listId: String,
        name: String,
        quantity: Double,
        unit: String,
        category: String,
        note: String,
        estimatedPrice: Double?
    ): Result<Unit>
    suspend fun updateItem(
        listId: String,
        itemId: String,
        name: String,
        quantity: Double,
        unit: String,
        category: String,
        note: String,
        estimatedPrice: Double?
    ): Result<Unit>
    suspend fun setPurchased(listId: String, itemId: String, purchased: Boolean): Result<Unit>
    suspend fun setReserved(listId: String, itemId: String, reserved: Boolean): Result<Unit>
    suspend fun deleteItem(listId: String, itemId: String): Result<Unit>
    suspend fun getListTotal(listId: String, currency: String): Result<ListTotalDto>
    suspend fun getExchangeRate(fromCurrency: String, toCurrency: String): Result<ExchangeRateDto>
}
